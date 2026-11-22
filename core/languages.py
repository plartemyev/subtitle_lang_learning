"""Canonical language registry.

Languages are identified by neutral ISO-like codes ('eng', 'deu', 'rus') everywhere
inside core. Human-readable names are a UI concern and must never be used as keys.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str  # canonical key used across the application, e.g. 'deu'
    opensubtitles_code: str  # OpenSubtitles.org language id (uses 'ger' for German)
    spacy_model: str  # spaCy model used for lemmatization and POS tagging


LANGUAGES = {
    'eng': Language(code='eng', opensubtitles_code='eng', spacy_model='en_core_web_sm'),
    'deu': Language(code='deu', opensubtitles_code='ger', spacy_model='de_core_news_sm'),
    'rus': Language(code='rus', opensubtitles_code='rus', spacy_model='ru_core_news_sm'),
}

DEFAULT_LANGUAGE_CODE = 'eng'


def resolve_language(code: str) -> Language:
    language = LANGUAGES.get(code)
    if language is None:
        supported = ', '.join(sorted(LANGUAGES))
        raise ValueError(f'Unsupported language code "{code}", supported: {supported}')
    return language
