#!/usr/bin/env python3
"""Terminal frontend: analyze a local SRT file or fetch one from OpenSubtitles.org."""
import argparse
import logging
import os
import sys
from typing import Optional

from core import analyzer
from core.controller import AppController
from core.languages import LANGUAGES
from ui import i18n


def init_logging(debug: bool) -> None:
    common_log_format = '[%(name)s:PID %(process)d:%(levelname)s:%(asctime)s,%(msecs)03d] %(message)s'
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt=common_log_format, datefmt='%S'))
    logging.captureWarnings(True)
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)


def ui_language_from_argv(argv) -> Optional[str]:
    """Peek at --ui-language before argparse: translations need the locale
    already active while the help texts are built."""
    for position, arg in enumerate(argv):
        if arg == '--ui-language' and position + 1 < len(argv):
            return argv[position + 1]
        if arg.startswith('--ui-language='):
            return arg.split('=', 1)[1]
    return None


def main() -> int:
    i18n.setup(ui_language_from_argv(sys.argv))
    cli = argparse.ArgumentParser()
    cli.add_argument('subtitle', type=str,
                     help=i18n.tr('cli_subtitle_help'))
    cli.add_argument('--language', type=str, default='eng', choices=sorted(LANGUAGES),
                     help=i18n.tr('cli_language_help'))
    cli.add_argument('--ui-language', type=str, choices=sorted(i18n.LOCALES),
                     default=i18n.active_locale,
                     help=i18n.tr('cli_ui_language_help'))
    cli.add_argument('--debug', action='store_true',
                     help=i18n.tr('cli_debug_help'))
    cli_args = cli.parse_args()
    init_logging(cli_args.debug)

    if cli_args.subtitle.lower().endswith('.srt') and os.path.isfile(cli_args.subtitle):
        result = analyzer.analyze_file(cli_args.subtitle, cli_args.language)
    else:
        result = AppController().load_online(cli_args.subtitle, cli_args.language)
        if result is None:
            return 1
    for word, entry in result.words.items():
        print(i18n.tr('cli_word_line', word=word, count=entry.count))
    return 0


if __name__ == '__main__':
    sys.exit(main())
