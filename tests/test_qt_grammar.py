"""UPOS → Montessori symbol mapping and per-category display data checks."""
import os

# Must be set before PyQt6 is imported anywhere.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys
import unittest
import unittest.mock
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtGui import QHelpEvent, QKeyEvent, QMouseEvent

from core.languages import LANGUAGES
from ui.qt import grammar
from ui.qt.grammar import (Category, MESSAGE_SUFFIXES, MORPH_FEATURE_VALUES, SYMBOL_COLORS,
                           SYMBOL_SIZES, UNDERLINES, WORD_COLORS, category_for, morphology_line,
                           parse_morph)
from ui.qt.phrase_view import PhraseView, TokenView

# PyQt6 converts unhandled exceptions in event handlers into qFatal (the
# process aborts instead of failing the test), so widget rendering is only
# verified through an actual offscreen render pass per category.
_qt_app = None


def setUpModule():
    global _qt_app
    if QtWidgets.QApplication.instance() is None:
        _qt_app = QtWidgets.QApplication([])


class CategoryMappingTest(unittest.TestCase):
    def test_content_and_function_tags_map_to_symbols(self):
        cases = {
            'NOUN': Category.NOUN,
            'PROPN': Category.PROP_NOUN,
            'VERB': Category.VERB,
            'AUX': Category.AUXILIARY,
            'ADJ': Category.ADJECTIVE,
            'ADV': Category.ADVERB,
            'ADP': Category.PREPOSITION,
            'PRON': Category.PRONOUN,
            'CCONJ': Category.CONJUNCTION,
            'SCONJ': Category.CONJUNCTION,
            'PART': Category.PARTICLE,
            'INTJ': Category.INTERJECTION,
            'NUM': Category.ADJECTIVE,  # numerals stay in the adjective family
        }
        for upos, expected in cases.items():
            self.assertIs(category_for(upos, 'x', LANGUAGES['eng']), expected, upos)

    def test_det_resolves_through_language_article_set(self):
        english = LANGUAGES['eng']
        german = LANGUAGES['deu']
        russian = LANGUAGES['rus']
        self.assertIs(category_for('DET', 'the', english), Category.ARTICLE)
        self.assertIs(category_for('DET', 'an', english), Category.ARTICLE)
        self.assertIs(category_for('DET', 'this', english), Category.ADJECTIVE)
        self.assertIs(category_for('DET', 'der', german), Category.ARTICLE)
        self.assertIs(category_for('DET', 'dieser', german), Category.ADJECTIVE)
        # Russian has no articles: every determiner stays in the adjective family
        self.assertIs(category_for('DET', 'этот', russian), Category.ADJECTIVE)

    def test_unknown_tags_stay_unmarked(self):
        for upos in ('PUNCT', 'SYM', 'X', 'SPACE', ''):
            self.assertIs(category_for(upos, 'x', LANGUAGES['eng']), Category.UNMARKED)


class CategoryDisplayDataTest(unittest.TestCase):
    def test_every_symbol_category_has_display_data(self):
        symbol_categories = set(MESSAGE_SUFFIXES)
        for category in symbol_categories:
            self.assertIn(category, SYMBOL_COLORS, category)
            self.assertIn(category, WORD_COLORS, category)
            self.assertIn(category, UNDERLINES, category)
            self.assertGreater(SYMBOL_SIZES[category], 0, category)
        self.assertNotIn(Category.UNMARKED, symbol_categories)

    def test_word_text_colors_differ_from_canonical_where_needed(self):
        # Light canonical hues (article sky-blue, interjection gold) must not be
        # reused for word text on a white background.
        self.assertNotEqual(WORD_COLORS[Category.ARTICLE], SYMBOL_COLORS[Category.ARTICLE])
        self.assertNotEqual(WORD_COLORS[Category.INTERJECTION], SYMBOL_COLORS[Category.INTERJECTION])
        self.assertNotEqual(WORD_COLORS[Category.VERB], SYMBOL_COLORS[Category.VERB])


