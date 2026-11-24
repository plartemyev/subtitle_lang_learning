#!/usr/bin/env python3
"""Offscreen visual verification of the Qt frontend: light/dark screenshots.

Renders the real MainWindow on Qt's offscreen platform (native font and
palette rendering, no display server needed), drives a word selection
through the local engines and saves composited screenshots - empty window,
word list, details + phrase + local translation, a token tooltip, both
menus, the file-source tab and both translation tabs - into tmp/screenshots/
(so a rerun after a change documents the visual diff).

Usage: poetry run python tools/visual_check.py {light,dark} [--locale ru]

Dark mode applies the standard Qt dark Fusion palette - the reference dark
system theme; light mode keeps the platform default. Constraints that make
this work are catalogued in the skill notes (qt-offscreen-testing):
QWebEngineView is stubbed before the .ui loads (it core-dumps offscreen),
top-levels like the tooltip and menus are grabbed separately and composed
onto the window image.
"""
import argparse
import glob
import os
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6 import QtWidgets  # noqa: E402  (platform must be set first)

# QWebEngineView cannot render on the offscreen platform (it core-dumps);
# stub it so the .ui loads - the online tab pane shows as an empty native pane.
if 'PyQt6.QtWebEngineWidgets' not in sys.modules:
    _stub = types.ModuleType('PyQt6.QtWebEngineWidgets')

    class _StubWebEngineView(QtWidgets.QWidget):
        def load(self, url):
            pass

        def setUrl(self, url):
            pass

    _stub.QWebEngineView = _StubWebEngineView
    sys.modules['PyQt6.QtWebEngineWidgets'] = _stub

from core.controller import AppController  # noqa: E402
from core.env import load_dotenv  # noqa: E402

load_dotenv()  # OLLAMA_* so the local engines view gets real content

from PyQt6 import QtCore, QtGui  # noqa: E402

SHOT_NAMES = ('01-empty', '02-word-list', '03-main-selected', '04-token-tooltip',
              '05-menu-language', '06-menu-symbols', '07-source-file-tab',
              '08-translation-online-tab', '09-translation-local-tab')


def dark_palette() -> QtGui.QPalette:
    """The standard Qt dark Fusion palette (the reference dark system theme)."""
    palette = QtGui.QPalette()
    window_color = QtGui.QColor(53, 53, 53)
    for role in (QtGui.QPalette.ColorRole.Window, QtGui.QPalette.ColorRole.Button,
                 QtGui.QPalette.ColorRole.AlternateBase):
        palette.setColor(role, window_color)
    palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(25, 25, 25))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor(42, 42, 42))
    for role in (QtGui.QPalette.ColorRole.WindowText, QtGui.QPalette.ColorRole.Text,
                 QtGui.QPalette.ColorRole.ButtonText, QtGui.QPalette.ColorRole.ToolTipText):
        palette.setColor(role, QtCore.Qt.GlobalColor.white)
    palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtCore.Qt.GlobalColor.red)
    palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(42, 130, 218))
    palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(42, 130, 218))
    palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor('black'))
    for role in (QtGui.QPalette.ColorRole.WindowText, QtGui.QPalette.ColorRole.Text,
                 QtGui.QPalette.ColorRole.ButtonText):
        palette.setColor(QtGui.QPalette.ColorGroup.Disabled, role,
                         QtGui.QColor(127, 127, 127))
    return palette


def spin(milliseconds: int):
    """Process queued events for ``milliseconds`` (timers, signals, popups)."""
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def save_composited(window, path, overlays=()):
    """Window grab with separate top-levels (tooltip/menu) drawn on top."""
    canvas = window.grab()
    painter = QtGui.QPainter(canvas)
    for widget, position in overlays:
        painter.drawPixmap(position, widget.grab())
    painter.end()
    canvas.save(path)
    print('saved', path)


def visible_tooltip():
    """The QTipLabel window after QToolTip.showText, or None."""
    return next((widget for widget in QtWidgets.QApplication.allWidgets()
                 if widget.metaObject().className() == 'QTipLabel'
                 and widget.isVisible()), None)


