"""Qt frontend: widgets, wiring and rendering only.

All business logic lives in :mod:`core` and is reached through
:class:`core.controller.AppController`; this module never parses subtitles,
talks to OpenSubtitles or formats core events itself. All display text comes
from the shared localization adapter :mod:`ui.i18n`, applied by
:func:`MainWindow._retranslate_ui` (the .ui file stays layout-only).
"""
import logging
import os
from pathlib import Path
from typing import Callable

import PyQt6.QtCore
from PyQt6 import QtCore, QtWidgets, uic
from PyQt6.QtCore import QDir, QUrl
from PyQt6.QtGui import (QAction, QActionGroup, QBrush, QColor, QStandardItem,
                         QStandardItemModel)

from core import translate
from core.controller import AppController, UserMessage
from core.languages import LANGUAGES
from ui import i18n

logger = logging.getLogger(__name__)

main_window_ui_path = Path(__file__).parent.joinpath('main_window.ui').resolve()
Ui_MainWindow, QtBaseClass = uic.loadUiType(main_window_ui_path)

# Static trilingual title: readable no matter which locale is active, so the
# override stays discoverable even when the wrong language was auto-selected.
LANGUAGE_MENU_TITLE = 'Language · Язык · Sprache'
NATIVE_LANGUAGE_NAMES = {
    'de': 'Deutsch',
    'en': 'English',
    'ru': 'Русский',
}

SETTINGS_ORGANIZATION = 'subtitle_lang_learning'
SETTINGS_APPLICATION = 'gui'
SETTINGS_LANGUAGE_KEY = 'ui_language'

# The translation provider rate-limits by IP: coalesce rapid word clicks and
# radio switches into a single request for the last selection.
TRANSLATE_DEBOUNCE_MS = 400


def _app_settings() -> QtCore.QSettings:
    """Persistent UI settings; module-level to stay injectable in tests."""
    return QtCore.QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)


