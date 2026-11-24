"""Offscreen test: word selection drives the translation views.

Covers the wiring lost in the UI-decoupling refactor and the debounce that
coalesces rapid word clicks into a single request. Translation ships
enabled with the local engines in phrase mode; the online (Google) tab is
translated only while it is the active one.
"""
import os

# Must be set before PyQt6 is imported anywhere.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys
import types
import unittest
import unittest.mock
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6 import QtCore, QtGui, QtWidgets

# QWebEngineView cannot be instantiated without a real graphics context (it
# core-dumps on the offscreen platform) - same stand-in as test_qt_retranslate.
if 'PyQt6.QtWebEngineWidgets' not in sys.modules:
    _stub_webengine = types.ModuleType('PyQt6.QtWebEngineWidgets')

    class _StubWebEngineView(QtWidgets.QWidget):
        def load(self, url):
            pass

        def setUrl(self, url):
            pass

    _stub_webengine.QWebEngineView = _StubWebEngineView
    sys.modules['PyQt6.QtWebEngineWidgets'] = _stub_webengine

import ui.qt.local_translation as local_translation
import ui.qt.main_window as main_window
from core.languages import LANGUAGES
from core.models import AnalysisResult, AnnotatedPhrase, AnnotatedWord, WordEntry
from core.translation.models import PhraseTranslation
from ui import i18n

# Keep a reference: an unreferenced QApplication is garbage-collected and its
# destruction makes any later QWidget construction abort (qFatal).
_qt_app = None


def setUpModule():
    global _qt_app
    if QtWidgets.QApplication.instance() is None:
        _qt_app = QtWidgets.QApplication([])


class FakeServices:
    """Scripted TranslationServices: no dictionary, scripted engine/literal."""

    def __init__(self, engine=None, literal=None, dictionary=None):
        self.engine = engine
        self.literal = literal
        self.dictionary = dictionary
        self.cache = types.SimpleNamespace(get=lambda key: None,
                                           put=lambda key, payload: None)


class FakeEngine:
    label = 'fake'

    def __init__(self):
        self.calls = []

    def translate(self, text, source_code, target_locale, words):
        self.calls.append(text)
        return PhraseTranslation(source_text=text, target_text=text + '!',
                                 words=[])


class FakeLiteral:
    def __init__(self):
        self.calls = []

    def translate(self, text, source_code, target_locale, words):
        self.calls.append(text)
        return 'word by word'


class MainWindowTestBase(unittest.TestCase):
    DEBOUNCE_MS = 20  # patched interval, keep the waits well above it

    def setUp(self):
        unittest.mock.patch.object(main_window, 'TRANSLATE_DEBOUNCE_MS',
                                   self.DEBOUNCE_MS).start()
        # the worker must not load spaCy: fake token lists are enough here
        unittest.mock.patch.object(local_translation, 'tokenize_phrase',
                                   lambda *args: []).start()
        self.addCleanup(unittest.mock.patch.stopall)
        self.window = main_window.MainWindow(language_code='en')
        self.addCleanup(self.window.close)

    def _select_words(self, words):
        model = QtGui.QStandardItemModel(self.window.ui.wordsListView)
        for word in words:
            model.appendRow(QtGui.QStandardItem(word))
        self.window.ui.wordsListView.setModel(model)
        selection_model = self.window.ui.wordsListView.selectionModel()
        selection_model.currentChanged.connect(self.window.wordInAListSelected)
        for word in words:
            selection_model.setCurrentIndex(
                model.indexFromItem(model.findItems(word)[0]),
                QtCore.QItemSelectionModel.SelectionFlag.Current)

    def _select_translation_tab(self, widget):
        tabs = self.window.ui.translationTabWidget
        tabs.setCurrentIndex(tabs.indexOf(widget))

    def _wait_ms(self, ms):
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def _wait_until(self, predicate, timeout_ms=2000):
        waited = 0
        while not predicate() and waited < timeout_ms:
            self._wait_ms(self.DEBOUNCE_MS)
            waited += self.DEBOUNCE_MS
        return predicate()

    def _wait_for_debounce(self):
        self._wait_ms(self.DEBOUNCE_MS * 5)


