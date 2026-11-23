#!/usr/bin/env python3
"""Build the Wiktionary lookup database from kaikki.org wiktextract dumps.

Streams the raw wiktextract JSONL editions (CC BY-SA 4.0 - see README), keeps
headwords of the edition language whose entries carry glosses and/or
translations into the UI languages (de/en/ru/th), and stores capped rows into
<data-dir>/dictionary/kaikki.sqlite. Downloads are cached under
tmp/dict-build/ and reused on reruns; the English edition is ~2.8 GB gz, so
the first run takes a while.

Usage: poetry run python tools/build_dictionary.py [--languages eng,deu,rus] [--data-dir data]
"""
import argparse
import gzip
import json
import sys
import urllib.request
from pathlib import Path

try:
    # ~5x faster over the multi-GB edition dumps; a plain-stdlib fallback works too
    import orjson as _fast_json
except ImportError:
    _fast_json = None

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.dictionary import WIKT_POS_TO_UPOS  # noqa: E402  (repo-root import)

# source subtitle language -> (edition URL, cache file name, entry lang_code)
EDITIONS = {
    'eng': ('https://kaikki.org/dictionary/raw-wiktextract-data.jsonl.gz',
            'raw-wiktextract-data.jsonl.gz', 'en'),
    'deu': ('https://kaikki.org/dictionary/downloads/de/de-extract.jsonl.gz',
            'de-extract.jsonl.gz', 'de'),
    'rus': ('https://kaikki.org/dictionary/downloads/ru/ru-extract.jsonl.gz',
            'ru-extract.jsonl.gz', 'ru'),
}
TARGET_LOCALES = ('de', 'en', 'ru', 'th')
# wiktextract translation entries name the target language via `lang_code`
# (ISO 639-1 in practice); the 639-3 spellings are accepted defensively
TRANSLATION_CODES = {'de': 'de', 'deu': 'de', 'en': 'en', 'eng': 'en',
                     'ru': 'ru', 'rus': 'ru', 'th': 'th', 'tha': 'th'}
MAX_WORD_LENGTH = 80
MAX_GLOSSES = 2
MAX_GLOSS_LENGTH = 200
MAX_TRANSLATIONS_PER_TARGET = 5
MAX_TERM_LENGTH = 64
DOWNLOAD_CHUNK_BYTES = 16 * 1024 * 1024
PROGRESS_EVERY_LINES = 2_000_000
FLUSH_EVERY_ENTRIES = 20_000

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    source TEXT NOT NULL,
    word TEXT NOT NULL,
    pos TEXT NOT NULL,
    glosses TEXT NOT NULL,
    translations TEXT NOT NULL,
    PRIMARY KEY (source, word, pos)
);
CREATE INDEX IF NOT EXISTS entries_word ON entries(source, word);
"""


def download_edition(url, filename, cache_dir):
    """Fetch the edition dump once into the project tmp cache."""
    target = cache_dir / filename
    if target.exists() and target.stat().st_size > 0:
        print(f'{filename}: reusing cached download ({target.stat().st_size} bytes)')
        return target
    partial = target.with_suffix(target.suffix + '.part')
    print(f'{filename}: downloading {url} ...')
    with urllib.request.urlopen(url) as response, open(partial, 'wb') as out:
        while True:
            chunk = response.read(DOWNLOAD_CHUNK_BYTES)
            if not chunk:
                break
            out.write(chunk)
            print(f'  {partial.stat().st_size} bytes', end='\r')
    print()
    partial.replace(target)
    return target


def parse_entry(entry, source_code):
    """One JSONL line -> a database row, or None when not worth keeping.

    Only headwords of the edition language are kept, lowercased; POS is
    mapped to the analyzer's UPOS when known; glosses and per-target
    translations are capped to keep the database compact.
    """
    if entry.get('lang_code') != EDITIONS[source_code][2]:
        return None
    word = str(entry.get('word', '')).strip().lower()
    if not word or len(word) > MAX_WORD_LENGTH:
        return None
    pos = str(entry.get('pos', '')).lower()
    pos = WIKT_POS_TO_UPOS.get(pos, pos)
    glosses = []
    for sense in entry.get('senses', []):
        for gloss in sense.get('glosses', [])[:1]:
            text = gloss.strip()
            if text and text not in glosses:
                glosses.append(text[:MAX_GLOSS_LENGTH])
            if len(glosses) >= MAX_GLOSSES:
                break
        if len(glosses) >= MAX_GLOSSES:
            break
    translations = {}
    for item in entry.get('translations', []):
        locale = TRANSLATION_CODES.get(str(item.get('lang_code', item.get('code', ''))).lower())
        term = str(item.get('word', '')).strip()
        if locale not in TARGET_LOCALES or not term:
            continue
        terms = translations.setdefault(locale, [])
        if term.lower() not in [existing.lower() for existing in terms]:
            terms.append(term[:MAX_TERM_LENGTH])
    translations = {locale: terms[:MAX_TRANSLATIONS_PER_TARGET]
                    for locale, terms in sorted(translations.items())}
    if not translations and not glosses:
        return None
    return (source_code, word, pos,
            json.dumps(glosses, ensure_ascii=False),
            json.dumps(translations, ensure_ascii=False))


def build_language(source_code, db, cache_dir):
    """Stream one edition dump into the entries table."""
    url, filename, _entry_lang = EDITIONS[source_code]
    path = download_edition(url, filename, cache_dir)
    kept = 0
    lines = 0
    buffer = []
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            lines += 1
            if lines % PROGRESS_EVERY_LINES == 0:
                print(f'  {source_code}: {lines} lines, {kept} entries kept')
            try:
                entry = _fast_json.loads(line) if _fast_json else json.loads(line)
                row = parse_entry(entry, source_code)
            except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
                continue
            if row is None:
                continue
            buffer.append(row)
            kept += 1
            if len(buffer) >= FLUSH_EVERY_ENTRIES:
                db.executemany('INSERT OR IGNORE INTO entries VALUES (?, ?, ?, ?, ?)', buffer)
                buffer.clear()
    if buffer:
        db.executemany('INSERT OR IGNORE INTO entries VALUES (?, ?, ?, ?, ?)', buffer)
        buffer.clear()
    db.commit()
    print(f'{source_code}: {lines} lines -> {kept} dictionary rows')


def main():
    parser = argparse.ArgumentParser(
        description='Build the Wiktionary lookup database from kaikki.org dumps.')
    parser.add_argument('--languages', default='eng,deu,rus',
                        help='comma-separated source languages: eng,deu,rus')
    parser.add_argument('--data-dir', default=str(REPO_ROOT / 'data'))
    args = parser.parse_args()
    languages = [code.strip() for code in args.languages.split(',') if code.strip()]
    unknown = [code for code in languages if code not in EDITIONS]
    if unknown:
        parser.error(f'unsupported languages: {", ".join(unknown)}; '
                     f'supported: {", ".join(EDITIONS)}')

    import sqlite3
    db_path = Path(args.data_dir) / 'dictionary' / 'kaikki.sqlite'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = REPO_ROOT / 'tmp' / 'dict-build'
    cache_dir.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.executescript(_SCHEMA)
    for source_code in languages:
        build_language(source_code, db, cache_dir)
    db.close()
    print(f'dictionary ready: {db_path}')
    print('Data: Wiktionary via kaikki.org/wiktextract, CC BY-SA 4.0 - keep the attribution.')


if __name__ == '__main__':
    main()
