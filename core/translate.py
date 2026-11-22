"""Online translation helpers.

The default target language is the UI display language of the user, not the
subtitle language. Frontends use the returned URL with whatever browsing
widget they have (embedded web view, external browser, mobile intent...).
"""
from urllib.parse import quote_plus

PROVIDER_URL_TEMPLATE = 'https://translate.google.com/?sl={source}&tl={target}&op=translate&text={text}'
DEFAULT_TARGET_LANGUAGE = 'ru'
DEFAULT_SOURCE_LANGUAGE = 'auto'


def build_translate_url(text: str, target: str = DEFAULT_TARGET_LANGUAGE,
                        source: str = DEFAULT_SOURCE_LANGUAGE) -> str:
    return PROVIDER_URL_TEMPLATE.format(source=source, target=target, text=quote_plus(text))
