#!/usr/bin/env python3

import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Callable

import PyQt6
import srt
from PyQt6 import QtCore, QtWidgets, uic
from PyQt6.QtCore import QDir, QUrl
from PyQt6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel

import sub_parser

# For development, it might be easier to work with PyQt ui declared as .py files:
# python3 -m PyQt6.uic.pyuic ui_resources/main_window.ui -o ui_resources/main_window.py
# from ui_resources.main_window import *
# And ten comment out lines 22-23
main_window_ui_path = Path(__file__).parent.joinpath('ui_resources').joinpath('main_window.ui').resolve()
Ui_MainWindow, QtBaseClass = uic.loadUiType(main_window_ui_path)


class UIWarningHandler(logging.Handler):
    def __init__(self, parent_widget):
        super().__init__()
        self.widget = parent_widget

    def emit(self, record: logging.LogRecord) -> None:
        QtWidgets.QMessageBox.warning(self.widget, record.levelname, record.message)


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

    def wordInAListSelected(self, item: PyQt6.QtCore.QModelIndex):
        self.selected_word = item.data()
        word_count = self.subtitles.get(self.selected_word, {}).get('count', 0)
        full_phrase = self.subtitles.get(self.selected_word, {}).get('sub_text', '')
        # TODO: Display selected word meta in a proper UI element
        # phrase_meta = self.subtitles.get(self.selected_word, {}).get('sub_object', {})
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
        parser_parameters = sub_parser.ModuleParameters(self.ui.filePathInput.text())
        raw_sub = sub_parser.read_subtitles_file(parser_parameters.subtitle)
        sub_generator = srt.parse(raw_sub)
        self.subtitles = sub_parser.parse_subtitles(sub_generator)
        self.populate_words_list()

    def loadSubtitlesFromInternet(self):
        if len(self.ui.onlineSearchTitle.text()) < 4 or (
                self.ui.onlineSearchTitle.text() == self.loaded_subs_for_title and
                self.ui.subtitlesLanguageSelect.currentText() == self.loaded_subs_for_lang
        ):
            return
        params = sub_parser.ModuleParameters(
            self.ui.onlineSearchTitle.text(), self.ui.subtitlesLanguageSelect.currentText()
        )
        self.loaded_subs_for_title = params.subtitle
        self.loaded_subs_for_lang = self.ui.subtitlesLanguageSelect.currentText()
        try:
            ost_handle = sub_parser.OpenSubtitles()
            ost_handle.login('', '')
            online_subs_available = sub_parser.search_subtitles(params.subtitle, params.language, ost_handle)
        except Exception as e:
            app_logger.warning('Problem with OpenSubtitles.org communication.', exc_info=e)
        else:
            if (not online_subs_available) or len(online_subs_available) == 0:
                app_logger.warning('No subtitles found')
                return
            for sub in online_subs_available:
                try:
                    online_sub_id = sub.get('IDSubtitleFile')
                    online_sub_name = sub.get('SubFileName')
                    raw_sub = sub_parser.download_subtitle(ost_handle, online_sub_id, online_sub_name)
                    sub_generator = srt.parse(raw_sub)
                    self.subtitles = sub_parser.parse_subtitles(sub_generator)
                    app_logger.info('Successfully parsed subtitle file')
                    break
                except Exception as e:
                    app_logger.info('Unable to parse subtitle file. Will try another one if there is some')
                    app_logger.debug('Traceback:\n{}'.format('\n'.join(traceback.format_tb(e.__traceback__))))
                    continue
            else:
                app_logger.warning(f'Unable to parse any subtitle file out of {len(online_subs_available)}')
                return  # Unable to decode any subs
            self.populate_words_list()

    def onlineTranslate(self, text: str):
        translate_url = QUrl(
            f'https://translate.google.com/?sl=auto&tl=ru&op=translate&text={text}'
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
                if selected_phrase := self.subtitles.get(self.selected_word, {}).get('sub_text', ''):
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


def logger_init(logger, lvl):
    common_log_format = '[%(filename)s:line %(lineno)d:%(asctime)s:%(levelname)s] %(message)s'
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        fmt=common_log_format,
        datefmt='%H.%M.%S'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(lvl)
    logger.addHandler(console_handler)
    logger.setLevel(lvl)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app_ui = MainWindow()

    logging.captureWarnings(True)
    app_logger = logging.getLogger('SLL')
    sub_parser.logger = logging.getLogger('SLL.parser')
    logger_init(app_logger, logging.INFO)
    ui_warning_handler = UIWarningHandler(app_ui)
    ui_warning_handler.setLevel(logging.WARNING)
    app_logger.addHandler(ui_warning_handler)

    sys.exit(app.exec())