class DefaultModeTest(MainWindowTestBase):
    def test_translation_ships_enabled_local_phrase(self):
        self.assertTrue(self.window.ui.translateCheckBox.isChecked())
        self.assertTrue(self.window.ui.translatePhraseRbtn.isChecked())
        self.assertFalse(self.window.ui.translateSingleWordRbtn.isChecked())
        self.assertTrue(self.window.ui.translationTabWidget.isEnabled())
        tabs = self.window.ui.translationTabWidget
        self.assertIs(tabs.currentWidget(), self.window.ui.translateLocallyTab)

    def test_selection_translates_phrase_through_local_engines(self):
        engine, literal = FakeEngine(), FakeLiteral()
        self.window.services = FakeServices(engine=engine, literal=literal)
        self._install_phrase('garden', 'In the garden we met.')
        self._select_words(['garden'])
        self.assertTrue(self._wait_until(
            lambda: self.window.ui.localTranslationText.text() == 'In the garden we met.!'))
        self.assertEqual(engine.calls, ['In the garden we met.'])
        self.assertEqual(literal.calls, ['In the garden we met.'])
        self.assertEqual(self.window.ui.localLiteralText.text(), 'word by word')

    def test_unavailable_engine_shows_localized_message(self):
        self.window.services = FakeServices(engine=None, literal=None)
        self._install_phrase('garden', 'In the garden we met.')
        self._select_words(['garden'])
        self.assertTrue(self._wait_until(lambda: self.window.ui.localTranslationText.text()
                                         == i18n.tr('translation_unavailable')))

    def test_literal_block_hides_without_dictionary(self):
        self.window.services = FakeServices(engine=FakeEngine(), literal=None)
        self._install_phrase('garden', 'In the garden we met.')
        self._select_words(['garden'])
        self._wait_for_debounce()
        self._wait_ms(self.DEBOUNCE_MS * 5)
        self.assertFalse(self.window.ui.localLiteralLabel.isVisible())
        self.assertFalse(self.window.ui.localLiteralText.isVisible())

    def _install_phrase(self, word, phrase_text):
        entry = WordEntry(word=word, count=2, occurrences={
            'noun': [AnnotatedPhrase(text=phrase_text, start_sec=0.0, end_sec=1.0)],
        })
        self.window.controller = types.SimpleNamespace(
            current_result=AnalysisResult(language_code='eng', words={word: entry}))


