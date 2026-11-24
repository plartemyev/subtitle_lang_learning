"""Fallback chain over translation providers.

Tries the engines in order (remote first, local backup last) and answers
with the first success; when every engine fails, the collected errors are
re-raised so the API layer can answer 503 and the UI keeps showing the
instant dictionary view.
"""
import logging

logger = logging.getLogger(__name__)


class FallbackProvider:
    """Translation provider chain with engine-level fallback."""

    def __init__(self, providers):
        self._providers = list(providers)

    def translate(self, text, source_code, target_locale, words):
        failures = []
        for provider in self._providers:
            try:
                return provider.translate(text, source_code, target_locale,
                                          words)
            except Exception as error:
                logger.warning('%s failed, falling back: %s',
                               getattr(provider, 'label',
                                       type(provider).__name__), error)
                failures.append(f'{getattr(provider, "label",
                                            type(provider).__name__)}: '
                                f'{error}')
        raise RuntimeError('all translation engines failed: '
                           + ' | '.join(failures))
