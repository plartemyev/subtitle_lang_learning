#!/usr/bin/env python3

import sys
import os
import logging

from PyQt5.QtGui import QStandardItemModel, QStandardItem

import parser
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QDir

from ui.main_window import *
# Ui_MainWindow, QtBaseClass = uic.loadUiType('ui/main_window.ui')


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.initUI()

    def initUI(self):
        # self.ui.sourceDirSelectBtn.clicked.connect(self.dirSelectionDialog)
        self.ui.fileSelectBtn.clicked.connect(self.fileSelectionDialog)
        # self.ui.targetDirSelectBtn.clicked.connect(self.dirSelectionDialog)
        self.ui.filePathInput.editingFinished.connect(self.sourceFileProvided)
        # self.ui.operationModeRbtnGroup.buttonClicked.connect(self.operationModeChanged)
        # self.ui.commenceBtn.clicked.connect(self.commenceProcessing)
        # self.ui.progressBar.hide()
        self.show()

    def fileSelectionDialog(self):
        if self.sender().objectName() == 'fileSelectBtn':
            _file = QDir.toNativeSeparators(
                QtWidgets.QFileDialog.getOpenFileName(directory=self.ui.filePathInput.text())[0]
            )
            self.ui.filePathInput.setText(_file)
            self.sourceFileProvided()

    def sourceFileProvided(self):
        _source_file = self.ui.filePathInput.text()
        if os.path.isfile(_source_file):
            self.commenceProcessing()

    def commenceProcessing(self):
        parser_parameters = ParserParameters(self.ui.filePathInput.text(), False)
        subtitles = parser.read_subtitles(parser_parameters)
        app_logger.info(f'Found {len(subtitles)} subtitle entries')
        # for k, v in subtitles.items():
        #     print(f'Word: {k} \t Count: {v["count"]}')
        words_list_model = QStandardItemModel(self.ui.wordsListView)
        self.ui.wordsListView.setModel(words_list_model)
        for word in subtitles.keys():
            item = QStandardItem(word)
            words_list_model.appendRow(item)


class ParserParameters(parser.ModuleParameters):
    def __init__(self, sub_file: str, debug: bool):
        self.subtitle_file = sub_file
        self.debug = debug


def logger_init():
    common_log_format = '[%(name)s:PID %(process)d:%(levelname)s:%(asctime)s,%(msecs)03d] %(message)s'
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        fmt=common_log_format,
        datefmt='%S'
    )
    console_handler.setFormatter(console_formatter)
    app_logger.handlers = [console_handler]


if __name__ == '__main__':
    logging.captureWarnings(True)
    app_logger = logging.getLogger(__name__)
    app_logger.setLevel('INFO')
    logger_init()

    app = QtWidgets.QApplication(sys.argv)
    app_ui = MainWindow()

    sys.exit(app.exec_())
