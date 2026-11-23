"""KaikkiDictionary lookup over a small fixture database (no downloads)."""
import json
import sqlite3
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.dictionary import KaikkiDictionary

TMP_DIR = PROJECT_ROOT / 'tmp' / 'tests'

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    source TEXT NOT NULL,
    word TEXT NOT NULL,
    pos TEXT NOT NULL,
    glosses TEXT NOT NULL,
    translations TEXT NOT NULL,
    PRIMARY KEY (source, word, pos)
);
"""

FAMILY_ROW = ('eng', 'family', 'NOUN',
              json.dumps(['A nuclear group', 'A social unit']),
              json.dumps({'ru': ['семья'], 'de': ['Familie'], 'th': ['ครอบครัว']}))
VERB_ROW = ('eng', 'family', 'VERB',
            json.dumps(['To be part of a family']),
            json.dumps({}))


class KaikkiDictionaryTests(unittest.TestCase):
    def setUp(self):
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = TMP_DIR / f'dict-{self.id()}.sqlite'
        db = sqlite3.connect(self.db_path)
        db.execute(_SCHEMA)
        db.execute('INSERT OR IGNORE INTO entries VALUES (?, ?, ?, ?, ?)', FAMILY_ROW)
        db.execute('INSERT OR IGNORE INTO entries VALUES (?, ?, ?, ?, ?)', VERB_ROW)
        db.commit()
        db.close()
        self.dictionary = KaikkiDictionary(self.db_path)
        self.addCleanup(self.dictionary._db.close)

    def test_lookup_matches_surface_form_and_pos(self):
        result = self.dictionary.lookup('eng', 'ru', 'family', pos='NOUN')
        self.assertEqual(result['word'], 'family')
        self.assertEqual(len(result['entries']), 1)
        entry = result['entries'][0]
        self.assertEqual(entry['pos'], 'NOUN')
        self.assertEqual(entry['translations'], ['семья'])
        self.assertEqual(entry['glosses'][0], 'A nuclear group')

    def test_lookup_prefers_the_requested_pos_over_other_rows(self):
        # ADJ never matches the noun/verb rows: the noun entry is still served
        result = self.dictionary.lookup('eng', 'ru', 'family', pos='ADJ')
        self.assertEqual(result['entries'][0]['pos'], 'NOUN')

    def test_lookup_falls_back_to_the_lemma(self):
        result = self.dictionary.lookup('eng', 'ru', 'families', lemma='family', pos='NOUN')
        self.assertEqual(result['entries'][0]['translations'], ['семья'])

    def test_lookup_filters_translations_by_target_locale(self):
        result = self.dictionary.lookup('eng', 'th', 'family', pos='NOUN')
        self.assertEqual(result['entries'][0]['translations'], ['ครอบครัว'])

    def test_unknown_word_returns_no_entries(self):
        self.assertEqual(self.dictionary.lookup('eng', 'ru', 'zzzqx'),
                         {'word': 'zzzqx', 'entries': []})

    def test_translations_are_capped_at_read_time(self):
        db = sqlite3.connect(self.db_path)
        many = json.dumps({'ru': [f'term{i}' for i in range(10)]})
        db.execute("UPDATE entries SET translations = ? WHERE word = 'family' AND pos = 'NOUN'",
                   (many,))
        db.commit()
        db.close()
        result = self.dictionary.lookup('eng', 'ru', 'family', pos='NOUN')
        self.assertEqual(len(result['entries'][0]['translations']), 5)


if __name__ == '__main__':
    unittest.main()
