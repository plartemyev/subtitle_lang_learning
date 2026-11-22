"""Online translation helpers.

The provider interface language (``hl``) and the translation target (``tl``)
both follow the active UI locale of the user, passed in by the frontend -
not the subtitle language. Frontends use the returned URL with whatever
browsing widget they have (embedded web view, external browser, mobile
intent...).
"""
from urllib.parse import quote_plus

PROVIDER_URL_TEMPLATE = ('https://translate.google.com/'
                         '?hl={interface}&sl={source}&tl={target}&op=translate&text={text}')
DEFAULT_SOURCE_LANGUAGE = 'auto'


def build_translate_url(text: str, target: str, interface: str,
                        source: str = DEFAULT_SOURCE_LANGUAGE) -> str:
    return PROVIDER_URL_TEMPLATE.format(interface=interface, source=source,
                                        target=target, text=quote_plus(text))
