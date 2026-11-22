"""Offscreen smoke test: the Qt language menu retranslates the UI live."""
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

from PyQt6 import QtCore, QtWidgets

# QWebEngineView cannot be instantiated without a real graphics context (it
# core-dumps on the offscreen platform), and the retranslate pass never
# touches it - so the generated UI code gets a plain QWidget stand-in.
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

TEST_SETTINGS_PATH = PROJECT_ROOT / 'tmp' / 'test-qt-settings.ini'

# Keep a reference: an unreferenced QApplication is garbage-collected and its
# destruction makes any later QWidget construction abort (qFatal).
_qt_app = None


def setUpModule():
    global _qt_app
    if QtWidgets.QApplication.instance() is None:
        _qt_app = QtWidgets.QApplication([])


class _TestSettings(QtCore.QSettings):
    """QSettings confined to the project tmp dir, isolating the user profile."""

    def __init__(self):
        super().__init__(str(TEST_SETTINGS_PATH), QtCore.QSettings.Format.IniFormat)


# One shared instance so pending writes are visible to assertions immediately
# (QSettings flushes to disk lazily, so separate instances are unreliable).
_test_settings = None


def _test_settings_factory() -> _TestSettings:
    global _test_settings
    if _test_settings is None:
        _test_settings = _TestSettings()
    return _test_settings


class RetranslateTest(unittest.TestCase):
    def setUp(self):
        global _test_settings
        _test_settings = None
        TEST_SETTINGS_PATH.unlink(missing_ok=True)
        patcher = unittest.mock.patch.object(main_window, '_app_settings', _test_settings_factory)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.window = main_window.MainWindow(language_code='en')
        self.addCleanup(self.window.close)

    def test_initial_texts_are_translated(self):
        self.assertEqual(self.window.windowTitle(), 'Learn languages with subtitles')
        self.assertTrue(self.window._language_actions['en'].isChecked())
        self.assertEqual(self.window.ui.onlineSearchBtn.text(), 'Search')

    def test_menu_switch_retranslates_and_persists(self):
        self.window._language_actions['ru'].trigger()
        self.assertEqual(self.window.windowTitle(), 'Изучение языков с субтитрами')
        self.assertEqual(self.window.ui.sourceSelectionTabs.tabText(0), 'Загрузить из онлайн-источников')
        self.assertEqual(self.window.ui.sourceSelectionTabs.tabText(1), 'Загрузить из SRT-файла')
        self.assertEqual(self.window.ui.onlineSearchBtn.text(), 'Найти')
        self.assertEqual(self.window.ui.translateCheckBox.text(), 'Переводить')
        self.assertEqual(self.window.ui.subtitlesLanguageSelect.itemText(0), 'Английский')
        self.assertEqual(self.window.ui.subtitlesLanguageSelect.currentData(), 'eng')
        self.assertTrue(self.window._language_actions['ru'].isChecked())
        self.assertEqual(_test_settings_factory().value('ui_language'), 'ru')

    def test_menu_switch_to_german(self):
        self.window._language_actions['de'].trigger()
        self.assertEqual(self.window.windowTitle(), 'Sprachen lernen mit Untertiteln')
        self.assertEqual(self.window.ui.fileSelectBtn.text(), 'SRT-Datei wählen')
        self.assertEqual(self.window.ui.subtitlesLanguageSelect.itemText(2), 'Russisch')

    def test_stored_override_applied_on_restart(self):
        # A fresh MainWindow without an explicit language reads the stored
        # override (the "restart after switching" scenario).
        _test_settings_factory().setValue('ui_language', 'ru')
        window = main_window.MainWindow()
        self.addCleanup(window.close)
        self.assertEqual(window.windowTitle(), 'Изучение языков с субтитрами')
        self.assertTrue(window._language_actions['ru'].isChecked())


if __name__ == '__main__':
    unittest.main()
