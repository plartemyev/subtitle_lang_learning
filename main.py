#!/usr/bin/env python3
"""Qt frontend entry point."""
import logging
import sys

from PyQt6 import QtWidgets

from core.env import load_dotenv
from ui.qt.main_window import MainWindow


def init_logging(level: int) -> None:
    common_log_format = '[%(filename)s:line %(lineno)d:%(asctime)s:%(levelname)s] %(message)s'
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(fmt=common_log_format, datefmt='%H.%M.%S'))
    console_handler.setLevel(level)
    logging.captureWarnings(True)
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(level)


def main() -> int:
    init_logging(logging.INFO)
    load_dotenv()  # OLLAMA_*/LLAMA_* wiring for the engines (README)
    app = QtWidgets.QApplication(sys.argv)
    MainWindow()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
