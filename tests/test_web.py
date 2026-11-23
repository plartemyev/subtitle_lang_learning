"""Web frontend backend checks (no network, fake subtitles client, no Qt)."""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from tests.test_controller import SAMPLE_SRT, FakeSubtitlesClient
from web.app import app, get_subtitles_client_factory

client = TestClient(app)


class StaticFrontendTest(unittest.TestCase):
    def test_index_page_served(self):
        response = client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('app.js', response.text)

    def test_health_reports_ok(self):
        self.assertEqual(client.get('/api/health').json(), {'status': 'ok'})


class LanguagesApiTest(unittest.TestCase):
    def test_lists_supported_subtitle_languages(self):
        response = client.get('/api/languages')
        self.assertEqual(response.status_code, 200)
        languages = response.json()
        self.assertEqual([language['code'] for language in languages], ['eng', 'deu', 'rus'])

    def test_german_carries_article_words(self):
        languages = client.get('/api/languages').json()
        deu = next(language for language in languages if language['code'] == 'deu')
        self.assertIn('der', deu['article_words'])


class I18nApiTest(unittest.TestCase):
    def test_reference_catalog_served_with_translations(self):
        data = client.get('/api/i18n/en').json()
        self.assertEqual(data['locale'], 'en')
        self.assertEqual(data['messages']['warning_title'], 'WARNING')

    def test_plural_pairs_collapse_into_ordered_forms(self):
        messages = client.get('/api/i18n/en').json()['messages']
        forms = messages['no_parseable_subtitles']
        self.assertEqual(len(forms), 2)
        self.assertIn('{count}', forms[0])

    def test_every_locale_ships_a_complete_catalog(self):
        en_keys = set(client.get('/api/i18n/en').json()['messages'])
        for locale in ('de', 'ru', 'th'):
            messages = client.get('/api/i18n/' + locale).json()['messages']
            self.assertEqual(set(messages), en_keys, locale)

    def test_unknown_locale_is_404(self):
        self.assertEqual(client.get('/api/i18n/fr').status_code, 404)


class AnalyzeFileApiTest(unittest.TestCase):
    def upload(self, content: bytes, filename: str = 'sample.srt'):
        return client.post('/api/analyze/file',
                           files={'file': (filename, content, 'text/plain')},
                           data={'language': 'eng'})

    def test_upload_is_analyzed_with_phrase_pool(self):
        response = self.upload(SAMPLE_SRT.encode())
        self.assertEqual(response.status_code, 200)
        analysis = response.json()
        self.assertEqual(analysis['language_code'], 'eng')
        # 'To be' twice plus the lemmatized 'is' of the second phrase
        self.assertEqual(analysis['words']['be']['count'], 3)
        phrase = analysis['phrases'][analysis['words']['be']['phrase']]
        self.assertEqual(phrase['text'], 'To be, or not to be.')
        self.assertIn('To', [word['text'] for word in phrase['words']])
        self.assertTrue(all('lemma' in word for word in phrase['words']))

    def test_context_phrase_is_deduplicated_across_words(self):
        analysis = self.upload(SAMPLE_SRT.encode()).json()
        referencing = {entry['phrase'] for entry in analysis['words'].values()
                       if entry['phrase'] is not None}
        # every context phrase is one pool entry, 'to' and 'be' share theirs
        self.assertEqual(len(referencing), len(analysis['phrases']))
        self.assertEqual(analysis['words']['to']['phrase'],
                         analysis['words']['be']['phrase'])

    def test_empty_upload_is_rejected_with_localizable_code(self):
        response = self.upload(b'', filename='broken.srt')
        self.assertEqual(response.status_code, 400)
        message = response.json()['detail']['message']
        self.assertEqual(message['code'], 'unable_to_load_file')
        self.assertEqual(message['params'], {'path': 'broken.srt'})


class AnalyzeOnlineApiTest(unittest.TestCase):
    def override_client_factory(self, client_class):
        app.dependency_overrides[get_subtitles_client_factory] = lambda: client_class
        self.addCleanup(app.dependency_overrides.pop, get_subtitles_client_factory, None)

    def test_search_result_is_analyzed(self):
        self.override_client_factory(FakeSubtitlesClient)
        response = client.post('/api/analyze/online',
                               json={'query': 'hamlet', 'language': 'eng'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['messages'], [])
        self.assertIn('be', payload['analysis']['words'])

    def test_service_failure_returns_localizable_message(self):
        class FailingClient(FakeSubtitlesClient):
            def search_subtitles(self, query: str, language_code: str) -> list:
                raise RuntimeError('service unreachable')

        self.override_client_factory(FailingClient)
        response = client.post('/api/analyze/online',
                               json={'query': 'hamlet', 'language': 'eng'})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload['analysis'])
        self.assertEqual([message['code'] for message in payload['messages']],
                         ['subtitles_service_error'])

    def test_unsupported_language_is_rejected(self):
        response = client.post('/api/analyze/online',
                               json={'query': 'hamlet', 'language': 'klingon'})
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
