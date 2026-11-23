"""Web frontend backend: a thin FastAPI adapter over the core package.

Same rules as the Qt frontend: analysis lives in core and is reached through
:class:`core.controller.AppController`; this module never parses subtitles or
talks to OpenSubtitles itself. User-facing outcomes stay structured (message
code + params) - the browser renders them from the ``/api/i18n`` catalog,
keeping this server free of display text.
"""
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import analyzer
from core.controller import AppController
from core.dictionary import KaikkiDictionary
from core.languages import DEFAULT_LANGUAGE_CODE, LANGUAGES
from core.opensubtitles import OpenSubtitlesClient
from core.translation import TranslationCache, cache_key, get_translator
from ui import i18n
from web.serializers import analysis_to_dict, phrase_translation_to_dict

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# Offline translation and dictionary artifacts live outside the repository in
# the data directory (env override), prepared once by tools/prepare_nllb.py
# and tools/build_dictionary.py - see README.
DATA_DIR = Path(os.environ.get(
    'SUBTITLE_LEARNING_DATA_DIR',
    Path(__file__).resolve().parent.parent / 'data'))
TRANSLATION_MODEL_DIR = DATA_DIR / 'models' / 'nllb-600m-ct2'
DICTIONARY_DB_PATH = DATA_DIR / 'dictionary' / 'kaikki.sqlite'
TRANSLATION_CACHE_PATH = DATA_DIR / 'cache' / 'translations.sqlite'

app = FastAPI(title='subtitle_lang_learning', docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware)


def get_subtitles_client_factory() -> Callable[[], OpenSubtitlesClient]:
    """Client factory for AppController; overridden with fakes in tests."""
    return OpenSubtitlesClient


_translator = None
_dictionary = None
_translation_cache = None


def get_translation_provider():
    """Process-wide offline translator; None until the model is prepared."""
    global _translator
    if not TRANSLATION_MODEL_DIR.joinpath('model.bin').exists():
        return None
    if _translator is None:
        _translator = get_translator(TRANSLATION_MODEL_DIR)
    return _translator


def get_dictionary():
    """Process-wide Wiktionary dictionary; None until the database is built."""
    global _dictionary
    if not DICTIONARY_DB_PATH.exists():
        return None
    if _dictionary is None:
        _dictionary = KaikkiDictionary(DICTIONARY_DB_PATH)
    return _dictionary


def get_translation_cache():
    """Process-wide sqlite LRU cache of phrase translation calls."""
    global _translation_cache
    if _translation_cache is None:
        _translation_cache = TranslationCache(TRANSLATION_CACHE_PATH)
    return _translation_cache


class OnlineQuery(BaseModel):
    query: str
    language: str = DEFAULT_LANGUAGE_CODE


class PhraseQuery(BaseModel):
    text: str
    language: str = DEFAULT_LANGUAGE_CODE
    target: str = i18n.DEFAULT_LOCALE


@app.get('/')
def index():
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.get('/api/languages')
def languages():
    return [{'code': language.code, 'article_words': sorted(language.article_words)}
            for language in LANGUAGES.values()]


@app.get('/api/i18n/{locale}')
def i18n_catalog(locale: str):
    if locale not in i18n.LOCALES:
        raise HTTPException(status_code=404, detail='unsupported locale')
    return {'locale': locale, 'messages': i18n.catalog(locale)}


@app.post('/api/analyze/file')
def analyze_file(file: UploadFile = File(...), language: str = Form(DEFAULT_LANGUAGE_CODE)):
    if language not in LANGUAGES:
        raise HTTPException(status_code=400, detail={'error': 'unsupported language'})
    # load_from_file wants a path: the exact desktop pipeline (chardet per
    # line, srt parse) runs on the uploaded bytes through a temp file.
    handle = tempfile.NamedTemporaryFile(delete=False, suffix='.srt')
    try:
        handle.write(file.file.read())
        handle.close()
        result = AppController().load_from_file(handle.name, language)
    except Exception:
        logger.warning('Unable to load uploaded subtitles.', exc_info=True)
        raise HTTPException(status_code=400, detail={
            'message': {'code': 'unable_to_load_file',
                        'params': {'path': file.filename or ''}}})
    finally:
        os.unlink(handle.name)
    return analysis_to_dict(result)


@app.post('/api/analyze/online')
def analyze_online(query: OnlineQuery,
                   subtitles_client_factory: Callable = Depends(get_subtitles_client_factory)):
    if query.language not in LANGUAGES:
        raise HTTPException(status_code=400, detail={'error': 'unsupported language'})
    messages = []
    controller = AppController(warning_callback=messages.append,
                               subtitles_client_factory=subtitles_client_factory)
    result = controller.load_online(query.query, query.language)
    return {'analysis': analysis_to_dict(result) if result is not None else None,
            'messages': [{'code': message.code, 'params': message.params}
                         for message in messages]}


@app.post('/api/translate/phrase')
def translate_phrase(query: PhraseQuery,
                     provider=Depends(get_translation_provider),
                     cache=Depends(get_translation_cache)):
    """Offline whole-phrase translation with per-word alignments.

    Results are served from the sqlite LRU cache when seen before; words
    without confident attention carry translation=null so the frontend can
    fall back to the dictionary lookup.
    """
    if query.language not in LANGUAGES:
        raise HTTPException(status_code=400, detail={'error': 'unsupported language'})
    if query.target not in i18n.LOCALES:
        raise HTTPException(status_code=400, detail={'error': 'unsupported target'})
    text = query.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail={'error': 'empty text'})
    key = cache_key(query.language, query.target, text)
    cached = cache.get(key)
    if cached is not None:
        return dict(cached, cached=True)
    if provider is None:
        raise HTTPException(status_code=503, detail={
            'message': {'code': 'translation_unavailable', 'params': {}}})
    words = analyzer.tokenize_phrase(text, query.language)
    try:
        translation = provider.translate(text, query.language, query.target, words)
    except Exception:
        logger.warning('Offline translation failed.', exc_info=True)
        raise HTTPException(status_code=503, detail={
            'message': {'code': 'translation_unavailable', 'params': {}}})
    payload = phrase_translation_to_dict(translation)
    cache.put(key, payload)
    return dict(payload, cached=False)


@app.get('/api/dictionary/lookup')
def dictionary_lookup(language: str, target: str, word: str, lemma: str = '',
                      pos: str = '', dictionary=Depends(get_dictionary)):
    """Wiktionary glosses/translations for one word of an analyzed phrase.

    Returns no entries (not an error) when the dictionary is not built yet
    or the word is unknown to Wiktionary.
    """
    if language not in LANGUAGES:
        raise HTTPException(status_code=400, detail={'error': 'unsupported language'})
    if target not in i18n.LOCALES:
        raise HTTPException(status_code=400, detail={'error': 'unsupported target'})
    if dictionary is None:
        return {'word': word, 'entries': []}
    return dictionary.lookup(language, target, word, lemma, pos)


app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')
