"""Remote fallback-switch policy: cached dead state, probes, dead TTLs."""
import io
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


METRICS_IDLE = ('# HELP llamacpp:requests_processing Number of requests '
                'processing\n'
                '# TYPE llamacpp:requests_processing gauge\n'
                'llamacpp:requests_processing 0\n'
                'llamacpp:requests_deferred 0\n')
METRICS_BUSY = ('llamacpp:requests_processing 1\n'
                'llamacpp:requests_deferred 1\n')
PROPS_ONE_SLOT = '{"total_slots": 1}'
# health, metrics, props, chat completion - a full successful probe sequence
PROBE_THEN_COMPLETION = [FakeResponse(), FakeResponse(body=METRICS_IDLE),
                         FakeResponse(body=PROPS_ONE_SLOT), FakeResponse()]


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
                                   'url', 503, 'loading', {}, None)):
            with self.assertRaisesRegex(RuntimeError, 'model loading'):
                self.provider.translate('hi', 'eng', 'ru', [])
        remaining = self.provider._cached_dead()
        self.assertLessEqual(remaining, remote.SLOT_DEAD_SECONDS)
        self.assertGreater(remaining, remote.SLOT_DEAD_SECONDS - 5)
        self.assertIn('model loading', self.provider._dead_reason)

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

    def test_health_503_is_treated_as_model_loading(self):
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               side_effect=remote.urllib.error.HTTPError(
                                   'url', 503, 'busy', {}, None)):
            with self.assertRaisesRegex(RuntimeError, 'model loading'):
                self.provider.translate('hi', 'eng', 'ru', [])

    def test_busy_gauges_cache_dead_without_sending_a_completion(self):
        # llama.cpp /health answers 200 while generating; the /metrics
        # gauges are what report the business
        responses = [FakeResponse(),  # health: 200 even while busy
                     FakeResponse(body=METRICS_BUSY),
                     FakeResponse(body=PROPS_ONE_SLOT)]
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               side_effect=responses) as opener:
            with self.assertRaisesRegex(RuntimeError, 'server busy'):
                self.provider.translate('hi', 'eng', 'ru', [])
        self.assertEqual(opener.call_count, 3)  # no chat completion sent
        remaining = self.provider._cached_dead()
        self.assertLessEqual(remaining, remote.SLOT_DEAD_SECONDS)
        self.assertGreater(remaining, remote.SLOT_DEAD_SECONDS - 5)
        self.assertIn('server busy', self.provider._dead_reason)

    def test_queued_requests_flag_busy_regardless_of_free_slots(self):
        # a deferred request is one already sitting in the server queue:
        # ours would line up behind it even with slots still free
        self.provider._slots = 4
        metrics = ('llamacpp:requests_processing 2\n'
                   'llamacpp:requests_deferred 3\n')
        responses = [FakeResponse(), FakeResponse(body=metrics)]
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               side_effect=responses) as opener:
            with self.assertRaisesRegex(RuntimeError, 'server busy'):
                self.provider.translate('hi', 'eng', 'ru', [])
        self.assertEqual(opener.call_count, 2)  # no /props refetch, no chat

    def test_partial_load_on_multi_slot_server_is_available(self):
        self.provider._slots = 4
        metrics = ('llamacpp:requests_processing 1\n'
                   'llamacpp:requests_deferred 0\n')
        responses = [FakeResponse(), FakeResponse(body=metrics),
                     FakeResponse()]
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               side_effect=responses):
            result = self.provider.translate('hi', 'eng', 'ru', [])
        self.assertEqual(result.target_text, 'перевод')

    def test_server_without_metrics_endpoint_is_available(self):
        # Ollama has no /metrics; occupancy stays unknown and the call
        # proceeds (the in-flight guard and completion timeout bound it)
        body = io.BytesIO(b'not found')
        responses = [FakeResponse(),
                     remote.urllib.error.HTTPError('url', 404, 'missing',
                                                   {}, body),
                     FakeResponse()]
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               side_effect=responses):
            result = self.provider.translate('hi', 'eng', 'ru', [])
        self.assertEqual(result.target_text, 'перевод')
        self.assertTrue(body.closed)

    def test_total_slots_is_fetched_once_and_cached(self):
        # first call: health + metrics + props + chat; second: props cached,
        # so health + metrics + chat
        responses = [FakeResponse(), FakeResponse(body=METRICS_IDLE),
                     FakeResponse(body=PROPS_ONE_SLOT), FakeResponse(),
                     FakeResponse(), FakeResponse(body=METRICS_IDLE),
                     FakeResponse()]
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               side_effect=responses) as opener:
            self.provider.translate('hi', 'eng', 'ru', [])
            self.provider.translate('more', 'eng', 'ru', [])
        self.assertEqual(opener.call_count, 7)
        self.assertEqual(self.provider._slots, 1)

    def test_own_completion_in_flight_raises_busy_without_probes(self):
        self.provider._slots = 1
        self.provider._in_flight = 1
        with mock.patch.object(remote.socket, 'create_connection') as connect, \
             mock.patch.object(remote.urllib.request, 'urlopen') as opener:
            with self.assertRaisesRegex(RuntimeError, 'in flight'):
                self.provider.translate('hi', 'eng', 'ru', [])
        self.assertEqual(connect.call_count, 0)
        self.assertEqual(opener.call_count, 0)

    def test_completion_timeout_is_busy_not_transport_dead(self):
        # a silent completion means our request sits in the server queue:
        # that must cache the short busy TTL, not the ten-minute one
        responses = list(PROBE_THEN_COMPLETION[:3])
        responses.append(remote.socket.timeout('timed out'))
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               side_effect=responses):
            with self.assertRaisesRegex(RuntimeError, 'no answer'):
                self.provider.translate('hi', 'eng', 'ru', [])
        remaining = self.provider._cached_dead()
        self.assertLessEqual(remaining, remote.SLOT_DEAD_SECONDS)
        self.assertGreater(remaining, remote.SLOT_DEAD_SECONDS - 5)
        self.assertIn('no answer', self.provider._dead_reason)

    def test_health_404_falls_through_to_occupancy_and_chat(self):
        # unknown servers (404 on /health and /metrics) are treated as
        # available - the call proceeds to the chat completion and succeeds
        health_body = io.BytesIO(b'missing')
        metrics_body = io.BytesIO(b'missing')
        responses = [remote.urllib.error.HTTPError('url', 404, 'missing',
                                                   {}, health_body),
                     remote.urllib.error.HTTPError('url', 404, 'missing',
                                                   {}, metrics_body),
                     FakeResponse()]
        with mock.patch.object(remote.socket, 'create_connection'), \
             mock.patch.object(remote.urllib.request, 'urlopen',
                               side_effect=responses) as opener:
            result = self.provider.translate('hi', 'eng', 'ru', [])
        self.assertEqual(result.target_text, 'перевод')
        self.assertEqual(opener.call_count, 3)  # health + metrics + chat
        self.assertTrue(health_body.closed)
        self.assertTrue(metrics_body.closed)

    def test_gauge_parsing(self):
        body = ('# HELP llamacpp:requests_processing Number of requests '
                'processing\n'
                '# TYPE llamacpp:requests_processing gauge\n'
                'llamacpp:requests_processing 2\n'
                'llamacpp:requests_deferred 0.0\n'
                'other_metric 5\n')
        self.assertEqual(remote._gauge(body, 'llamacpp:requests_processing'),
                         2.0)
        self.assertEqual(remote._gauge(body, 'llamacpp:requests_deferred'),
                         0.0)
        self.assertIsNone(remote._gauge(body, 'llamacpp:missing'))
        self.assertIsNone(remote._gauge('llamacpp:requests_processing abc',
                                        'llamacpp:requests_processing'))

    def test_failed_calls_release_the_error_response(self):
        # an HTTPError doubles as an open response body: left to the garbage
        # collector it warns ("Implicitly cleaning up <HTTPError ...>")
        # responses route by request URL: the probe chain is data-dependent
        # (props runs only after a parseable metrics body), so call-order
        # reply lists would misalign
        positions = ('health', 'metrics', 'props', 'chat')
        for code, message in ((503, 'busy'), (404, 'missing'), (500, 'down')):
            for position in positions:
                with self.subTest(code=code, position=position):
                    self.provider = make_provider()  # a 503 caches the remote dead
                    body = io.BytesIO(b'error details')
                    failure = remote.urllib.error.HTTPError('url', code, message, {}, body)

                    def routed(request, **kwargs):
                        url = getattr(request, 'full_url', request)
                        if url.endswith('/health'):
                            return failure if position == 'health' else FakeResponse()
                        if url.endswith('/metrics'):
                            return (failure if position == 'metrics'
                                    else FakeResponse(body=METRICS_IDLE))
                        if url.endswith('/props'):
                            return (failure if position == 'props'
                                    else FakeResponse(body=PROPS_ONE_SLOT))
                        return failure if position == 'chat' else FakeResponse()

                    with mock.patch.object(remote.socket, 'create_connection'), \
                         mock.patch.object(remote.urllib.request, 'urlopen',
                                           side_effect=routed):
                        try:
                            self.provider.translate('hi', 'eng', 'ru', [])
                        except RuntimeError:
                            pass  # slot and HTTP failures raise on purpose
                    self.assertTrue(body.closed)


if __name__ == '__main__':
    unittest.main()
