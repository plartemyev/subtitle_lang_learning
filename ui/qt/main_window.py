"""Qt frontend: widgets, wiring and rendering only.

All business logic lives in :mod:`core` and is reached through
:class:`core.controller.AppController`; this module never parses subtitles,
talks to OpenSubtitles or formats core events itself. All display text comes
from the shared localization adapter :mod:`ui.i18n`, applied by
:func:`MainWindow._retranslate_ui` (the .ui file stays layout-only).
"""
import html
import logging
import os
from pathlib import Path
from typing import Callable

import PyQt6.QtCore
from PyQt6 import QtCore, QtWidgets, uic
from PyQt6.QtCore import QDir, QUrl
from PyQt6.QtGui import (QAction, QActionGroup, QBrush, QColor, QDesktopServices, QFont, QIcon,
                         QPalette, QStandardItem, QStandardItemModel)

from core import paths, translate
from core.controller import AppController, UserMessage
from core.languages import LANGUAGES
from ui import i18n
from ui.qt import grammar
from ui.qt.flow_layout import FlowLayout
from ui.qt.local_translation import TranslationRequest, TranslationServices
from ui.qt.phrase_view import PosChip, TokenView

logger = logging.getLogger(__name__)

main_window_ui_path = Path(__file__).parent.joinpath('main_window.ui').resolve()
Ui_MainWindow, QtBaseClass = uic.loadUiType(main_window_ui_path)
# Breeze "application-x-srt" icon (LGPL-3.0-or-later, credited in the README):
# without a window icon the desktop shows the interpreter's generic one.
window_icon_path = Path(__file__).parent.joinpath('icon.svg').resolve()

NATIVE_LANGUAGE_NAMES = {
    'de': 'Deutsch',
    'en': 'English',
    'ru': 'Русский',
    'th': 'ไทย',
}

SETTINGS_ORGANIZATION = 'subtitle_lang_learning'
SETTINGS_APPLICATION = 'gui'
SETTINGS_LANGUAGE_KEY = 'ui_language'
SETTINGS_SYMBOL_SYSTEM_KEY = 'symbol_system'
# The About menu-bar item opens the project repository.
REPOSITORY_URL = 'https://github.com/plartemyev/subtitle_lang_learning'
# Whose Montessori tradition paints the symbols: the interface language's
# (the student's) or the subtitle language's (the language being learned).
SYMBOL_SYSTEM_UI = 'ui'
SYMBOL_SYSTEM_SUBTITLE = 'subtitle'

# The translation provider rate-limits by IP: coalesce rapid word clicks and
# radio switches into a single request for the last selection.
TRANSLATE_DEBOUNCE_MS = 300

# Word details stay hidden until a word from the list is selected.
DETAIL_WIDGET_NAMES = ('selectedWordLabel', 'selectedPosChip', 'selectedWordSubline',
                       'detailsDivider', 'contextLabel', 'phraseView', 'legendHint',
                       'legendLabel', 'legendChips')
