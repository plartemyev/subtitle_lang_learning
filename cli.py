#!/usr/bin/env python3
"""Terminal frontend: analyze a local SRT file or fetch one from OpenSubtitles.org."""
import argparse
import logging
import os
import sys

from core import analyzer
from core.controller import AppController
from core.languages import LANGUAGES


def init_logging(debug: bool) -> None:
    common_log_format = '[%(name)s:PID %(process)d:%(levelname)s:%(asctime)s,%(msecs)03d] %(message)s'
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt=common_log_format, datefmt='%S'))
    logging.captureWarnings(True)
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)


def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument('subtitle', type=str,
                     help='path to an SRT file, or a movie/series title to search online')
    cli.add_argument('--language', type=str, default='eng', choices=sorted(LANGUAGES),
                     help='subtitle language code (default: %(default)s)')
    cli.add_argument('--debug', action='store_true')
    cli_args = cli.parse_args()
    init_logging(cli_args.debug)

    if cli_args.subtitle.lower().endswith('.srt') and os.path.isfile(cli_args.subtitle):
        result = analyzer.analyze_file(cli_args.subtitle, cli_args.language)
    else:
        result = AppController().load_online(cli_args.subtitle, cli_args.language)
        if result is None:
            return 1
    for word, entry in result.words.items():
        print(f'Word: {word} \t Count: {entry.count}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