def create_range_interpolator(original_min: int, original_max: int, new_min: int, new_max: int) -> Callable[[int], int]:
    original_span = original_max - original_min
    new_span = new_max - new_min

    def interpolator(original_value: int) -> int:
        return int(round(new_min + ((original_value - original_min) / original_span) * new_span))

    return interpolator


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, controller: AppController = None, language_code: str = None):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.controller = controller if controller is not None else AppController(warning_callback=self.showWarning)
        self.selected_word = ''
        if language_code is None:
            # Manual override wins, then the system locale; i18n.setup()
            # validates both and falls back to the default locale.
            language_code = _app_settings().value(SETTINGS_LANGUAGE_KEY) \
                or QtCore.QLocale.system().name()[:2]
        i18n.setup(language_code)
        self.initUI()

    def initUI(self):
        self._build_language_menu()
        self.ui.fileSelectBtn.clicked.connect(self.fileSelectionDialog)
        self.ui.translationOptionsGroup.buttonClicked.connect(self.translationOptionsChanged)
        self.ui.translateCheckBox.clicked.connect(self.translationOptionsChanged)
        self.ui.filePathInput.editingFinished.connect(self.sourceFileProvided)
        self.ui.onlineSearchTitle.editingFinished.connect(self.loadSubtitlesFromInternet)
        self.ui.onlineSearchBtn.clicked.connect(self.loadSubtitlesFromInternet)
        self.ui.translationTabWidget.tabBarClicked.connect(self.translationTabClicked)
        self._translate_timer = QtCore.QTimer(self)
        self._translate_timer.setSingleShot(True)
        self._translate_timer.timeout.connect(self._translate_current_selection)
        self._retranslate_ui()
        self.show()

    def _build_language_menu(self):
        language_menu = self.menuBar().addMenu(LANGUAGE_MENU_TITLE)
        actions_group = QActionGroup(self)
        self._language_actions = {}
        for locale_code in i18n.LOCALES:
            action = QAction(NATIVE_LANGUAGE_NAMES[locale_code], self)
            action.setCheckable(True)
            action.setChecked(locale_code == i18n.active_locale)
            action.triggered.connect(
                lambda checked, code=locale_code: self._switch_language(code))
            actions_group.addAction(action)
            language_menu.addAction(action)
            self._language_actions[locale_code] = action

    def _switch_language(self, language_code: str):
        if language_code == i18n.active_locale:
            return
        _app_settings().setValue(SETTINGS_LANGUAGE_KEY, language_code)
        i18n.setup(language_code)
        self._retranslate_ui()

    def _retranslate_ui(self):
        self.setWindowTitle(i18n.tr('window_title'))
        self._set_tab_text(self.ui.sourceSelectionTabs, 'onlineSource', 'tab_online_source')
        self._set_tab_text(self.ui.sourceSelectionTabs, 'fileSourceSRT', 'tab_file_source')
        self._set_tab_text(self.ui.translationTabWidget, 'translateOnlineTab', 'tab_translate_online')
        self._set_tab_text(self.ui.translationTabWidget, 'translateLocallyTab', 'tab_translate_local')
        self.ui.filePathInput.setPlaceholderText(i18n.tr('placeholder_subtitle_file'))
        self.ui.fileSelectBtn.setText(i18n.tr('button_select_srt'))
        self.ui.onlineSearchBtn.setText(i18n.tr('button_search'))
        self.ui.translateCheckBox.setText(i18n.tr('checkbox_translate'))
        self.ui.translateSingleWordRbtn.setText(i18n.tr('radio_single_word'))
        self.ui.translatePhraseRbtn.setText(i18n.tr('radio_whole_phrase'))
        self._populate_language_select()
        self._render_word_meta()

    def _set_tab_text(self, tab_widget: QtWidgets.QTabWidget, widget_name: str, message_code: str):
        for index in range(tab_widget.count()):
            if tab_widget.widget(index).objectName() == widget_name:
                tab_widget.setTabText(index, i18n.tr(message_code))
                return

    def _populate_language_select(self):
        selected_code = self.currentLanguageCode()
        select = self.ui.subtitlesLanguageSelect
        select.blockSignals(True)
        select.clear()
        for language_code in LANGUAGES:
            select.addItem(i18n.tr('language_name_' + language_code), language_code)
        if selected_code is not None:
            index = select.findData(selected_code)
            if index >= 0:
                select.setCurrentIndex(index)
        select.blockSignals(False)

    def currentLanguageCode(self) -> str:
        return self.ui.subtitlesLanguageSelect.currentData()

    def showWarning(self, message: UserMessage):
        QtWidgets.QMessageBox.warning(
            self, i18n.tr('warning_title'), i18n.format_user_message(message))

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
        self._render_word_meta()
        self._schedule_online_translation()

    def _render_word_meta(self):
        if not self.selected_word:
            return
        entry = None
        if self.controller.current_result is not None:
            entry = self.controller.current_result.words.get(self.selected_word)
        if entry is None:
            return
        meta_line = i18n.ntr('word_meta_line', 'word_meta_line_plural', entry.count,
                             word=self.selected_word, count=entry.count)
        if entry.pos:
            meta_line += i18n.tr('pos_suffix', pos=entry.pos.lower())
        if entry.possessive_count:
            meta_line += i18n.ntr('possessive_suffix', 'possessive_suffix_plural',
                                  entry.possessive_count, count=entry.possessive_count)
        context_phrase = entry.context_phrase.text if entry.context_phrase else ''
        # TODO: Display selected word meta in a proper UI element
        self.ui.fullPhraseTextBrowser.setText(
            f'{meta_line}\n{i18n.tr("context_label")}\n{context_phrase}')

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

    def _selected_phrase(self) -> str:
        entry = None
        if self.controller.current_result is not None:
            entry = self.controller.current_result.words.get(self.selected_word)
        if entry is not None and entry.context_phrase:
            return entry.context_phrase.text
        return ''

    def _schedule_online_translation(self):
        """Restart the debounce so only the last selection gets translated."""
        if not self.ui.translateCheckBox.isChecked():
            return
        self._translate_timer.start(TRANSLATE_DEBOUNCE_MS)

    def _translate_current_selection(self):
        if self.ui.translateSingleWordRbtn.isChecked():
            text = self.selected_word
        else:
            text = self._selected_phrase()
        if text:
            self.onlineTranslate(text)

    def translationOptionsChanged(self):
        if self.ui.translateCheckBox.isChecked():
            self.ui.translationTabWidget.setEnabled(True)
            self.ui.webEngineView.setEnabled(True)
            self.ui.translateSingleWordRbtn.setEnabled(True)
            self.ui.translatePhraseRbtn.setEnabled(True)
            self._schedule_online_translation()
        else:
            self._translate_timer.stop()
            self.ui.webEngineView.setUrl(QtCore.QUrl("about:blank"))
            self.ui.webEngineView.setEnabled(False)
            self.ui.translationTabWidget.setEnabled(False)
            self.ui.translateSingleWordRbtn.setEnabled(False)
            self.ui.translatePhraseRbtn.setEnabled(False)

    def translationTabClicked(self):
        current_tab = self.ui.translationTabWidget.currentWidget().objectName()
        logger.info(f'Tab {current_tab} is active')
