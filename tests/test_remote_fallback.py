"""Remote fallback-switch policy: cached dead state, probes, dead TTLs."""
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.translation import chain, remote


class FakeResponse:
    def __init__(self, status=200, body='{"choices": [{"message": '
                 '{"content": "перевод"}}]}'):
        self.status = status
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.body.encode('utf-8')


def make_provider():
    return remote.OllamaProvider('http://203.0.113.1:8011', 'test-model',
                                 api_key='sk-test')


class OllamaFallbackSwitchTests(unittest.TestCase):
    def setUp(self):
        self.provider = make_provider()

    def test_no_connect_caches_dead_for_ten_minutes(self):
        with mock.patch.object(remote.socket, 'create_connection',
                               side_effect=OSError('refused')):
            with self.assertRaisesRegex(RuntimeError, 'no connect'):
                self.provider.translate('hi', 'eng', 'ru', [])
        self.assertGreaterEqual(self.provider._dead_until
                                - self.provider._dead_until, 0)
        self.assertIn('no connect', self.provider._dead_reason)
        remaining = self.provider._cached_dead()
        self.assertLessEqual(remaining, remote.CONNECT_DEAD_SECONDS)
        self.assertGreater(remaining, remote.CONNECT_DEAD_SECONDS - 5)

    def test_cached_dead_skips_probes_entirely(self):
        self.provider._mark_dead(remote.CONNECT_DEAD_SECONDS, 'no connect')
        calls = []
        with mock.patch.object(remote.socket, 'create_connection',
                               side_effect=lambda *a, **k: calls.append(1)):
            with self.assertRaisesRegex(RuntimeError, 'cached dead'):
                self.provider.translate('hi', 'eng', 'ru', [])
        self.assertEqual(calls, [])  # no probe happened while cached dead

    def test_no_slot_caches_dead_for_ten_seconds(self):
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               side_effect=remote.urllib.error.HTTPError(
                                   'url', 503, 'slot unavailable', {}, None)):
            with self.assertRaisesRegex(RuntimeError, 'no free slot'):
                self.provider.translate('hi', 'eng', 'ru', [])
        remaining = self.provider._cached_dead()
        self.assertLessEqual(remaining, remote.SLOT_DEAD_SECONDS)
        self.assertGreater(remaining, remote.SLOT_DEAD_SECONDS - 5)
        self.assertIn('no free slot', self.provider._dead_reason)

    def test_successful_call_clears_dead_state(self):
        self.provider._mark_dead(remote.SLOT_DEAD_SECONDS, 'no free slot')
        self.provider._dead_until = time.monotonic() - 0.1  # cache expired
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               return_value=FakeResponse()):
            result = self.provider.translate('hi', 'eng', 'ru', [])
        self.assertEqual(result.target_text, 'перевод')
        self.assertEqual(self.provider._cached_dead(), 0.0)
        self.assertEqual(self.provider._dead_reason, 'fresh')

    def test_health_503_is_treated_as_no_slot(self):
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               side_effect=remote.urllib.error.HTTPError(
                                   'url', 503, 'busy', {}, None)):
            with self.assertRaisesRegex(RuntimeError, 'no free slot'):
                self.provider.translate('hi', 'eng', 'ru', [])

    def test_server_without_health_endpoint_is_available(self):
        # servers without /health answer 404; that is not a slot failure -
        # the call should proceed to the chat completion and succeed
        responses = [remote.urllib.error.HTTPError('url', 404, 'missing',
                                                   {}, None),
                     FakeResponse()]
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               side_effect=responses) as opener:
            result = self.provider.translate('hi', 'eng', 'ru', [])
        self.assertEqual(result.target_text, 'перевод')
        self.assertEqual(opener.call_count, 2)  # health + chat only


if __name__ == '__main__':
    unittest.main()
