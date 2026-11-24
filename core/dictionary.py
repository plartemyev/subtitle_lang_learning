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

        Rows carrying translations into the target locale win over gloss-only
        rows - inflected forms usually have their own Wiktionary row with just
        a relational gloss, and spaCy tags pronouns Wiktionary calls
        determiners, so the preference applies within the headword too, not
        only across headwords. POS-matching rows are still preferred inside
        each preference tier; a headword wins over the next one only when it
        has something to serve.
        """
        plain = None  # first gloss-only result, served when nothing richer exists

        def entry(row):
            return self._entry_to_dict(row, target_locale)

        def rich_rows(rows_):
            return [row for row in rows_ if json.loads(row['translations'])
                    .get(target_locale)]

        for headword in dict.fromkeys([word.strip().lower(), lemma.strip().lower()]):
            if not headword:
                continue
            rows = self._db.execute(
                'SELECT pos, glosses, translations FROM entries '
                'WHERE source = ? AND word = ? ORDER BY pos',
                (source_code, headword)).fetchall()
            if not rows:
                continue
            # wiktextract keeps some raw POS codes ('intj') the UPOS mapping
            # does not cover; match the analyzer's tag case-insensitively
            matching = [row for row in rows
                        if row['pos'].casefold() == pos.casefold()] if pos else []
            for tier in (matching, rows):
                rich = [entry(row) for row in rich_rows(tier)[:MAX_ENTRIES]]
                if rich:
                    return {'word': word, 'entries': rich}
            if plain is None:
                served = matching or rows
                plain = {'word': word,
                         'entries': [entry(row) for row in served[:MAX_ENTRIES]]}
        return plain if plain is not None else {'word': word, 'entries': []}

    def _entry_to_dict(self, row, target_locale):
        translations = json.loads(row['translations']).get(target_locale, [])
        return {'pos': row['pos'],
                'glosses': json.loads(row['glosses'])[:MAX_GLOSSES],
                'translations': translations[:MAX_TRANSLATIONS]}


# Edition whose headwords translate INTO a given UI locale; used by the
# reverse index. The Thai edition is not part of the dictionary pipeline,
# so thai lookups fall back to transliteration upstream.
TARGET_EDITION = {'en': 'eng', 'de': 'deu', 'ru': 'rus'}


class ReverseDictionaryIndex:
    """(edition, locale, translation term) -> headword, built once from the
    dictionary database.

    Plugs single-word data gaps in the forward direction: the English
    edition carries no ru translations for the pronoun "I", but the Russian
    edition's "я" entry translates back to "I", so a missed source word can
    still resolve through its translations.
    """

    def __init__(self, path):
        self._db = sqlite3.connect(f'file:{path}?mode=ro', uri=True,
                                   check_same_thread=False)

    def lookup(self, target_locale, term):
        """Headword whose translations into ``target_locale`` contain
        ``term`` (case-insensitive); None when the index has no match or
        the locale's edition was not built."""
        edition = TARGET_EDITION.get(target_locale)
        if edition is None:
            return None
        row = self._db.execute(
            'SELECT word FROM reverse WHERE edition=? AND locale=? AND '
            'term=? ORDER BY word LIMIT 1',
            (edition, target_locale, term.strip().casefold())).fetchone()
        return row[0] if row else None


def build_reverse_index(db_path, reverse_path):
    """Derive the reverse index table from a built dictionary database.

    One row per (edition, locale, translation term): the kaikki entry whose
    translations into ``locale`` contain ``term`` maps to its headword.
    """
    source = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    target = sqlite3.connect(str(reverse_path))
    target.execute('CREATE TABLE IF NOT EXISTS reverse (edition TEXT, '
                   'locale TEXT, term TEXT, word TEXT, '
                   'PRIMARY KEY (edition, locale, term, word))')
    batch = []
    for source_code, word, translations_json in source.execute(
            'SELECT source, word, translations FROM entries'):
        for locale, terms in json.loads(translations_json).items():
            for term in terms:
                batch.append((source_code, locale,
                              term.strip().casefold(), word))
        if len(batch) >= 50_000:
            target.executemany('INSERT OR IGNORE INTO reverse VALUES '
                               '(?, ?, ?, ?)', batch)
            batch.clear()
    if batch:
        target.executemany('INSERT OR IGNORE INTO reverse VALUES '
                           '(?, ?, ?, ?)', batch)
    target.commit()
    target.close()
    source.close()