class OnlineTranslationTest(MainWindowTestBase):
    def setUp(self):
        super().setUp()
        self.load_mock = unittest.mock.Mock()
        unittest.mock.patch.object(self.window.ui.webEngineView, 'load',
                                   self.load_mock).start()
        self._select_translation_tab(self.window.ui.translateOnlineTab)

    def _use_single_word_mode(self):
        # phrase mode ships as the default; word-mode tests opt out explicitly
        self.window.ui.translateSingleWordRbtn.click()
        self.assertTrue(self.window.ui.translateSingleWordRbtn.isChecked())

    def test_rapid_selection_translates_only_last_word(self):
        self._use_single_word_mode()
        self._select_words(['house', 'home', 'garden'])
        self.assertEqual(self.load_mock.call_count, 0)  # debounce holds the request
        self._wait_for_debounce()
        self.assertEqual(self.load_mock.call_count, 1)
        self.assertIn('text=garden', self.load_mock.call_args[0][0].toString())

    def test_single_selection_translates_word(self):
        self._use_single_word_mode()
        self._select_words(['house'])
        self._wait_for_debounce()
        self.assertEqual(self.load_mock.call_count, 1)
        self.assertIn('text=house', self.load_mock.call_args[0][0].toString())

    def test_translate_url_follows_active_locale(self):
        self._use_single_word_mode()
        self._select_words(['house'])
        self._wait_for_debounce()
        url = self.load_mock.call_args[0][0].toString()
        # both the provider interface language and the translation target
        self.assertIn('hl=en', url)
        self.assertIn('tl=en', url)

    def test_language_switch_updates_translate_url(self):
        self._use_single_word_mode()
        self.addCleanup(i18n.setup, 'en')
        i18n.setup('de')
        self._select_words(['house'])
        self._wait_for_debounce()
        url = self.load_mock.call_args[0][0].toString()
        self.assertIn('hl=de', url)
        self.assertIn('tl=de', url)

    def test_phrase_mode_translates_context_phrase(self):
        entry = WordEntry(word='garden', count=2, occurrences={
            'noun': [AnnotatedPhrase(text='In the garden we met.', start_sec=0.0, end_sec=1.0)],
        })
        self.window.controller = types.SimpleNamespace(
            current_result=AnalysisResult(language_code='eng', words={'garden': entry}))
        self.assertTrue(self.window.ui.translatePhraseRbtn.isChecked())
        self._select_words(['garden'])
        self._wait_for_debounce()
        self.assertEqual(self.load_mock.call_count, 1)
        self.assertIn('text=In+the+garden+we+met.', self.load_mock.call_args[0][0].toString())

    def test_selection_with_translate_disabled_does_not_load(self):
        self._use_single_word_mode()
        self.window.ui.translateCheckBox.click()  # ships checked, click disables
        self.assertFalse(self.window.ui.webEngineView.isEnabled())
        self._select_words(['house'])
        self._wait_for_debounce()
        self.assertEqual(self.load_mock.call_count, 0)

    def test_unchecking_cancels_pending_translation(self):
        self._use_single_word_mode()
        self._select_words(['house'])
        self.window.ui.translateCheckBox.click()
        self._wait_for_debounce()
        self.assertEqual(self.load_mock.call_count, 0)


class TokenTooltipTest(MainWindowTestBase):
    WORD = AnnotatedWord(text="'s", lemma='be', pos='AUX', start=0, end=2,
                         morph='Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin',
                         full_form='is')

    def test_full_form_and_bold_lemma_in_header(self):
        self.window.services = FakeServices(dictionary=None)
        tooltip = self.window._token_tooltip(self.WORD, self._entry(),
                                             LANGUAGES['eng'])
        self.assertIn("<b>&#x27;s</b> <b>(is)</b>", tooltip)
        self.assertIn('<b>be</b>', tooltip)

    def test_wiktionary_line_is_bold_and_glossed(self):
        dictionary = types.SimpleNamespace(lookup=lambda *args: {'entries': [
            {'pos': 'VERB', 'glosses': ['To perform; to execute.'],
             'translations': ['де́лать', 'ли']},
        ]})
        self.window.services = FakeServices(dictionary=dictionary)
        tooltip = self.window._token_tooltip(self.WORD, self._entry(),
                                             LANGUAGES['eng'])
        self.assertIn('<b>де́лать, ли</b>', tooltip)
        self.assertIn('To perform; to execute.', tooltip)

    def test_possessive_token_has_no_full_form(self):
        token = AnnotatedWord(text="'s", lemma="'s", pos='PART', start=0, end=2,
                              morph='', full_form='')
        self.window.services = FakeServices(dictionary=None)
        tooltip = self.window._token_tooltip(token, self._entry(), LANGUAGES['eng'])
        self.assertNotIn('(', tooltip.split('<br>')[0])

    def _entry(self):
        return WordEntry(word='be', count=3, occurrences={
            'aux': [AnnotatedPhrase(text="It's fine.", start_sec=0.0, end_sec=1.0)],
        })


if __name__ == '__main__':
    unittest.main()
