"""OpenSubtitles.org XML-RPC client.

UI-library agnostic: raises exceptions and returns plain data structures.
"""
import base64
import logging
import zlib
from typing import Dict, List
from xmlrpc.client import ServerProxy, Transport

from chardet.universaldetector import UniversalDetector

from core.languages import resolve_language

logger = logging.getLogger(__name__)


class OpenSubtitlesError(RuntimeError):
    """Raised when the OpenSubtitles.org API responds with a non-success status."""


def decompress(data: bytes) -> str:
    """
    Convert a base64-compressed subtitles file back to a string.

    :param data: the compressed data
    """
    fall_back_encodings = ['utf_8_sig', 'utf-8', 'latin1']
    uncompressed_string = zlib.decompress(base64.b64decode(data), 16 + zlib.MAX_WBITS)
    detector = UniversalDetector()
    detector.feed(uncompressed_string)
    detector.close()
    encoding = detector.result.get('encoding')
    logger.debug(f"Detected encoding: {encoding}")
    try:
        decoded_string = uncompressed_string.decode(encoding=encoding)
    except (TypeError, UnicodeDecodeError):
        # Detection was inconclusive, trying fall-back encodings
        for encoding in fall_back_encodings:
            try:
                decoded_string = uncompressed_string.decode(encoding=encoding)
            except UnicodeDecodeError as e:
                logger.info(f'Unable to decode content as {encoding}')
                logger.debug(e)
            else:
                # No exceptions happened, decoding success
                break
        else:
            # Tried all fall-back encodings, no success
            raise RuntimeError('Unable to decode subtitle content')
    return decoded_string


class OpenSubtitlesClient:
    def __init__(self):
        # noinspection SpellCheckingInspection
        opensubtitles_ua = b'VkxzdWIgMC4xMC4y'
        self.ua = base64.b64decode(opensubtitles_ua).decode()
        self.opensubtitles_api_url = 'http://api.opensubtitles.org/xml-rpc'
        self.opensubtitles_lang = 'en'
        self.token = None
        self.xmlrpc_transport = Transport()
        self.xmlrpc_transport.user_agent = self.ua
        self.xmlrpc = ServerProxy(self.opensubtitles_api_url, allow_none=True, transport=self.xmlrpc_transport)

    def _check_status(self, response: Dict, context: str) -> None:
        status = response.get('status', '').split()[0]
        if status != '200':
            raise OpenSubtitlesError(f'Unable to {context}, returned status is {status}')

    def login(self, username: str, password: str) -> None:
        response = self.xmlrpc.LogIn(username, password, self.opensubtitles_lang, self.ua)
        self._check_status(response, 'authenticate')
        self.token = response.get('token')

    def search_subtitles(self, query: str, language_code: str) -> List[Dict[str, str]]:
        logger.info(f'Searching subtitles for title {query} ({language_code}) in online DB')
        response = self.xmlrpc.SearchSubtitles(self.token, [{
            'sublanguageid': resolve_language(language_code).opensubtitles_code,
            'query': query
        }])
        self._check_status(response, 'search subtitles')
        found = response.get('data') or []
        logger.info(f'Found {len(found)} matching subtitles')
        return found

    def retrieve_subtitles(self, ids: List[str]) -> Dict[str, str]:
        response = self.xmlrpc.DownloadSubtitles(self.token, ids)
        self._check_status(response, 'get subtitles')
        subtitles_content = {}
        for item in response.get('data'):
            sub_id = item['idsubtitlefile']
            decoded_data = decompress(item['data'])
            if not decoded_data:
                logger.error('An error occurred while decoding subtitle ID {}.'.format(sub_id))
            else:
                subtitles_content[sub_id] = decoded_data
        return subtitles_content

    def download_subtitle(self, sub_id: str, sub_name: str) -> str:
        logger.info(f'Downloading subtitle file {sub_name} ID: {sub_id}')
        raw_subs_dict = self.retrieve_subtitles([sub_id])
        return raw_subs_dict.get(sub_id)
