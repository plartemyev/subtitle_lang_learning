"""Offline translation and dictionary endpoints (fake provider, no model)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

import web.app
from core.translation.cache import cache_key
from core.translation.models import PhraseTranslation, WordTranslation
from web.app import app, get_dictionary, get_translation_cache, get_translation_provider

client = TestClient(app)


class FakeProvider:
    """Deterministic stand-in: uppercases every word, counts real passes."""

    def __init__(self):
        self.calls = 0

    def translate(self, text, source_code, target_locale, words):
        self.calls += 1
        return PhraseTranslation(source_text=text, target_text='перевод: ' + text,
                                 words=[WordTranslation(text=token.text, lemma=token.lemma,
                                                        pos=token.pos, start=token.start,
                                                        end=token.end, morph=token.morph,
                                                        translation=token.text.upper(),
                                                        score=0.9)
                                        for token in words])


class FakeCache:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def put(self, key, payload):
        self.store[key] = payload


class TranslatePhraseApiTests(unittest.TestCase):
    def override(self, dependency, value):
        app.dependency_overrides[dependency] = lambda: value
        self.addCleanup(app.dependency_overrides.pop, dependency, None)

    def setUp(self):
        self.provider = FakeProvider()
        self.cache = FakeCache()
        self.override(get_translation_provider, self.provider)
        self.override(get_translation_cache, self.cache)

    def post_phrase(self, text='Hello world', language='eng', target='ru'):
        return client.post('/api/translate/phrase',
                           json={'text': text, 'language': language, 'target': target})

    def test_translation_carries_word_alignments(self):
        response = self.post_phrase()
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['translation'], 'перевод: Hello world')
        self.assertFalse(payload['cached'])
        self.assertEqual([word['translation'] for word in payload['words']],
                         ['HELLO', 'WORLD'])
        self.assertEqual(payload['words'][0]['lemma'], 'hello')

    def test_repeated_call_is_served_from_the_cache(self):
        self.post_phrase()
        response = self.post_phrase()
        self.assertTrue(response.json()['cached'])
        self.assertEqual(self.provider.calls, 1, 'model must run once')
        self.assertEqual(len(self.cache.store), 1)
        # the stored payload is keyed by the same rule the endpoint uses
        self.assertIn(cache_key('eng', 'ru', 'Hello world'), self.cache.store)

    def test_missing_model_returns_localizable_code(self):
        self.override(get_translation_provider, None)
        response = self.post_phrase()
        self.assertEqual(response.status_code, 503)
        message = response.json()['detail']['message']
        self.assertEqual(message['code'], 'translation_unavailable')

    def test_unsupported_language_is_rejected(self):
        self.assertEqual(self.post_phrase(language='klingon').status_code, 400)

    def test_unsupported_target_is_rejected(self):
        self.assertEqual(self.post_phrase(target='fr').status_code, 400)

    def test_blank_text_is_rejected(self):
        self.assertEqual(self.post_phrase(text='   ').status_code, 400)


class FakeChain:
    """Chain stand-in carrying just the attribute the start-up hook reads."""

    def __init__(self, providers):
        self._providers = providers


class PrewarmTests(unittest.TestCase):
    """web.app._prewarm_engines warms the engines that expose prewarm and
    stays non-fatal on engines that fail (the per-request start retries)."""

    def run_hook(self, provider):
        with mock.patch.object(web.app, 'get_translation_provider',
                               return_value=provider):
            web.app._prewarm_engines()

    def test_prewarms_only_engines_that_expose_it(self):
        warm = mock.Mock()
        self.run_hook(FakeChain([FakeProvider(), warm]))
        warm.prewarm.assert_called_once_with()

    def test_survives_a_failing_engine(self):
        failing = mock.Mock()
        failing.prewarm.side_effect = RuntimeError('llama-server exited')
        with self.assertLogs('web.app', level='WARNING'):
            self.run_hook(FakeChain([failing]))
        failing.prewarm.assert_called_once_with()

    def test_without_engines_is_a_no_op(self):
        self.run_hook(None)


class FakeDictionary:
    """Stand-in returning one fixed entry regardless of the query."""

    def __init__(self):
        self.last_query = None

    def lookup(self, source_code, target_locale, word, lemma='', pos=''):
        self.last_query = (source_code, target_locale, word, lemma, pos)
        return {'word': word, 'entries': [
            {'pos': 'NOUN', 'glosses': ['A nuclear group'], 'translations': ['семья']}]}


class DictionaryApiTests(unittest.TestCase):
    def override(self, dependency, value):
        app.dependency_overrides[dependency] = lambda: value
        self.addCleanup(app.dependency_overrides.pop, dependency, None)

    def lookup(self, word='family', language='eng', target='ru', lemma='', pos=''):
        return client.get('/api/dictionary/lookup',
                          params={'language': language, 'target': target,
                                  'word': word, 'lemma': lemma, 'pos': pos})

    def test_lookup_returns_entries_from_the_dictionary(self):
        fake = FakeDictionary()
        self.override(get_dictionary, fake)
        response = self.lookup()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['entries'][0]['translations'], ['семья'])
        self.assertEqual(fake.last_query, ('eng', 'ru', 'family', '', ''))

    def test_lookup_without_dictionary_returns_no_entries(self):
        self.override(get_dictionary, None)
        response = self.lookup()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'word': 'family', 'entries': []})

    def test_unsupported_language_is_rejected(self):
        self.assertEqual(self.lookup(language='klingon').status_code, 400)

    def test_unsupported_target_is_rejected(self):
        self.assertEqual(self.lookup(target='fr').status_code, 400)


if __name__ == '__main__':
    unittest.main()
