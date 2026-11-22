"""AppController orchestration checks (no network, fake subtitles client)."""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.controller import AppController

SAMPLE_SRT = ('1\n00:00:01,000 --> 00:00:02,000\nTo be, or not to be.\n\n'
              '2\n00:00:03,000 --> 00:00:04,000\nThat is the question.\n\n')


class FakeSubtitlesClient:
    """Records the call order and serves a canned SRT without any network."""

    def __init__(self):
        self.calls = []

    def login(self, username: str, password: str) -> None:
        self.calls.append(('login', username, password))

    def search_subtitles(self, query: str, language_code: str) -> list:
        self.calls.append(('search', query, language_code))
        return [{'IDSubtitleFile': '42', 'SubFileName': 'sample.srt'}]

    def download_subtitle(self, sub_id: str, sub_name: str) -> str:
        self.calls.append(('download', sub_id, sub_name))
        return SAMPLE_SRT


class LoadOnlineTest(unittest.TestCase):
    def test_login_precedes_search_and_result_is_analyzed(self):
        client = FakeSubtitlesClient()
        controller = AppController(subtitles_client_factory=lambda: client)
        result = controller.load_online('hamlet', 'eng')
        self.assertIsNotNone(result)
        # SearchSubtitles rejects a None token with 401: login must go first
        self.assertEqual(client.calls[0], ('login', '', ''))
        self.assertEqual(client.calls[1], ('search', 'hamlet', 'eng'))
        self.assertEqual(client.calls[2], ('download', '42', 'sample.srt'))
        self.assertIn('be', result.words)
        # 'To be' twice plus the lemmatized 'is' of the second phrase
        self.assertEqual(result.words['be'].count, 3)

    def test_too_short_query_returns_none_without_calls(self):
        client = FakeSubtitlesClient()
        controller = AppController(subtitles_client_factory=lambda: client)
        self.assertIsNone(controller.load_online('ab', 'eng'))
        self.assertEqual(client.calls, [])

    def test_same_query_and_language_returns_none(self):
        controller = AppController(subtitles_client_factory=FakeSubtitlesClient)
        first = controller.load_online('hamlet', 'eng')
        again = controller.load_online('hamlet', 'eng')
        self.assertIsNotNone(first)
        self.assertIsNone(again)

    def test_search_failure_warns_and_returns_none(self):
        class FailingClient(FakeSubtitlesClient):
            def search_subtitles(self, query: str, language_code: str) -> list:
                raise RuntimeError('service unreachable')

        warnings = []
        controller = AppController(warning_callback=warnings.append,
                                   subtitles_client_factory=FailingClient)
        self.assertIsNone(controller.load_online('hamlet', 'eng'))
        self.assertEqual([message.code for message in warnings],
                         ['subtitles_service_error'])


if __name__ == '__main__':
    unittest.main()
