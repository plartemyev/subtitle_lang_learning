"""Qt frontend: widgets, wiring and rendering only.

All business logic lives in :mod:`core` and is reached through
:class:`core.controller.AppController`; this module never parses subtitles,
talks to OpenSubtitles or formats core events itself.
"""
import logging
import os
from pathlib import Path
from typing import Callable

import PyQt6.QtCore
from PyQt6 import QtCore, QtWidgets, uic
from PyQt6.QtCore import QDir, QUrl
from PyQt6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel

from core import translate
from core.controller import AppController, UserMessage
from core.languages import LANGUAGES
from ui.qt import messages

logger = logging.getLogger(__name__)

main_window_ui_path = Path(__file__).parent.joinpath('main_window.ui').resolve()
Ui_MainWindow, QtBaseClass = uic.loadUiType(main_window_ui_path)


def create_range_interpolator(original_min: int, original_max: int, new_min: int, new_max: int) -> Callable[[int], int]:
    original_span = original_max - original_min
    new_span = new_max - new_min

    def interpolator(original_value: int) -> int:
        return int(round(new_min + ((original_value - original_min) / original_span) * new_span))

    return interpolator


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, controller: AppController = None):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.controller = controller if controller is not None else AppController(warning_callback=self.showWarning)
        self.selected_word = ''
        self.initUI()

    def initUI(self):
        for language_code in LANGUAGES:
            self.ui.subtitlesLanguageSelect.addItem(
                messages.LANGUAGE_NAMES.get(language_code, language_code), language_code)
        self.ui.fileSelectBtn.clicked.connect(self.fileSelectionDialog)
        self.ui.translationOptionsGroup.buttonClicked.connect(self.translationOptionsChanged)
        self.ui.translateCheckBox.clicked.connect(self.translationOptionsChanged)
        self.ui.filePathInput.editingFinished.connect(self.sourceFileProvided)
        self.ui.onlineSearchTitle.editingFinished.connect(self.loadSubtitlesFromInternet)
        self.ui.onlineSearchBtn.clicked.connect(self.loadSubtitlesFromInternet)
        self.ui.translationTabWidget.tabBarClicked.connect(self.translationTabClicked)

        self.show()

    def currentLanguageCode(self) -> str:
        return self.ui.subtitlesLanguageSelect.currentData()

    def showWarning(self, message: UserMessage):
        QtWidgets.QMessageBox.warning(
            self, messages.WARNING_DIALOG_TITLE, messages.format_user_message(message))

    def fileSelectionDialog(self):
        _file = QDir.toNativeSeparators(
            QtWidgets.QFileDialog.getOpenFileName(directory=self.ui.filePathInput.text())[0]
        )
        self.ui.filePathInput.setText(_file)
        self.sourceFileProvided()

    def sourceFileProvided(self):
        _source_file = self.ui.filePathInput.text()
        if os.path.isfile(_source_file):
            self.loadSubtitlesFromFile()

    def wordInAListSelected(self, index: PyQt6.QtCore.QModelIndex):
        self.selected_word = index.data()
        entry = None
        if self.controller.current_result is not None:
            entry = self.controller.current_result.words.get(self.selected_word)
        if entry is None:
            return
        meta_line = messages.WORD_META_LINE.format(word=self.selected_word, count=entry.count)
        if entry.pos:
            meta_line += messages.POS_SUFFIX.format(pos=entry.pos.lower())
        if entry.possessive_count:
            meta_line += messages.POSSESSIVE_SUFFIX.format(count=entry.possessive_count)
        context_phrase = entry.context_phrase.text if entry.context_phrase else ''
        # TODO: Display selected word meta in a proper UI element
        self.ui.fullPhraseTextBrowser.setText(f'{meta_line}\n{messages.CONTEXT_LABEL}\n{context_phrase}')
        if self.ui.translateCheckBox.isChecked():
            if self.ui.translateSingleWordRbtn.isChecked():
                self.onlineTranslate(self.selected_word)
            else:
                self.onlineTranslate(context_phrase)

    def populate_words_list(self):
        result = self.controller.current_result
        if result is None or not result.words:
            return
        top_word_prevalence = result.top_count
        color_interpolator = create_range_interpolator(1, int(round(top_word_prevalence / 5)), 250, 0)
        words_list_model = QStandardItemModel(self.ui.wordsListView)
        self.ui.wordsListView.setModel(words_list_model)
        words_list_selection_model = self.ui.wordsListView.selectionModel()
        words_list_selection_model.currentChanged.connect(self.wordInAListSelected)
        for word, entry in result.words.items():
            item = QStandardItem(word)
            if entry.count > top_word_prevalence / 5:
                hue_value = color_interpolator(int(round(top_word_prevalence / 5)))
            else:
                hue_value = color_interpolator(entry.count)
            colored_brush = QBrush(QColor().fromHsv(hue_value, 70, 255))
            item.setBackground(colored_brush)
            words_list_model.appendRow(item)

    def loadSubtitlesFromFile(self):
        try:
            self.controller.load_from_file(self.ui.filePathInput.text(), self.currentLanguageCode())
        except Exception as e:
            logger.warning('Unable to load subtitles from file.', exc_info=e)
            self.showWarning(UserMessage('unable_to_load_file', {'path': self.ui.filePathInput.text()}))
            return
        self.populate_words_list()

    def loadSubtitlesFromInternet(self):
        result = self.controller.load_online(self.ui.onlineSearchTitle.text(), self.currentLanguageCode())
        if result is not None:
            self.populate_words_list()

    def onlineTranslate(self, text: str):
        self.ui.webEngineView.load(QUrl(translate.build_translate_url(text)))

    def translationOptionsChanged(self):
        if self.ui.translateCheckBox.isChecked():
            self.ui.translationTabWidget.setEnabled(True)
            self.ui.webEngineView.setEnabled(True)
            self.ui.translateSingleWordRbtn.setEnabled(True)
            self.ui.translatePhraseRbtn.setEnabled(True)
            if self.ui.translateSingleWordRbtn.isChecked():
                self.onlineTranslate(self.selected_word)
            else:
                selected_phrase = ''
                if self.controller.current_result is not None:
                    entry = self.controller.current_result.words.get(self.selected_word)
                    if entry is not None and entry.context_phrase:
                        selected_phrase = entry.context_phrase.text
                if selected_phrase:
                    self.onlineTranslate(selected_phrase)
        else:
            self.ui.webEngineView.setUrl(QtCore.QUrl("about:blank"))
            self.ui.webEngineView.setEnabled(False)
            self.ui.translationTabWidget.setEnabled(False)
            self.ui.translateSingleWordRbtn.setEnabled(False)
            self.ui.translatePhraseRbtn.setEnabled(False)

    def translationTabClicked(self):
        current_tab = self.ui.translationTabWidget.currentWidget().objectName()
        logger.info(f'Tab {current_tab} is active')