class SymbolSystemTest(unittest.TestCase):
    """Per-tradition symbol variants and the resolution helpers behind the knob."""

    def setUp(self):
        self.addCleanup(grammar.set_active_system, grammar.active_system())

    def test_reference_system_renders_without_variants(self):
        grammar.set_active_system('en')
        self.assertEqual(grammar.variant_suffix(Category.INTERJECTION), '')
        self.assertEqual(grammar.variant_suffix(Category.PRONOUN), '')
        self.assertEqual(grammar.tip_message_suffix(Category.INTERJECTION), 'intj')
        self.assertEqual(grammar.tip_message_suffix(Category.PRONOUN), 'pron')

    def test_ru_and_de_systems_deviate_where_traditions_differ(self):
        for system in ('ru', 'de'):
            grammar.set_active_system(system)
            self.assertEqual(grammar.variant_suffix(Category.INTERJECTION), 'exclaim')
            self.assertEqual(grammar.variant_suffix(Category.PRONOUN), 'plain')
            self.assertEqual(grammar.tip_message_suffix(Category.INTERJECTION), 'intj_exclaim')
            self.assertEqual(grammar.tip_message_suffix(Category.PRONOUN), 'pron_plain')
            # the agreed categories stay untouched
            self.assertEqual(grammar.variant_suffix(Category.NOUN), '')
            self.assertEqual(grammar.tip_message_suffix(Category.VERB), 'verb')

    def test_unknown_system_falls_back_to_reference(self):
        grammar.set_active_system('fr')
        self.assertEqual(grammar.active_system(), 'en')

    def test_resolution_helpers(self):
        self.assertEqual(grammar.system_for_ui_locale('ru'), 'ru')
        self.assertEqual(grammar.system_for_ui_locale('th'), 'th')
        self.assertEqual(grammar.system_for_ui_locale('zz'), 'en')
        self.assertEqual(grammar.system_for_subtitle_language('eng'), 'en')
        self.assertEqual(grammar.system_for_subtitle_language('deu'), 'de')
        self.assertEqual(grammar.system_for_subtitle_language('rus'), 'ru')
        self.assertEqual(grammar.system_for_subtitle_language('xyz'), 'en')


class MorphologyLineTest(unittest.TestCase):
    def test_parse_morph_splits_pairs(self):
        self.assertEqual(parse_morph('Number=Sing|Person=3|Tense=Pres'),
                         [('number', 'sing'), ('person', '3'), ('tense', 'pres')])
        self.assertEqual(parse_morph(''), [])
        self.assertEqual(parse_morph('FeatureWithoutValue'), [])

    def test_morphology_line_localizes_known_and_skips_unknown(self):
        catalog = {f'morph_{feature}_{value}': f'{feature}={value}'
                   for feature, value in MORPH_FEATURE_VALUES}
        line = morphology_line('Number=Sing|Person=3|Tense=Pres', catalog.get)
        self.assertEqual(line, 'number=sing · person=3 · tense=pres')

        # unknown UD values must not leak raw Feature=Value into the tooltip
        self.assertEqual(morphology_line('Case=Abessive', catalog.get), '')
        self.assertEqual(morphology_line('Polarity=Neg', catalog.get), 'polarity=neg')


