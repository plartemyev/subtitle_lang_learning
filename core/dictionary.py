"""Wiktionary dictionary for word tooltips (kaikki.org/wiktextract data).

The lookup database is built once by ``tools/build_dictionary.py`` into the
data directory; rows carry, per headword and part of speech, capped glosses
(in the subtitle language) and translations into the UI languages extracted
from Wiktionary (CC BY-SA 4.0 - see the README attribution). A missing
database or a missing word is a normal outcome, not an error: lookup simply
returns no entries.
"""
import json
import sqlite3

MAX_ENTRIES = 2
MAX_GLOSSES = 2
MAX_TRANSLATIONS = 5

# wiktextract part-of-speech values -> the UPOS tags the analyzer produces
WIKT_POS_TO_UPOS = {
    'noun': 'NOUN', 'verb': 'VERB', 'adj': 'ADJ', 'adv': 'ADV',
    'name': 'PROPN', 'pron': 'PRON', 'prep': 'ADP', 'postp': 'ADP',
    'prep_phrase': 'ADP', 'num': 'NUM', 'interj': 'INTJ', 'conj': 'CCONJ',
    'conjunctive': 'CCONJ', 'conjunction': 'CCONJ', 'det': 'DET',
    'article': 'DET', 'particle': 'PART',
}


class KaikkiDictionary:
    """Read-only lookup over the built sqlite database."""

    def __init__(self, db_path):
        self._db = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True,
                                   check_same_thread=False)
        self._db.row_factory = sqlite3.Row

    def lookup(self, source_code, target_locale, word, lemma='', pos=''):
        """Dictionary entries for one token: surface form first, then lemma.

        Entries tagged with the requested UPOS are preferred; Wiktionary and
        spaCy disagree on POS often, so any POS of the same headword is
        returned when nothing matches.
        """
        wanted = dict.fromkeys([word.strip().lower(), lemma.strip().lower()])
        for headword in (headword for headword in wanted if headword):
            rows = self._db.execute(
                'SELECT pos, glosses, translations FROM entries '
                'WHERE source = ? AND word = ? ORDER BY pos',
                (source_code, headword)).fetchall()
            if not rows:
                continue
            matching = [row for row in rows if row['pos'] == pos] if pos else []
            return {'word': word,
                    'entries': [self._entry_to_dict(row, target_locale)
                                for row in (matching or rows)[:MAX_ENTRIES]]}
        return {'word': word, 'entries': []}

    def _entry_to_dict(self, row, target_locale):
        translations = json.loads(row['translations']).get(target_locale, [])
        return {'pos': row['pos'],
                'glosses': json.loads(row['glosses'])[:MAX_GLOSSES],
                'translations': translations[:MAX_TRANSLATIONS]}
