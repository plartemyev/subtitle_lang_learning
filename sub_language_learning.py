#!/usr/bin/env python3

import logging
import os
import sys
from typing import Callable

import parser
import srt
import traceback

import PyQt5
from PyQt5.QtCore import QDir, QUrl
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor

# python3 -m PyQt5.uic.pyuic main_window.ui -o main_window.py
# from ui.main_window import *

from PyQt5 import uic, QtWidgets, QtCore

Ui_MainWindow, QtBaseClass = uic.loadUiType('ui/main_window.ui')


def create_range_interpolator(original_min: int, original_max: int, new_min: int, new_max: int) -> Callable[[int], int]:
    original_span = original_max - original_min
    new_span = new_max - new_min

    def interpolator(original_value: int) -> int:
        return int(round(new_min + ((original_value - original_min) / original_span) * new_span))

    return interpolator


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.initUI()
        self.subtitles = {}
        self.selected_word = ''
        self.loaded_subs_for_title = ''
        self.loaded_subs_for_lang = ''

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
        full_phrase = self.subtitles.get(self.selected_word, {}).get('sub_text', {})
        phrase_meta = self.subtitles.get(self.selected_word, {}).get('sub_object', {})
        self.ui.fullPhraseTextBrowser.setText(f'Word "{self.selected_word}" encountered {word_count} times\n'
                                              f'Context:\n{full_phrase}')
        if self.ui.translateCheckBox.isChecked():
            if self.ui.translateSingleWordRbtn.isChecked():
                self.onlineTranslate(self.selected_word)
            else:
                self.onlineTranslate(full_phrase)

    def populate_words_list(self):
        top_word_prevalence = self.subtitles.get(tuple(self.subtitles.keys())[0]).get('count', 0)
        color_interpolator = create_range_interpolator(1, int(round(top_word_prevalence / 5)), 250, 0)
        words_list_model = QStandardItemModel(self.ui.wordsListView)
        self.ui.wordsListView.setModel(words_list_model)
        words_list_selection_model = self.ui.wordsListView.selectionModel()
        words_list_selection_model.currentChanged.connect(self.wordInAListSelected)
        for word in self.subtitles.keys():
            item = QStandardItem(word)
            word_prevalence = self.subtitles.get(word, {}).get('count', 0)
            if word_prevalence > top_word_prevalence / 5:
                hue_value = color_interpolator(int(round(top_word_prevalence / 5)))
            else:
                hue_value = color_interpolator(word_prevalence)
            colored_brush = QBrush(QColor().fromHsv(hue_value, 70, 255))
            item.setBackground(colored_brush)
            words_list_model.appendRow(item)

    def loadSubtitlesFromFile(self):
        parser_parameters = ParserParameters(self.ui.filePathInput.text(), False)
        raw_sub = parser.read_subtitles_file(parser_parameters.subtitle)
        sub_generator = srt.parse(raw_sub)
        self.subtitles = parser.parse_subtitles(sub_generator)
        self.populate_words_list()

    def loadSubtitlesFromInternet(self):
        if len(self.ui.onlineSearchTitle.text()) < 4 or (
                self.ui.onlineSearchTitle.text() == self.loaded_subs_for_title and
                self.ui.subtitlesLanguageSelect.currentText() == self.loaded_subs_for_lang
        ):
            return
        params = ParserParameters(
            self.ui.onlineSearchTitle.text(), False, self.ui.subtitlesLanguageSelect.currentText()
        )
        self.loaded_subs_for_title = params.subtitle
        self.loaded_subs_for_lang = self.ui.subtitlesLanguageSelect.currentText()
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
            except Exception as e:
                app_logger.info('Unable to parse subtitle file. Will try another one if there is some')
                app_logger.debug('Traceback:\n{}'.format('\n'.join(traceback.format_tb(e.__traceback__))))
                sub_index += 1
                continue
        if sub_index == len(online_subs_available):
            app_logger.warning(f'Unable to parse any subtitle file out of {len(online_subs_available)}')
            return  # Unable to decode any subs
        self.populate_words_list()

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
                selected_phrase = self.subtitles.get(self.selected_word, {}).get('sub_text', {})
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


def logger_init(logger, lvl):
    common_log_format = '[%(filename)s:line %(lineno)d:%(asctime)s:%(levelname)s] %(message)s'
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        fmt=common_log_format,
        datefmt='%H.%M.%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    logger.setLevel(lvl)


if __name__ == '__main__':
    logging.captureWarnings(True)
    app_logger = logging.getLogger('SLL')
    parser.logger = logging.getLogger('SLL.parser')
    logger_init(app_logger, logging.INFO)

    app = QtWidgets.QApplication(sys.argv)
    app_ui = MainWindow()

    sys.exit(app.exec_())
