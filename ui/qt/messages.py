"""All user-visible strings of the Qt frontend.

Single source to be replaced by a translation catalog (gettext / Qt Linguist)
later; view code must never hardcode display sentences. Static labels inside
main_window.ui are the remaining deferred part of the i18n pass.
"""
from core.controller import NO_PARSEABLE_SUBTITLES, NO_SUBTITLES_FOUND, SUBTITLES_SERVICE_ERROR

# Display names of the core language codes (keys of core.languages.LANGUAGES)
LANGUAGE_NAMES = {
    'eng': 'English',
    'deu': 'German',
    'rus': 'Russian',
}

WARNING_DIALOG_TITLE = 'WARNING'

WORD_META_LINE = 'Word "{word}" encountered {count} times'
POS_SUFFIX = ', {pos}'
POSSESSIVE_SUFFIX = ', {count} possessive'
CONTEXT_LABEL = 'Context:'

WARNING_TEMPLATES = {
    NO_SUBTITLES_FOUND: 'No subtitles found',
    SUBTITLES_SERVICE_ERROR: 'Problem with OpenSubtitles.org communication.',
    NO_PARSEABLE_SUBTITLES: 'Unable to parse any subtitle file out of {count}',
    'unable_to_load_file': 'Unable to load subtitles from file {path}',
}


def format_user_message(message) -> str:
    """Render a structured core UserMessage into display text."""
    template = WARNING_TEMPLATES.get(message.code, message.code)
    return template.format(**message.params)
