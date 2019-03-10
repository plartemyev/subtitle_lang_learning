#!/usr/bin/env python3

import logging
import os
import sys

import parser
import srt

import PyQt5
from PyQt5.QtCore import QDir, QUrl
from PyQt5.QtGui import QStandardItemModel, QStandardItem

# python3 -m PyQt5.uic.pyuic main_window.ui -o main_window.py
from ui.main_window import *

# from PyQt5 import uic, QtWidgets
# Ui_MainWindow, QtBaseClass = uic.loadUiType('ui/main_window.ui')


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.initUI()
        self.subtitles = {}
        self.selected_word = ''

    def initUI(self):
        self.ui.fileSelectBtn.clicked.connect(self.fileSelectionDialog)
        self.ui.translationOptionsGroup.buttonClicked.connect(self.translationOptionsChanged)
        self.ui.translateCheckBox.clicked.connect(self.translationOptionsChanged)
        self.ui.filePathInput.editingFinished.connect(self.sourceFileProvided)
        self.ui.onlineSearchTitle.editingFinished.connect(self.loadSubtitlesFromInternet)
        self.ui.onlineSearchBtn.clicked.connect(self.loadSubtitlesFromInternet)
        self.ui.translationTabWidget.tabBarClicked.connect(self.translationTabClicked)

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
            self.loadSubtitlesFromFile()

    def wordInAListSelected(self, item: PyQt5.QtCore.QModelIndex):
        self.selected_word = item.data()
        word_count = self.subtitles.get(self.selected_word, {}).get('count', 0)
        full_phrase = self.subtitles.get(self.selected_word, {}).get('sub_object', {}).content
        self.ui.fullPhraseTextBrowser.setText(f'Word "{self.selected_word}" encountered {word_count} times\n'
                                              f'Context:\n{full_phrase}')
        if self.ui.translateCheckBox.isChecked():
            if self.ui.translateSingleWordRbtn.isChecked():
                self.onlineTranslate(self.selected_word)
            else:
                self.onlineTranslate(full_phrase)

    def loadSubtitlesFromFile(self):
        parser_parameters = ParserParameters(self.ui.filePathInput.text(), False)
        raw_sub = parser.read_subtitles_file(parser_parameters.subtitle)
        sub_generator = srt.parse(raw_sub)
        self.subtitles = parser.parse_subtitles(sub_generator)
        words_list_model = QStandardItemModel(self.ui.wordsListView)
        self.ui.wordsListView.setModel(words_list_model)
        words_list_selection_model = self.ui.wordsListView.selectionModel()
        words_list_selection_model.currentChanged.connect(self.wordInAListSelected)
        for word in self.subtitles.keys():
            item = QStandardItem(word)
            words_list_model.appendRow(item)

    def loadSubtitlesFromInternet(self):
        if len(self.ui.onlineSearchTitle.text()) < 4:
            return
        params = ParserParameters(
            self.ui.onlineSearchTitle.text(), False, self.ui.subtitlesLanguageSelect.currentText()
        )
        ost_handle = parser.OpenSubtitles()
        ost_handle.login('', '', parser.opensubtitles_lang, parser.opensubtitles_ua)
        online_subs_available = parser.search_subtitles(params.subtitle, params.language, ost_handle)
        if (not online_subs_available) or len(online_subs_available) == 0:
            return  # todo show alert that there were no subtitles found
        sub_index = 0
        for sub in online_subs_available:
            try:
                online_sub_id = online_subs_available[sub_index].get('IDSubtitleFile')
                online_sub_name = online_subs_available[sub_index].get('SubFileName')
                raw_sub = parser.download_subtitle(ost_handle, online_sub_id, online_sub_name)
                sub_generator = srt.parse(raw_sub)
                self.subtitles = parser.parse_subtitles(sub_generator)
                app_logger.info('Successfully parsed subtitle file')
                break
            except srt.SRTParseError as e:
                app_logger.info('Unable to parse subtitle file. Will try another one if there is some')
                app_logger.warning(e)
                sub_index += 1
                continue
        if sub_index == len(online_subs_available):
            app_logger.warning(f'Unable to parse any subtitle file out of {len(online_subs_available)}')
            return  # Unable to decode any subs
        words_list_model = QStandardItemModel(self.ui.wordsListView)
        self.ui.wordsListView.setModel(words_list_model)
        words_list_selection_model = self.ui.wordsListView.selectionModel()
        words_list_selection_model.currentChanged.connect(self.wordInAListSelected)
        for word in self.subtitles.keys():
            item = QStandardItem(word)
            words_list_model.appendRow(item)

    def onlineTranslate(self, text: str):
        translate_url = QUrl(
            f'https://translate.google.com/m/translate#view=home&op=translate&sl=auto&tl=ru&text={text}'
        )
        self.ui.webEngineView.load(translate_url)

    def translationOptionsChanged(self):
        if self.ui.translateCheckBox.isChecked():
            self.ui.translationTabWidget.setEnabled(True)
            self.ui.webEngineView.setEnabled(True)
            self.ui.translateSingleWordRbtn.setEnabled(True)
            self.ui.translatePhraseRbtn.setEnabled(True)
            if self.ui.translateSingleWordRbtn.isChecked():
                self.onlineTranslate(self.selected_word)
            else:
                selected_phrase = self.subtitles.get(self.selected_word, {}).get('sub_object', {}).content
                self.onlineTranslate(selected_phrase)
        else:
            self.ui.webEngineView.setUrl(QtCore.QUrl("about:blank"))
            self.ui.webEngineView.setEnabled(False)
            self.ui.translationTabWidget.setEnabled(False)
            self.ui.translateSingleWordRbtn.setEnabled(False)
            self.ui.translatePhraseRbtn.setEnabled(False)

    def translationTabClicked(self):
        current_tab = self.ui.translationTabWidget.currentWidget().objectName()
        app_logger.info(f'Tab {current_tab} is active')


class ParserParameters(parser.ModuleParameters):
    def __init__(self, sub_file: str, debug: bool, language=''):
        self.subtitle = sub_file
        self.debug = debug
        self.language = language


def logger_init():
    common_log_format = '[%(name)s:PID %(process)d:%(levelname)s:%(asctime)s,%(msecs)03d] %(message)s'
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        fmt=common_log_format,
        datefmt='%S'
    )
    console_handler.setFormatter(console_formatter)
    logging.basicConfig(level=logging.INFO, handlers=[console_handler])


if __name__ == '__main__':
    logging.captureWarnings(True)
    app_logger = logging.getLogger(__name__)
    logger_init()

    app = QtWidgets.QApplication(sys.argv)
    app_ui = MainWindow()

    sys.exit(app.exec_())
