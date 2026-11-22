"""Offscreen test: word selection drives the online translation view.

Covers the wiring lost in the UI-decoupling refactor and the debounce that
coalesces rapid word clicks into a single provider request (Google
rate-limits by IP).
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

import ui.qt.main_window as main_window
from core.models import AnalysisResult, AnnotatedPhrase, WordEntry
from ui import i18n

# Keep a reference: an unreferenced QApplication is garbage-collected and its
# destruction makes any later QWidget construction abort (qFatal).
_qt_app = None


def setUpModule():
    global _qt_app
    if QtWidgets.QApplication.instance() is None:
        _qt_app = QtWidgets.QApplication([])


class OnlineTranslationTest(unittest.TestCase):
    DEBOUNCE_MS = 20  # patched interval, keep the waits well above it

    def setUp(self):
        unittest.mock.patch.object(main_window, 'TRANSLATE_DEBOUNCE_MS', self.DEBOUNCE_MS).start()
        self.addCleanup(unittest.mock.patch.stopall)
        self.load_mock = unittest.mock.Mock()
        self.window = main_window.MainWindow(language_code='en')
        self.addCleanup(self.window.close)
        unittest.mock.patch.object(self.window.ui.webEngineView, 'load', self.load_mock).start()

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

    def _enable_translation(self):
        self.window.ui.translateCheckBox.click()
        self.assertTrue(self.window.ui.webEngineView.isEnabled())

    def _wait_ms(self, ms):
        loop = QtCore.QEventLoop()
        QtCore.QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def _wait_for_debounce(self):
        self._wait_ms(self.DEBOUNCE_MS * 5)

    def test_rapid_selection_translates_only_last_word(self):
        self._enable_translation()
        self._select_words(['house', 'home', 'garden'])
        self.assertEqual(self.load_mock.call_count, 0)  # debounce holds the request
        self._wait_for_debounce()
        self.assertEqual(self.load_mock.call_count, 1)
        self.assertIn('text=garden', self.load_mock.call_args[0][0].toString())

    def test_single_selection_translates_word(self):
        self._enable_translation()
        self._select_words(['house'])
        self._wait_for_debounce()
        self.assertEqual(self.load_mock.call_count, 1)
        self.assertIn('text=house', self.load_mock.call_args[0][0].toString())

    def test_translate_url_follows_active_locale(self):
        self._enable_translation()
        self._select_words(['house'])
        self._wait_for_debounce()
        url = self.load_mock.call_args[0][0].toString()
        # both the provider interface language and the translation target
        self.assertIn('hl=en', url)
        self.assertIn('tl=en', url)

    def test_language_switch_updates_translate_url(self):
        self._enable_translation()
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
        self._enable_translation()  # the radio buttons stay disabled until then
        self.window.ui.translatePhraseRbtn.click()
        self._select_words(['garden'])
        self._wait_for_debounce()
        self.assertEqual(self.load_mock.call_count, 1)
        self.assertIn('text=In+the+garden+we+met.', self.load_mock.call_args[0][0].toString())

    def test_selection_with_translate_disabled_does_not_load(self):
        self.assertFalse(self.window.ui.translateCheckBox.isChecked())
        self._select_words(['house'])
        self._wait_for_debounce()
        self.assertEqual(self.load_mock.call_count, 0)

    def test_unchecking_cancels_pending_translation(self):
        self._enable_translation()
        self._select_words(['house'])
        self.window.ui.translateCheckBox.click()
        self._wait_for_debounce()
        self.assertEqual(self.load_mock.call_count, 0)


if __name__ == '__main__':
    unittest.main()
