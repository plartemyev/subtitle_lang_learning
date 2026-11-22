"""Shared localization for all frontends (Qt, CLI, future web/Android).

One gettext catalog per UI locale lives in ``locales/`` at the repository
root, keyed by stable frontend-neutral message codes; the codes emitted by
:class:`core.controller.UserMessage` are a subset of them. The English
catalog is the reference locale: every locale ships a complete catalog and
a missing key falls back ``active -> en -> raw code``; catalog completeness
is guarded by ``tests/test_locales.py``.

UI locale codes are ISO-639-1 (``de``/``en``/``ru``/``th``) and are independent of
the subtitle language codes of :mod:`core.languages` (``eng``/``deu``/``rus``).
"""
import gettext
import os
from pathlib import Path

LOCALES = ('de', 'en', 'ru', 'th')
DEFAULT_LOCALE = 'en'
_DOMAIN = 'messages'
_LOCALE_DIR = Path(__file__).resolve().parent.parent / 'locales'

_translator = gettext.NullTranslations()
active_locale = DEFAULT_LOCALE


def detect_system_locale() -> str:
    """Best-effort UI locale from the environment, validated against LOCALES."""
    for variable in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        value = os.environ.get(variable)
        if not value:
            continue
        code = value.split('.')[0].split('_')[0].lower()
        return code if code in LOCALES else DEFAULT_LOCALE
    return DEFAULT_LOCALE


def setup(code: str = None) -> str:
    """Activate a UI locale and return the active locale code.

    ``None`` or an unsupported code falls back to the environment-detected
    locale and then to :data:`DEFAULT_LOCALE`. Callable again for live
    language switching.
    """
    global _translator, active_locale
    active_locale = code if code in LOCALES else detect_system_locale()
    translation = gettext.translation(_DOMAIN, _LOCALE_DIR, [active_locale], fallback=True)
    if active_locale != DEFAULT_LOCALE:
        translation.add_fallback(
            gettext.translation(_DOMAIN, _LOCALE_DIR, [DEFAULT_LOCALE], fallback=True))
    _translator = translation
    return active_locale


def tr(code: str, **params) -> str:
    """Look up a message code and interpolate optional ``{param}`` placeholders."""
    text = _translator.gettext(code)
    return text.format(**params) if params else text


def ntr(singular: str, plural: str, n: int, **params) -> str:
    """Plural-aware :func:`tr` (gettext ngettext lookup).

    ``n`` selects the plural form; interpolation params are passed separately
    (e.g. ``count=n`` when the template shows the number).
    """
    text = _translator.ngettext(singular, plural, n)
    return text.format(**params) if params else text


def format_user_message(message) -> str:
    """Render a structured core UserMessage into display text.

    A message carrying a ``count`` parameter looks up the plural variant
    ``<code>_plural`` (see the catalogs in ``locales/``).
    """
    if 'count' in message.params:
        return ntr(message.code, message.code + '_plural',
                   message.params['count'], **message.params)
    return tr(message.code, **message.params)
