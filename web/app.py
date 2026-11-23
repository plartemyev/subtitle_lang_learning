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

from core.controller import AppController
from core.languages import DEFAULT_LANGUAGE_CODE, LANGUAGES
from core.opensubtitles import OpenSubtitlesClient
from ui import i18n
from web.serializers import analysis_to_dict

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

app = FastAPI(title='subtitle_lang_learning', docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware)


def get_subtitles_client_factory() -> Callable[[], OpenSubtitlesClient]:
    """Client factory for AppController; overridden with fakes in tests."""
    return OpenSubtitlesClient


class OnlineQuery(BaseModel):
    query: str
    language: str = DEFAULT_LANGUAGE_CODE


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


app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')
