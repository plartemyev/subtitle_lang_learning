"""KaikkiDictionary lookup over a small fixture database (no downloads)."""
import json
import sqlite3
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.dictionary import KaikkiDictionary, ReverseDictionaryIndex, build_reverse_index

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
FAMILIES_ROW = ('eng', 'families', 'NOUN',
                json.dumps(['Plural of family']),
                json.dumps({}))
YOUR_DET_ROW = ('eng', 'your', 'DET',
                json.dumps(['Belonging to you']),
                json.dumps({'ru': ['твой', 'ваш']}))
YOUR_PRON_ROW = ('eng', 'your', 'PRON',
                 json.dumps(['Honorific form of you']),
                 json.dumps({}))
DO_VERB_ROW = ('eng', 'do', 'VERB',
               json.dumps(['To perform; to execute.']),
               json.dumps({'ru': ['де́лать']}))
DO_NOUN_ROW = ('eng', 'do', 'NOUN',
               json.dumps(['A party or social event.']),
               json.dumps({'ru': ['вечери́нка']}))
LOOK_INTJ_ROW = ('eng', 'look', 'intj',
                 json.dumps(['Pay attention.']),
                 json.dumps({'ru': ['смотри́']}))
LOOK_NOUN_ROW = ('eng', 'look', 'NOUN',
                 json.dumps(['The action of looking.']),
                 json.dumps({'ru': ['взгляд']}))
LOOK_VERB_ROW = ('eng', 'look', 'VERB',
                 json.dumps(['To try to see.']),
                 json.dumps({'ru': ['смотре́ть']}))
IF_CCONJ_ROW = ('eng', 'if', 'CCONJ',
                json.dumps(['Supposing that.']),
                json.dumps({'ru': ['ли']}))
ALL_ROWS = (FAMILY_ROW, VERB_ROW, FAMILIES_ROW, YOUR_DET_ROW, YOUR_PRON_ROW,
            DO_VERB_ROW, DO_NOUN_ROW, LOOK_INTJ_ROW, LOOK_NOUN_ROW, LOOK_VERB_ROW,
            IF_CCONJ_ROW)


class KaikkiDictionaryTests(unittest.TestCase):
    def setUp(self):
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = TMP_DIR / f'dict-{self.id()}.sqlite'
        db = sqlite3.connect(self.db_path)
        db.execute(_SCHEMA)
        for row in ALL_ROWS:
            db.execute('INSERT OR IGNORE INTO entries VALUES (?, ?, ?, ?, ?)', row)
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

    def test_gloss_only_surface_row_does_not_shadow_the_lemma(self):
        # inflected forms have their own Wiktionary row, gloss-only; the
        # lemma's translations must still surface for the tooltip
        result = self.dictionary.lookup('eng', 'ru', 'families', lemma='family', pos='NOUN')
        self.assertEqual(result['entries'][0]['pos'], 'NOUN')
        self.assertEqual(result['entries'][0]['translations'], ['семья'])

    def test_gloss_only_rows_are_served_when_nothing_has_translations(self):
        result = self.dictionary.lookup('eng', 'ru', 'families', lemma='zzzqx')
        self.assertEqual(result['entries'][0]['glosses'], ['Plural of family'])

    def test_rich_rows_of_another_pos_shadow_the_gloss_only_pos_match(self):
        # spaCy tags 'your' PRON, Wiktionary files the translations under DET
        result = self.dictionary.lookup('eng', 'ru', 'your', lemma='your', pos='PRON')
        self.assertEqual(result['entries'][0]['pos'], 'DET')
        self.assertEqual(result['entries'][0]['translations'], ['твой', 'ваш'])

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

    def test_auxiliary_pos_matches_the_verb_rows(self):
        # spaCy tags auxiliary 'do' AUX; without the AUX->VERB sibling the
        # alphabetically first noun row ("a big do") won and served вечеринка
        result = self.dictionary.lookup('eng', 'ru', 'do', lemma='do', pos='AUX')
        self.assertEqual(result['entries'][0]['pos'], 'VERB')
        self.assertEqual(result['entries'][0]['translations'], ['де́лать'])

    def test_subordinator_pos_matches_conjunction_rows(self):
        # spaCy tags subordinators (if, because) SCONJ, Wiktionary files them
        # under plain conjunction rows
        result = self.dictionary.lookup('eng', 'ru', 'if', lemma='if', pos='SCONJ')
        self.assertEqual(result['entries'][0]['pos'], 'CCONJ')

    def test_lowercase_rows_rank_case_insensitively(self):
        # legacy lowercase rows ('intj' from older builds) used to sink behind
        # every uppercase UPOS row and vanish under the read-time entry cap
        result = self.dictionary.lookup('eng', 'ru', 'look', lemma='look', pos='X')
        self.assertEqual([entry['pos'] for entry in result['entries']],
                         ['intj', 'NOUN'])


class ReverseDictionaryIndexTests(unittest.TestCase):
    def setUp(self):
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = TMP_DIR / f'reverse-src-{self.id()}.sqlite'
        self.reverse_path = TMP_DIR / f'reverse-{self.id()}.sqlite'
        db = sqlite3.connect(self.db_path)
        db.execute(_SCHEMA)
        YA_ROW = ('rus', 'я', 'PRON', json.dumps(['First person singular.']),
                  json.dumps({'en': ['I'], 'de': ['ich']}))
        db.execute('INSERT OR IGNORE INTO entries VALUES (?, ?, ?, ?, ?)', YA_ROW)
        db.commit()
        db.close()
        build_reverse_index(self.db_path, self.reverse_path)
        self.index = ReverseDictionaryIndex(self.reverse_path)
        self.addCleanup(self.index._db.close)

    def test_lookup_matches_terms_of_the_source_language(self):
        # the Russian edition's 'я' entry translates back to 'I': the term is
        # matched against the source locale column of the target edition
        self.assertEqual(self.index.lookup('eng', 'ru', 'I'), 'я')
        self.assertIsNone(self.index.lookup('eng', 'ru', 'zzzqx'))

    def test_unbuilt_target_editions_yield_no_match(self):
        self.assertIsNone(self.index.lookup('eng', 'th', 'I'))


class ConcurrentLookupTests(unittest.TestCase):
    """The web threadpool and the Qt worker threads share one instance."""

    WORDS = ['family', 'do', 'look', 'your', 'if', 'families'] * 8

    def test_parallel_lookups_over_one_dictionary_are_clean(self):
        # uvicorn burst-fires ~10 token lookups at once; unsynchronized
        # multi-call sequences on the shared connection answered
        # SQLITE_MISUSE / cross-read rows (web UI 500s)
        self.dictionary = KaikkiDictionary(self._build_db())
        self.addCleanup(self.dictionary._db.close)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(
                lambda word: self.dictionary.lookup('eng', 'ru', word, lemma=word,
                                                    pos='NOUN'),
                self.WORDS))
        self.assertEqual(len(results), len(self.WORDS))
        for word, result in zip(self.WORDS, results):
            self.assertEqual(result['word'], word)

    def _build_db(self):
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        db_path = TMP_DIR / f'dict-concurrent-{self.id()}.sqlite'
        db = sqlite3.connect(db_path)
        db.execute(_SCHEMA)
        for row in ALL_ROWS:
            db.execute('INSERT OR IGNORE INTO entries VALUES (?, ?, ?, ?, ?)', row)
        db.commit()
        db.close()
        return db_path


if __name__ == '__main__':
    unittest.main()
