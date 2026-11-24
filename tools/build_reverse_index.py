#!/usr/bin/env python3
"""Rebuild the reverse translation index (standalone, one-time preparation).

Derives data/dictionary/reverse.sqlite from the built dictionary database:
one row per (edition, locale, translation term), mapping a target-language
term back to the headword whose translations contain it. The literal
word-by-word view consults it when the forward lookup has no translation
for a token (e.g. the English edition carries no ru translations for the
pronoun "I", but the Russian edition's "я" entry translates back to "I").
tools/build_dictionary.py runs this automatically; this tool exists for
rebuilds without re-streaming the kaikki dumps.

Usage: poetry run python tools/build_reverse_index.py [--data-dir data]
"""
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.dictionary import build_reverse_index  # noqa: E402  (repo-root import)


def main():
    parser = argparse.ArgumentParser(
        description='Rebuild the reverse translation index from the built '
                    'dictionary database.')
    parser.add_argument('--data-dir', default=str(REPO_ROOT / 'data'))
    args = parser.parse_args()
    db_path = Path(args.data_dir) / 'dictionary' / 'kaikki.sqlite'
    reverse_path = Path(args.data_dir) / 'dictionary' / 'reverse.sqlite'
    if not db_path.exists():
        parser.error(f'dictionary database not found: {db_path} - run '
                     f'tools/build_dictionary.py first')
    if reverse_path.exists():
        reverse_path.unlink()
    build_reverse_index(db_path, reverse_path)
    print(f'reverse index ready: {reverse_path}')


if __name__ == '__main__':
    main()
