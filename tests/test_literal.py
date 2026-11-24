"""Literal word-by-word dictionary view (fakes, no dictionary database)."""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.literal import LiteralDictionary, _lemma_candidates, transliterate


class FakeDictionary:
    """Scripted KaikkiDictionary: word -> rows of (pos, translations)."""

    def __init__(self, entries):
        self.entries = entries

    def lookup(self, source_code, target_locale, word, lemma='', pos=''):
        rows = self.entries.get(word.lower(), [])
        matching = [row for row in rows
                    if row['pos'].casefold() == pos.casefold()] if pos else []
        for tier in (matching, rows):
            rich = [row for row in tier if row['translations']]
            if rich:
                return {'word': word, 'entries': rich}
        return {'word': word, 'entries': rows}


class FakeReverse:
    def __init__(self, mapping):
        self.mapping = mapping

    def lookup(self, target_locale, term):
        return self.mapping.get((target_locale, term.strip().casefold()))


def words(*tokens):
    out = []
    for token in tokens:
        if isinstance(token, dict):
            out.append(token)  # idempotent: already prepared
        elif isinstance(token, tuple):
            text, lemma, pos = token
            out.append({'text': text, 'lemma': lemma, 'pos': pos})
        else:
            out.append({'text': token, 'lemma': token, 'pos': 'PUNCT'})
    return out


class TransliterateTests(unittest.TestCase):
    def test_cyrillic_keeps_capitalization(self):
        self.assertEqual(transliterate('Чтоб', 'en'), 'Chtob')
        self.assertEqual(transliterate('Встряхнись', 'en'), 'Vstryakhnis')

    def test_latin_passes_through_to_latin_targets(self):
        self.assertEqual(transliterate('Well', 'de'), 'Well')

    def test_latin_to_cyrillic(self):
        self.assertEqual(transliterate('chto', 'ru'), 'что')


class LiteralDictionaryTests(unittest.TestCase):
    def setUp(self):
        self.dictionary = LiteralDictionary(
            FakeDictionary({
                'ups and downs': [{'pos': 'NOUN',
                                   'translations': ['взлёты и паде́ния']}],
                'мужик': [{'pos': 'NOUN',
                           'translations': ['muzhik', 'man', 'guy']}],
                'well': [{'pos': 'intj', 'translations': ['ну']},
                         {'pos': 'adj', 'translations': ['здоро́вый']}],
            }),
            FakeReverse({('ru', 'i'): 'я'}))

    def translate(self, tokens, source='eng', target='ru'):
        return self.dictionary.translate(' '.join(t['text'] for t in tokens),
                                         source, target, words(*tokens))

    def test_ngram_sweep_reads_idiom_headwords(self):
        tokens = words(('ups', 'up', 'NOUN'), ('and', 'and', 'CCONJ'),
                       ('downs', 'down', 'NOUN'), '.')
        self.assertEqual(self.translate(tokens), 'взлёты и паде́ния .')

    def test_prefers_non_transliteration_translation(self):
        tokens = words(('Эй', 'эй', 'INTJ'), '!', ('мужик', 'мужик', 'NOUN'), '!')
        self.assertEqual(self.translate(tokens, target='en'), 'Ey ! man !')

    def test_pos_prefers_the_matching_sense_tier(self):
        tokens = words(('Well', 'well', 'INTJ'))
        self.assertEqual(self.translate(tokens), 'ну')

    def test_reverse_index_plugs_data_gaps(self):
        tokens = words(('I', 'i', 'PRON'))
        self.assertEqual(self.translate(tokens), 'я')

    def test_transliteration_is_the_last_resort(self):
        tokens = words(('qqq', 'qqq', 'NOUN'))
        self.assertEqual(self.translate(tokens), 'ккк')

    def test_punctuation_passes_through(self):
        tokens = words('.', ',', '!')
        self.assertEqual(self.translate(tokens), '. , !')

    def test_pymorphy_candidates_for_cyrillic_case_forms(self):
        self.assertIn('вы', _lemma_candidates('вам'))


if __name__ == '__main__':
    unittest.main()