# The local translation block stays hidden until the first phrase request.
LOCAL_WIDGET_NAMES = ('localTranslationLabel', 'localTranslationText',
                      'localLiteralLabel', 'localLiteralText')


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
        self.setWindowIcon(QIcon(str(window_icon_path)))
        self.controller = controller if controller is not None else AppController(warning_callback=self.showWarning)
        self.selected_word = ''
        self.services = TranslationServices(paths.data_dir())
        self._request_id = 0  # sequence guard: only the newest request renders
        self._pending_requests = []  # keep runnables alive while the pool runs them
        if language_code is None:
            # Manual override wins, then the system locale; i18n.setup()
            # validates both and falls back to the default locale.
            language_code = _app_settings().value(SETTINGS_LANGUAGE_KEY) \
                or QtCore.QLocale.system().name()[:2]
        i18n.setup(language_code)
        self.initUI()

    def initUI(self):
        self._build_language_menu()
        self._build_symbol_system_menu()
        self._about_action = self.menuBar().addAction(i18n.tr('button_about'))
        self._about_action.triggered.connect(self._open_repository)
        self.ui.fileSelectBtn.clicked.connect(self.fileSelectionDialog)
        self.ui.translationOptionsGroup.buttonClicked.connect(self.translationOptionsChanged)
        self.ui.translateCheckBox.clicked.connect(self.translationOptionsChanged)
        self.ui.filePathInput.editingFinished.connect(self.sourceFileProvided)
        self.ui.onlineSearchTitle.editingFinished.connect(self.loadSubtitlesFromInternet)
        self.ui.onlineSearchBtn.clicked.connect(self.loadSubtitlesFromInternet)
        self.ui.subtitlesLanguageSelect.currentIndexChanged.connect(self._subtitle_language_changed)
        self.ui.translationTabWidget.currentChanged.connect(self._translation_tab_changed)
        self._translate_timer = QtCore.QTimer(self)
        self._translate_timer.setSingleShot(True)
        self._translate_timer.timeout.connect(self._translate_current_selection)
        self.ui.legendChips.setLayout(FlowLayout())
        self.ui.phraseView.copy_requested.connect(self._copy_context_phrase)
        self._style_word_details()
        for widget_name in DETAIL_WIDGET_NAMES + LOCAL_WIDGET_NAMES:
            getattr(self.ui, widget_name).setVisible(False)
        self._retranslate_ui()
        # after _retranslate_ui: in subtitle mode the system resolves through
        # the language selector, which is only populated by now
        self._apply_symbol_system()
        # translation ships enabled with the local engines in phrase mode;
        # the .ui file carries those defaults, this applies the enabled state
        self.ui.translationTabWidget.setCurrentIndex(
            self.ui.translationTabWidget.indexOf(self.ui.translateLocallyTab))
        self.translationOptionsChanged()
        self.show()

    def _build_language_menu(self):
        self._language_menu = self.menuBar().addMenu(i18n.tr('menu_language'))
        actions_group = QActionGroup(self)
        self._language_actions = {}
        for locale_code in i18n.LOCALES:
            action = QAction(NATIVE_LANGUAGE_NAMES[locale_code], self)
            action.setCheckable(True)
            action.setChecked(locale_code == i18n.active_locale)
            action.triggered.connect(
                lambda checked, code=locale_code: self._switch_language(code))
            actions_group.addAction(action)
            self._language_menu.addAction(action)
            self._language_actions[locale_code] = action

    def _switch_language(self, language_code: str):
        if language_code == i18n.active_locale:
            return
        _app_settings().setValue(SETTINGS_LANGUAGE_KEY, language_code)
        i18n.setup(language_code)
        self._apply_symbol_system()
        self._retranslate_ui()

    def _open_repository(self):
        QDesktopServices.openUrl(QUrl(REPOSITORY_URL))

    def _build_symbol_system_menu(self):
        self._symbols_menu = self.menuBar().addMenu(i18n.tr('menu_symbols'))
        actions_group = QActionGroup(self)
        self._symbol_system_actions = {}
        for mode, message_code in ((SYMBOL_SYSTEM_UI, 'symbol_system_ui'),
                                   (SYMBOL_SYSTEM_SUBTITLE, 'symbol_system_subtitle')):
            action = QAction(i18n.tr(message_code), self)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked, mode_value=mode: self._set_symbol_system_mode(mode_value))
            actions_group.addAction(action)
            self._symbols_menu.addAction(action)
            self._symbol_system_actions[mode] = action

    def _set_symbol_system_mode(self, mode: str):
        if mode == _app_settings().value(SETTINGS_SYMBOL_SYSTEM_KEY, SYMBOL_SYSTEM_UI):
            return
        _app_settings().setValue(SETTINGS_SYMBOL_SYSTEM_KEY, mode)
        self._apply_symbol_system()
        if self.selected_word:
            self._render_word_meta()

    def _apply_symbol_system(self):
        """Resolve and activate the symbol system for the current knob mode."""
        mode = _app_settings().value(SETTINGS_SYMBOL_SYSTEM_KEY, SYMBOL_SYSTEM_UI)
        if mode == SYMBOL_SYSTEM_SUBTITLE and self.currentLanguageCode() is not None:
            system = grammar.system_for_subtitle_language(self.currentLanguageCode())
        else:
            system = grammar.system_for_ui_locale(i18n.active_locale)
        grammar.set_active_system(system)
        for mode_value, action in self._symbol_system_actions.items():
            action.setChecked(mode_value == mode)

    def _subtitle_language_changed(self):
        # In subtitle mode the painted tradition follows the language selector;
        # repopulation in _retranslate_ui keeps signals blocked, so only real
        # user changes land here.
        if _app_settings().value(SETTINGS_SYMBOL_SYSTEM_KEY, SYMBOL_SYSTEM_UI) \
                != SYMBOL_SYSTEM_SUBTITLE:
            return
        self._apply_symbol_system()
        if self.selected_word:
            self._render_word_meta()

    def _retranslate_ui(self):
        self.setWindowTitle(i18n.tr('window_title'))
        self._language_menu.setTitle(i18n.tr('menu_language'))
        self._symbols_menu.setTitle(i18n.tr('menu_symbols'))
        self._set_tab_text(self.ui.sourceSelectionTabs, 'onlineSource', 'tab_online_source')
        self._set_tab_text(self.ui.sourceSelectionTabs, 'fileSourceSRT', 'tab_file_source')
        self._set_tab_text(self.ui.translationTabWidget, 'translateOnlineTab', 'tab_translate_online')
        self._set_tab_text(self.ui.translationTabWidget, 'translateLocallyTab', 'tab_translate_local')
        self.ui.filePathInput.setPlaceholderText(i18n.tr('placeholder_subtitle_file'))
        self.ui.fileSelectBtn.setText(i18n.tr('button_select_srt'))
        self.ui.onlineSearchBtn.setText(i18n.tr('button_search'))
        self.ui.introLabel.setText(i18n.tr('intro_text'))
        self._about_action.setText(i18n.tr('button_about'))
        self.ui.translateCheckBox.setText(i18n.tr('checkbox_translate'))
        self.ui.translateSingleWordRbtn.setText(i18n.tr('radio_single_word'))
        self.ui.translatePhraseRbtn.setText(i18n.tr('radio_whole_phrase'))
        self._symbol_system_actions[SYMBOL_SYSTEM_UI].setText(i18n.tr('symbol_system_ui'))
        self._symbol_system_actions[SYMBOL_SYSTEM_SUBTITLE].setText(i18n.tr('symbol_system_subtitle'))
        self.ui.contextLabel.setText(i18n.tr('context_label'))
        self.ui.legendLabel.setText(i18n.tr('legend_in_phrase'))
        self.ui.legendHint.setText(i18n.tr('legend_hint'))
        self.ui.localTranslationLabel.setText(i18n.tr('translation_label'))
        self.ui.localLiteralLabel.setText(i18n.tr('translation_literal_label'))
        self._populate_language_select()
        self._render_word_meta()
        # the translation target follows the UI locale: refetch under the new one
        self._schedule_translation()

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
        self._schedule_translation()

    def _render_word_meta(self):
        if not self.selected_word:
            return
        entry = None
        if self.controller.current_result is not None:
            entry = self.controller.current_result.words.get(self.selected_word)
        if entry is None:
            return
        language = LANGUAGES[self.currentLanguageCode()]
        occurrence_pos = self._occurrence_pos(entry)
        category = grammar.category_for(occurrence_pos, entry.word, language)
        for widget_name in DETAIL_WIDGET_NAMES:
            getattr(self.ui, widget_name).setVisible(True)
        self.ui.selectedWordLabel.setText(entry.word)
        subline = f'{entry.count}\u00d7'
        if category is grammar.Category.UNMARKED:
            self.ui.selectedPosChip.setVisible(False)
            if occurrence_pos:
                subline += ' \u00b7 ' + i18n.tr('pos_suffix', pos=occurrence_pos.lower()).lstrip(', ')
        else:
            suffix = grammar.message_suffix(category)
            self.ui.selectedPosChip.set_data(category, i18n.tr('pos_name_' + suffix))
            self.ui.selectedPosChip.setToolTip(
                i18n.tr('pos_tip_' + grammar.tip_message_suffix(category)))
            details = self._entry_subline(entry, language, occurrence_pos)
            if details:
                subline += ' \u00b7 ' + details
        self.ui.selectedWordSubline.setText(subline)
        self._render_phrase(entry, language)

    def _style_word_details(self):
        """Fonts and secondary colors for the details pane and the start screen;
        the .ui file stays layout-only."""
        word_font = self.ui.selectedWordLabel.font()
        word_font.setPointSizeF(word_font.pointSizeF() + 6)
        word_font.setBold(True)
        self.ui.selectedWordLabel.setFont(word_font)

        subline_font = self.ui.selectedWordSubline.font()
        subline_font.setPointSizeF(max(subline_font.pointSizeF() - 1, 7))
        self.ui.selectedWordSubline.setFont(subline_font)

        for label in (self.ui.contextLabel, self.ui.legendLabel,
                      self.ui.localTranslationLabel, self.ui.localLiteralLabel):
            small_font = label.font()
            small_font.setPointSizeF(max(small_font.pointSizeF() - 2, 7))
            small_font.setCapitalization(QFont.Capitalization.SmallCaps)
            small_font.setBold(True)
            small_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 106)
            label.setFont(small_font)

        translation_font = self.ui.localTranslationText.font()
        translation_font.setPointSizeF(translation_font.pointSizeF() + 1)
        self.ui.localTranslationText.setFont(translation_font)

        # the rough word-by-word gloss is secondary next to the real translation
        literal_font = self.ui.localLiteralText.font()
        literal_font.setPointSizeF(max(literal_font.pointSizeF() - 1, 7))
        literal_font.setItalic(True)
        self.ui.localLiteralText.setFont(literal_font)

        hint_font = self.ui.legendHint.font()
        hint_font.setPointSizeF(max(hint_font.pointSizeF() - 1, 7))
        self.ui.legendHint.setFont(hint_font)
        hint_palette = self.ui.legendHint.palette()
        hint_palette.setColor(QPalette.ColorRole.WindowText,
                              grammar.secondary_color(self.palette()))
        for label in (self.ui.legendHint, self.ui.localLiteralText, self.ui.introLabel):
            label.setPalette(hint_palette)

    def _occurrence_pos(self, entry) -> str:
        """Part of speech of the occurrence highlighted in the context phrase:
        the details chip describes this very usage, the aggregate counts stay
        in the subline ('34× · также …')."""
        phrase = entry.context_phrase
        if phrase is not None:
            for word in phrase.words:
                if self._is_selected_token(word, entry):
                    return word.pos
        return entry.pos

    def _entry_subline(self, entry, language, chip_pos) -> str:
        """'also a noun (2×)' line plus the possessive note, if any."""
        parts = []
        others = sorted(((upos, count) for upos, count in entry.pos_counts.items()
                         if upos != chip_pos), key=lambda item: item[1], reverse=True)
        if others:
            items = ', '.join(f'{self._pos_display(upos, entry.word, language)} ({count}\u00d7)'
                              for upos, count in others)
            parts.append(i18n.tr('pos_also_line', items=items))
        if entry.possessive_count:
            possessive = i18n.ntr('possessive_suffix', 'possessive_suffix_plural',
                                  entry.possessive_count, count=entry.possessive_count)
            parts.append(possessive.lstrip(', '))
        return ' \u00b7 '.join(parts)

    def _pos_display(self, upos, token_lower, language) -> str:
        category = grammar.category_for(upos, token_lower, language)
        suffix = grammar.message_suffix(category)
        return i18n.tr('pos_name_' + suffix) if suffix else upos.lower()

    def _render_phrase(self, entry, language):
        phrase = entry.context_phrase
        tokens = []
        categories = []  # first-occurrence order, unmarked tokens skipped
        if phrase is not None:
            for index, word in enumerate(phrase.words):
                category = grammar.category_for(word.pos, word.text.lower(), language)
                # written tight against the previous token in the source ('ll, commas)
                attached = index > 0 and word.start == phrase.words[index - 1].end
                tokens.append(TokenView(text=word.text, category=category,
                                        tooltip=self._token_tooltip(word, entry, language),
                                        selected=self._is_selected_token(word, entry),
                                        attached=attached))
                if category is not grammar.Category.UNMARKED and category not in categories:
                    categories.append(category)
        self.ui.phraseView.set_tokens(tokens)
        self._rebuild_legend(categories)

    def _copy_context_phrase(self):
        """Click on the context phrase: its plain text goes to the clipboard."""
        text = ' '.join(self._selected_phrase().split())
        if text:
            QtWidgets.QApplication.clipboard().setText(text)

    def _token_tooltip(self, word, entry, language) -> str:
        suffix = grammar.message_suffix(
            grammar.category_for(word.pos, word.text.lower(), language))
        if suffix is None:
            return ''
        pos_name = i18n.tr('pos_name_' + suffix)
        header = f'<b>{html.escape(word.text)}</b>'
        if word.full_form:
            header += f' <b>({html.escape(word.full_form)})</b>'
        lemma_line = i18n.tr('token_lemma_line',
                             lemma=f'<b>{html.escape(word.lemma)}</b>', pos=pos_name)
        tooltip = f'{header}<br>{lemma_line}'
        morphology = grammar.morphology_line(word.morph, i18n.tr)
        if morphology:
            tooltip += f'<br>{html.escape(morphology)}'
        tooltip += self._dictionary_tooltip_lines(word)
        return tooltip

    def _dictionary_tooltip_lines(self, word) -> str:
        """Bold Wiktionary translations plus the first sense gloss, both into
        the active UI locale; empty when the dictionary is not prepared."""
        dictionary = self.services.dictionary
        if dictionary is None:
            return ''
        result = dictionary.lookup(self.currentLanguageCode(), i18n.active_locale,
                                   word.text, word.lemma, word.pos)
        terms, gloss = [], ''
        for entry in result['entries']:
            terms.extend(entry['translations'])
            if not gloss and entry['glosses']:
                gloss = entry['glosses'][0]
        lines = ''
        if terms:
            translations = f"<b>{html.escape(', '.join(terms))}</b>"
            lines += '<br>' + i18n.tr('token_dictionary_line', translations=translations)
        if gloss:
            lines += '<br>' + i18n.tr('token_gloss_line', gloss=html.escape(gloss))
        return lines

    @staticmethod
    def _is_selected_token(word, entry) -> bool:
        return word.lemma == entry.word or word.text.lower() == entry.word.lower()

    def _rebuild_legend(self, categories):
        layout = self.ui.legendChips.layout()
        while layout.count():
            layout.takeAt(0).widget().deleteLater()
        for category in categories:
            suffix = grammar.message_suffix(category)
            chip = PosChip()
            chip.set_data(category, i18n.tr('pos_name_' + suffix))
            chip.setToolTip(i18n.tr('pos_tip_' + grammar.tip_message_suffix(category)))
            layout.addWidget(chip)

    def populate_words_list(self):
        result = self.controller.current_result
        if result is None or not result.words:
            return
        self.ui.introLabel.setVisible(False)  # the start-screen description has served its purpose
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
            # the heat background is always bright: pin dark text so the list
            # stays readable under both the light and the dark system theme
            item.setForeground(QBrush(QColor('#1c1c1c')))
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
        locale = i18n.active_locale
        self.ui.webEngineView.load(QUrl(translate.build_translate_url(
            text, target=locale, interface=locale)))

    def _selected_phrase(self) -> str:
        entry = None
        if self.controller.current_result is not None:
            entry = self.controller.current_result.words.get(self.selected_word)
        if entry is not None and entry.context_phrase:
            return entry.context_phrase.text
        return ''

    def _schedule_translation(self):
        """Restart the debounce so only the last selection gets translated."""
        if not self.ui.translateCheckBox.isChecked():
            return
        self._translate_timer.start(TRANSLATE_DEBOUNCE_MS)

    def _translate_current_selection(self):
        if self.ui.translateSingleWordRbtn.isChecked():
            text = self.selected_word
        else:
            text = self._selected_phrase()
        if not text:
            return
        if self.ui.translationTabWidget.currentWidget() is self.ui.translateLocallyTab:
            self._translate_locally(text)
        else:
            self.onlineTranslate(text)

    def _translate_locally(self, text: str):
        """Dispatch one phrase through the literal view and the engine chain."""
        self._request_id += 1
        request = TranslationRequest(self._request_id, self.services, text,
                                     self.currentLanguageCode(), i18n.active_locale)
        request.signals.literal_ready.connect(self._literal_ready)
        request.signals.translation_ready.connect(self._local_translation_ready)
        self._pending_requests.append(request)
        for widget_name in LOCAL_WIDGET_NAMES:
            getattr(self.ui, widget_name).setVisible(True)
        self.ui.localTranslationText.setText('\u2026')
        QtCore.QThreadPool.globalInstance().start(request)

    def _literal_ready(self, request_id: int, gloss: str):
        if request_id != self._request_id:
            return
        has_gloss = bool(gloss)
        self.ui.localLiteralLabel.setVisible(has_gloss)
        self.ui.localLiteralText.setVisible(has_gloss)
        self.ui.localLiteralText.setText(gloss)

    def _local_translation_ready(self, request_id: int, payload):
        # the final signal of every request: release the runnable reference
        self._pending_requests = [pending for pending in self._pending_requests
                                  if pending.request_id != request_id]
        if request_id != self._request_id:
            return
        if payload is None:
            self.ui.localTranslationText.setText(i18n.tr('translation_unavailable'))
            return
        self.ui.localTranslationText.setText(payload['translation'])

    def translationOptionsChanged(self):
        if self.ui.translateCheckBox.isChecked():
            self.ui.translationTabWidget.setEnabled(True)
            self.ui.webEngineView.setEnabled(True)
            self.ui.translateSingleWordRbtn.setEnabled(True)
            self.ui.translatePhraseRbtn.setEnabled(True)
            self._schedule_translation()
        else:
            self._translate_timer.stop()
            self._request_id += 1  # in-flight results of the stale state are dropped
            self.ui.webEngineView.setUrl(QtCore.QUrl("about:blank"))
            self.ui.webEngineView.setEnabled(False)
            self.ui.translationTabWidget.setEnabled(False)
            self.ui.translateSingleWordRbtn.setEnabled(False)
            self.ui.translatePhraseRbtn.setEnabled(False)
            for widget_name in LOCAL_WIDGET_NAMES:
                getattr(self.ui, widget_name).setVisible(False)

    def _translation_tab_changed(self, index: int):
        current_tab = self.ui.translationTabWidget.widget(index).objectName()
        logger.info(f'Tab {current_tab} is active')
        self._schedule_translation()