def capture_token_tooltip(window, out_dir, suffix):
    """Focus a contraction token and composite its tooltip over the window."""
    phrase_view = window.ui.phraseView
    with_tooltip = [i for i, token in enumerate(phrase_view._tokens) if token.tooltip]
    token_index = next((i for i in with_tooltip if "'" in phrase_view._tokens[i].text),
                       with_tooltip[0] if with_tooltip else -1)
    if token_index < 0:
        print('no tooltip-annotated token in the phrase, skipped')
        return
    phrase_view.setFocus()
    phrase_view._focus_index = token_index
    phrase_view.update()
    token_rect = phrase_view._token_rect(token_index)
    anchor = phrase_view.mapToGlobal(QtCore.QPoint(int(token_rect.center().x()),
                                                   int(token_rect.top())))
    QtWidgets.QToolTip.showText(anchor, phrase_view._tokens[token_index].tooltip,
                                phrase_view)
    spin(400)
    tip = visible_tooltip()
    overlays = ()
    if tip is not None:
        local = phrase_view.mapTo(window, token_rect.topLeft().toPoint())
        overlays = ((tip, QtCore.QPoint(max(10, local.x()),
                                        max(10, local.y() - tip.height() - 8))),)
    save_composited(window, f'{out_dir}/04-token-tooltip{suffix}.png', overlays)


def wait_for_translation(window, timeout_seconds=60):
    """Poll the local translation label until the engines answered."""
    for _ in range(timeout_seconds * 2):
        spin(500)
        text = window.ui.localTranslationText.text()
        if text and text != '\u2026':
            return
    print('warning: translation label stayed pending, capturing anyway')


def capture_tabs(window, out_dir, suffix):
    tabs = window.ui.sourceSelectionTabs
    tabs.setCurrentIndex(tabs.indexOf(window.ui.fileSourceSRT))
    spin(300)
    save_composited(window, f'{out_dir}/07-source-file-tab{suffix}.png')
    tabs.setCurrentIndex(tabs.indexOf(window.ui.onlineSource))

    translation_tabs = window.ui.translationTabWidget
    translation_tabs.setCurrentIndex(
        translation_tabs.indexOf(window.ui.translateOnlineTab))
    spin(300)
    save_composited(window, f'{out_dir}/08-translation-online-tab{suffix}.png')
    translation_tabs.setCurrentIndex(
        translation_tabs.indexOf(window.ui.translateLocallyTab))
    spin(300)
    save_composited(window, f'{out_dir}/09-translation-local-tab{suffix}.png')


def capture_menus(window, out_dir, suffix):
    for name, menu, offset in (('05-menu-language', window._language_menu, 10),
                               ('06-menu-symbols', window._symbols_menu, 80)):
        menu.popup(window.mapToGlobal(QtCore.QPoint(offset, 30)))
        spin(300)
        overlays = ((menu, window.mapFromGlobal(menu.pos())),)
        save_composited(window, f'{out_dir}/{name}{suffix}.png', overlays)
        menu.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Offscreen light/dark visual verification of the Qt frontend.')
    parser.add_argument('mode', choices=('light', 'dark'),
                        help='system theme palette to render with')
    parser.add_argument('--locale', default='en', help='UI locale (default: en)')
    parser.add_argument('--sample', default=None,
                        help='subtitle file to load (default: first samples/*.srt)')
    parser.add_argument('--out', default=str(REPO_ROOT / 'tmp' / 'screenshots'),
                        help='screenshot directory')
    args = parser.parse_args()

    sample = args.sample or (sorted(glob.glob(str(REPO_ROOT / 'samples' / '*.srt')) or [None])[0])
    if not sample:
        parser.error('no subtitle sample found under samples/')
    suffix = '' if args.locale == 'en' else f'-{args.locale}'
    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)

    app = QtWidgets.QApplication([])
    app.setStyle('Fusion')
    if args.mode == 'dark':
        app.setPalette(dark_palette())

    from ui.qt.main_window import MainWindow  # after the palette is in place

    window = MainWindow(language_code=args.locale)
    window.resize(1280, 800)
    window.show()
    spin(300)
    save_composited(window, f'{out_dir}/01-empty{suffix}.png')

    window.controller.load_from_file(sample, window.currentLanguageCode())
    window.populate_words_list()
    spin(300)
    save_composited(window, f'{out_dir}/02-word-list{suffix}.png')

    model = window.ui.wordsListView.model()
    index = model.indexFromItem(model.findItems('do')[0])
    window.ui.wordsListView.selectionModel().setCurrentIndex(
        index, QtCore.QItemSelectionModel.SelectionFlag.Current)
    wait_for_translation(window)
    save_composited(window, f'{out_dir}/03-main-selected{suffix}.png')

    capture_token_tooltip(window, out_dir, suffix)
    capture_menus(window, out_dir, suffix)
    capture_tabs(window, out_dir, suffix)
    print('done', args.mode, args.locale)
    return 0


if __name__ == '__main__':
    sys.exit(main())
