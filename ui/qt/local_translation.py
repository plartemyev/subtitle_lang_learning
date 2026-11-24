"""Local engines translation: lazily built resources and a thread-pool worker.

Native-primitives port of the web frontend's offline translation block
(web/app.py wiring + the updatePhraseTranslation flow): the instant literal
dictionary view is emitted first, the model translation (remote + local
fallback chain, sqlite LRU cached) second; both run on the global thread
pool so the UI never blocks on a llama.cpp call. Results carry the request
id - the main window renders only the newest one.
"""
import logging
from pathlib import Path

from PyQt6 import QtCore

from core.analyzer import tokenize_phrase
from core.dictionary import KaikkiDictionary, ReverseDictionaryIndex
from core.literal import LiteralDictionary
from core.translation import TranslationCache, cache_key, provider_from_env

logger = logging.getLogger(__name__)


class TranslationServices:
    """Process-wide lazily built translation resources, shared by the local
    view and the token tooltips (mirrors web/app.py's wiring)."""

    def __init__(self, data_dir):
        self._data_dir = Path(data_dir)
        self._engine = None
        self._engine_built = False
        self._dictionary = None
        self._literal = None
        self._cache = None

    @property
    def engine(self):
        """Fallback engine chain, or None when no engine is configured."""
        if not self._engine_built:
            self._engine = provider_from_env(self._data_dir)
            self._engine_built = True
        return self._engine

    @property
    def dictionary(self):
        """Wiktionary lookup for tooltips, or None until the database is built."""
        if self._dictionary is None:
            db_path = self._data_dir / 'dictionary' / 'kaikki.sqlite'
            if db_path.exists():
                self._dictionary = KaikkiDictionary(db_path)
        return self._dictionary

    @property
    def literal(self):
        """Word-by-word dictionary view, or None without the database."""
        if self._literal is None and self.dictionary is not None:
            self._literal = LiteralDictionary(self.dictionary)
            reverse_path = self._data_dir / 'dictionary' / 'reverse.sqlite'
            if reverse_path.exists():
                self._literal.reverse = ReverseDictionaryIndex(reverse_path)
        return self._literal

    @property
    def cache(self):
        """sqlite LRU cache of phrase translation calls."""
        if self._cache is None:
            self._cache = TranslationCache(
                self._data_dir / 'cache' / 'translations.sqlite')
        return self._cache


class _Signals(QtCore.QObject):
    literal_ready = QtCore.pyqtSignal(int, str)
    translation_ready = QtCore.pyqtSignal(int, object)


class TranslationRequest(QtCore.QRunnable):
    """One phrase through the literal view and the engine chain."""

    def __init__(self, request_id, services, text, language_code, target_locale):
        super().__init__()
        self.setAutoDelete(True)
        self.request_id = request_id
        self.services = services
        self.text = text
        self.language_code = language_code
        self.target_locale = target_locale
        self.signals = _Signals()

    def run(self):
        try:
            self._emit_literal()
            self._emit_translation()
        except Exception:
            logger.warning('Local translation failed.', exc_info=True)
            try:
                self.signals.translation_ready.emit(self.request_id, None)
            except RuntimeError:
                pass  # the frontend is shutting down, nothing to report to

    def _emit_literal(self):
        gloss = ''
        if self.services.literal is not None:
            words = tokenize_phrase(self.text, self.language_code)
            gloss = self.services.literal.translate(
                self.text, self.language_code, self.target_locale, words)
        self.signals.literal_ready.emit(self.request_id, gloss)

    def _emit_translation(self):
        payload = None
        if self.services.engine is not None:
            key = cache_key(self.language_code, self.target_locale, self.text)
            payload = self.services.cache.get(key)
            if payload is None:
                words = tokenize_phrase(self.text, self.language_code)
                translation = self.services.engine.translate(
                    self.text, self.language_code, self.target_locale, words)
                payload = translation.to_payload()
                self.services.cache.put(key, payload)
        self.signals.translation_ready.emit(self.request_id, payload)
