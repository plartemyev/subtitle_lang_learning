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
from typing import Callable

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import analyzer, paths
from core.controller import AppController
from core.dictionary import KaikkiDictionary, ReverseDictionaryIndex
from core.languages import DEFAULT_LANGUAGE_CODE, LANGUAGES
from core.literal import LiteralDictionary
from core.opensubtitles import OpenSubtitlesClient
from core.translation import (TranslationCache, cache_key, provider_from_env)
from ui import i18n
from web.serializers import analysis_to_dict, phrase_translation_to_dict

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# Translation and dictionary artifacts live outside the repository in the
# data directory (env override), prepared once by tools/build_dictionary.py
# and tools/prepare_hymt15.py - see README. The model engines are a remote
# OpenAI-compatible server (OLLAMA_* variables from the gitignored .env)
# with a local HY-MT1.5-1.8B llama.cpp fallback.
DATA_DIR = paths.data_dir()
DICTIONARY_DB_PATH = DATA_DIR / 'dictionary' / 'kaikki.sqlite'
DICTIONARY_REVERSE_PATH = DATA_DIR / 'dictionary' / 'reverse.sqlite'
TRANSLATION_CACHE_PATH = DATA_DIR / 'cache' / 'translations.sqlite'

app = FastAPI(title='subtitle_lang_learning', docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware)


@app.middleware('http')
async def cache_headers(request, call_next):
    """SPA shell and static assets cache for ten minutes, API answers never.

    Poor-connection visitors reload at zero round trips within the TTL; a
    deploy lands at most ten minutes late for them (assets fetched together
    also expire together, so stale script pairs do not occur). API answers
    carry no-store explicitly: no validators to revalidate with, and no
    intermediary may cache localized results.
    """
    response = await call_next(request)
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    else:
        response.headers['Cache-Control'] = 'max-age=600'
    return response


def get_subtitles_client_factory() -> Callable[[], OpenSubtitlesClient]:
    """Client factory for AppController; overridden with fakes in tests."""
    return OpenSubtitlesClient


_provider = None
_dictionary = None
_translation_cache = None
_literal_dictionary = None


def get_translation_provider():
    """Process-wide provider chain: remote model first, local HY-MT1.5
    fallback second; None when no engine is configured."""
    global _provider
    if _provider is not None:
        return _provider
    _provider = provider_from_env(DATA_DIR)
    return _provider


def get_literal_dictionary():
    """Process-wide word-by-word dictionary view; the reverse index is
    optional and picked up whenever its database appears."""
    global _literal_dictionary
    if not DICTIONARY_DB_PATH.exists():
        return None
    if _literal_dictionary is None:
        _literal_dictionary = LiteralDictionary(
            KaikkiDictionary(DICTIONARY_DB_PATH))
    if _literal_dictionary.reverse is None and DICTIONARY_REVERSE_PATH.exists():
        _literal_dictionary.reverse = ReverseDictionaryIndex(
            DICTIONARY_REVERSE_PATH)
    return _literal_dictionary


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
    """Offline whole-phrase translation through the engine chain.

    Results are served from the sqlite LRU cache when seen before; without
    an engine, or when it fails, the answer is 503 with the structured
    `translation_unavailable` message. The current engines return no
    per-word alignment (``words`` is empty): the frontend glosses single
    words through /api/dictionary/lookup.
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


@app.post('/api/translate/literal')
def translate_literal(query: PhraseQuery,
                      literal=Depends(get_literal_dictionary)):
    """Instant word-by-word dictionary view of a phrase (no model).

    Served before the model translation in the UI: the student immediately
    sees how the phrase is assembled from dictionary pieces while the model
    translation is still generating. A missing dictionary answers 503 with
    the same structured message as the model engines; the frontend hides
    the literal view in that case.
    """
    if query.language not in LANGUAGES:
        raise HTTPException(status_code=400, detail={'error': 'unsupported language'})
    if query.target not in i18n.LOCALES:
        raise HTTPException(status_code=400, detail={'error': 'unsupported target'})
    text = query.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail={'error': 'empty text'})
    if literal is None:
        raise HTTPException(status_code=503, detail={
            'message': {'code': 'translation_unavailable', 'params': {}}})
    words = analyzer.tokenize_phrase(text, query.language)
    return {'literal': literal.translate(text, query.language, query.target,
                                         words)}


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