class PhraseViewWidgetTest(unittest.TestCase):
    """Offscreen render and interaction smoke tests for the phrase widgets."""

    ALL_CATEGORIES = [category for category in Category
                      if category is not Category.UNMARKED]

    def test_render_passes_for_every_category(self):
        tokens = [TokenView(text=f'w{category.value}', category=category)
                  for category in self.ALL_CATEGORIES]
        tokens.append(TokenView(text='know', category=Category.VERB, tooltip='tip',
                                selected=True))
        view = PhraseView()
        view.set_tokens(tokens)
        view.resize(600, 120)
        view.show()
        self.assertFalse(view.grab().isNull())

    def test_render_passes_for_every_symbol_system(self):
        tokens = [TokenView(text=f'w{category.value}', category=category)
                  for category in Category if category is not Category.UNMARKED]
        for system in ('en', 'ru', 'de', 'th'):
            grammar.set_active_system(system)
            view = PhraseView()
            view.set_tokens(tokens)
            view.resize(600, 120)
            view.show()
            self.assertFalse(view.grab().isNull(), system)
        grammar.set_active_system('en')

    def test_tooltip_event_shows_word_tooltip(self):
        view = PhraseView()
        view.set_tokens([TokenView(text='wanders', category=Category.VERB, tooltip='tip-text'),
                         TokenView(text=',', category=Category.UNMARKED)])
        view.resize(400, 80)
        view.show()
        event = QHelpEvent(QtCore.QEvent.Type.ToolTip, QPoint(5, 40), QPoint(100, 100))
        with unittest.mock.patch('ui.qt.phrase_view.QtWidgets.QToolTip.showText') as show_text:
            self.assertTrue(view.event(event))
        show_text.assert_called_once()
        self.assertEqual(show_text.call_args[0][1], 'tip-text')

    def test_keyboard_navigation_walks_tokens(self):
        view = PhraseView()
        view.set_tokens([TokenView(text='a', category=Category.NOUN, tooltip='t1'),
                         TokenView(text='b', category=Category.VERB, tooltip='t2')])
        view.resize(300, 80)
        view.show()
        right = QKeyEvent(QtCore.QEvent.Type.KeyPress, Qt.Key.Key_Right,
                          QtCore.Qt.KeyboardModifier.NoModifier)
        with unittest.mock.patch('ui.qt.phrase_view.QtWidgets.QToolTip.showText') as show_text:
            view.keyPressEvent(right)
            self.assertEqual(view._focus_index, 0)
            view.keyPressEvent(right)
            self.assertEqual(view._focus_index, 1)
        self.assertEqual(show_text.call_count, 2)

    def test_attached_tokens_are_typeset_tight_and_wrap_together(self):
        view = PhraseView()
        font = view.font()
        font.setPointSizeF(20)  # wide tokens: the layout never wraps below 200 px
        view.setFont(font)
        view.set_tokens([TokenView(text='wanderers', category=Category.NOUN),
                         TokenView(text="'ll", category=Category.AUXILIARY, attached=True),
                         TokenView(text='understand', category=Category.VERB),
                         TokenView(text='.', category=Category.UNMARKED, attached=True)])
        advance = view._font_metrics().horizontalAdvance
        padding = 2 * PhraseView.TOKEN_PADDING
        verb_x = advance('wanderers') + advance("'ll") + padding + advance(' ')
        # wide enough for "wanderers'll understand", not for the cluster "understand."
        view.resize(int(verb_x + advance('understand') + padding), 140)
        view.show()
        first, clitic, verb, period = view._positions
        self.assertEqual(round(clitic[0]), round(first[0] + advance('wanderers')))
        # the punctuation follows its word onto the next line
        self.assertEqual((verb[1], period[1]), (1, 1))
        self.assertEqual(round(period[0]), round(verb[0] + advance('understand')))
        # each attached token keeps its own hit area
        self.assertEqual(view._token_at(QPoint(int(clitic[0]) + PhraseView.TOKEN_PADDING + 1, 40)), 1)
        self.assertEqual(view._token_at(QPoint(int(first[0]) + PhraseView.TOKEN_PADDING + 1, 40)), 0)

    def test_click_asks_the_caller_to_copy_the_phrase(self):
        view = PhraseView()
        view.set_tokens([TokenView(text='a', category=Category.NOUN)])
        view.resize(300, 80)
        view.show()
        requested = []
        view.copy_requested.connect(lambda: requested.append(True))
        release = QMouseEvent(QtCore.QEvent.Type.MouseButtonRelease, QPointF(10, 40), QPointF(10, 40),
                              Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
                              Qt.KeyboardModifier.NoModifier)
        view.mouseReleaseEvent(release)
        self.assertEqual(requested, [True])


if __name__ == '__main__':
    unittest.main()
