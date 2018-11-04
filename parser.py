#!/usr/bin/env python3

import srt
import logging
import argparse
import os

module_logger = logging.getLogger(__name__)
logging.captureWarnings(True)


class ModuleParameters:
    def __init__(self):
        cli = argparse.ArgumentParser()
        cli.add_argument('subtitle_file', type=str)
        cli.add_argument('--debug', action='store_true')
        cli_args = cli.parse_args()
        self.subtitle_file = cli_args.subtitle_file
        self.debug = cli_args.debug


def logger_init():
    common_log_format = '[%(name)s:PID %(process)d:%(levelname)s:%(asctime)s,%(msecs)03d] %(message)s'
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        fmt=common_log_format,
        datefmt='%S'
    )
    console_handler.setFormatter(console_formatter)
    module_logger.handlers = [console_handler]


if __name__ == '__main__':
    parameters = ModuleParameters()
    if parameters.debug:
        module_logger.setLevel('DEBUG')
    else:
        module_logger.setLevel('INFO')
    logger_init()

    assert os.path.isfile(parameters.subtitle_file)
    with open(parameters.subtitle_file, encoding='latin-1') as sub_f:
        sub_generator = srt.parse(sub_f.read())

    for sub in sub_generator:
        print(sub.content)
