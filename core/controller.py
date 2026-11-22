"""Application orchestration.

Coordinates subtitle loading and analysis for any frontend. Communicates
user-facing outcomes through structured :class:`UserMessage` events (never
pre-formatted sentences) so that each UI can localize them.
"""
import logging
import traceback
from dataclasses import dataclass, field
from typing import Callable, Optional

from core import analyzer
from core.models import AnalysisResult
from core.opensubtitles import OpenSubtitlesClient

logger = logging.getLogger(__name__)

# User message codes, rendered by the UI layer
NO_SUBTITLES_FOUND = 'no_subtitles_found'
SUBTITLES_SERVICE_ERROR = 'subtitles_service_error'
NO_PARSEABLE_SUBTITLES = 'no_parseable_subtitles'


@dataclass
class UserMessage:
    """User-facing event: a code plus interpolation params, no display text."""
    code: str
    params: dict = field(default_factory=dict)


class AppController:
    """Loads subtitles from files or online sources and keeps the current analysis."""

    def __init__(self, warning_callback: Optional[Callable[[UserMessage], None]] = None,
                 subtitles_client_factory=OpenSubtitlesClient):
        self.warning_callback = warning_callback
        self.subtitles_client_factory = subtitles_client_factory
        self.current_result: Optional[AnalysisResult] = None
        self._loaded_query = ''
        self._loaded_language_code = ''

    def _warn(self, message: UserMessage) -> None:
        if self.warning_callback is not None:
            self.warning_callback(message)

    def load_from_file(self, sub_file_path: str, language_code: str) -> AnalysisResult:
        raw_sub = analyzer.read_subtitles_file(sub_file_path)
        self.current_result = analyzer.analyze_subtitles(analyzer.parse_raw(raw_sub), language_code)
        return self.current_result

    def load_online(self, query: str, language_code: str) -> Optional[AnalysisResult]:
        """Search and analyze online subtitles.

        Returns None when nothing new was loaded: too short query, same
        query+language already loaded, search failure or no parseable result.
        """
        if len(query) < 4 or (query == self._loaded_query and language_code == self._loaded_language_code):
            return None
        client = self.subtitles_client_factory()
        try:
            # anonymous login is mandatory: without a token SearchSubtitles
            # answers 401 Unauthorized
            client.login('', '')
            candidates = client.search_subtitles(query, language_code)
        except Exception as e:
            logger.warning('Problem with OpenSubtitles.org communication.', exc_info=e)
            self._warn(UserMessage(SUBTITLES_SERVICE_ERROR))
            return None
        if not candidates:
            self._warn(UserMessage(NO_SUBTITLES_FOUND))
            return None
        for candidate in candidates:
            try:
                raw_sub = client.download_subtitle(candidate.get('IDSubtitleFile'), candidate.get('SubFileName'))
                self.current_result = analyzer.analyze_subtitles(analyzer.parse_raw(raw_sub), language_code)
            except Exception as e:
                logger.info('Unable to parse subtitle file. Will try another one if there is some')
                logger.debug('Traceback:\n{}'.format('\n'.join(traceback.format_tb(e.__traceback__))))
                continue
            logger.info('Successfully parsed subtitle file')
            self._loaded_query = query
            self._loaded_language_code = language_code
            return self.current_result
        logger.warning(f'Unable to parse any subtitle file out of {len(candidates)}')
        self._warn(UserMessage(NO_PARSEABLE_SUBTITLES, {'count': len(candidates)}))
        return None
