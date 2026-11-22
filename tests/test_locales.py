"""Catalog completeness, plural rules and adapter behavior checks.

The catalog tests recompile the committed .po files with msgfmt into
tmp/test-locales and validate the fresh binaries, so editing a .po without
re-running tools/compile_locales.sh cannot go unnoticed.
"""
import os
import sys
import unittest
import unittest.mock
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import gettext
import shutil
import subprocess

from core.controller import UserMessage
from ui import i18n

LOCALES_DIR = PROJECT_ROOT / 'locales'
FRESHLY_COMPILED_DIR = PROJECT_ROOT / 'tmp' / 'test-locales'

# Every message code of the shared catalogs. Direct gettext keys (singular
# entries); the *_plural variants are only reachable via ngettext and are
# covered by PLURAL_SINGULAR_CODES.
def _morph_message_codes():
    """Morphology codes derived from the frontend's UD feature whitelist."""
    from ui.qt.grammar import MORPH_FEATURE_VALUES
    return [f'morph_{feature}_{value}' for feature, value in sorted(MORPH_FEATURE_VALUES)]


EXPECTED_CODES = frozenset({
    'warning_title',
    'unable_to_load_file',
    'no_subtitles_found',
    'subtitles_service_error',
    'no_parseable_subtitles',
    'word_meta_line',
    'pos_suffix',
    'possessive_suffix',
    'context_label',
    'language_name_eng',
    'language_name_deu',
    'language_name_rus',
    'window_title',
    'tab_online_source',
    'tab_file_source',
    'placeholder_subtitle_file',
    'button_select_srt',
    'button_search',
    'checkbox_translate',
    'radio_single_word',
    'radio_whole_phrase',
    'symbol_system_ui',
    'symbol_system_subtitle',
    'tab_translate_online',
    'tab_translate_local',
    'cli_word_line',
    'cli_subtitle_help',
    'cli_language_help',
    'cli_debug_help',
    'cli_ui_language_help',
    'pos_name_noun',
    'pos_name_propn',
    'pos_name_art',
    'pos_name_adj',
    'pos_name_verb',
    'pos_name_aux',
    'pos_name_part',
    'pos_name_adp',
    'pos_name_pron',
    'pos_name_adv',
    'pos_name_conj',
    'pos_name_intj',
    'pos_tip_noun',
    'pos_tip_propn',
    'pos_tip_art',
    'pos_tip_adj',
    'pos_tip_verb',
    'pos_tip_aux',
    'pos_tip_part',
    'pos_tip_adp',
    'pos_tip_pron',
    'pos_tip_adv',
    'pos_tip_conj',
    'pos_tip_intj',
    'pos_tip_intj_exclaim',
    'pos_tip_pron_plain',
    'token_lemma_line',
    'pos_also_line',
    'legend_in_phrase',
    'legend_hint',
    *_morph_message_codes(),
})

# Singular msgids of the codes defined as gettext plural pairs in the catalogs.
PLURAL_SINGULAR_CODES = ('no_parseable_subtitles', 'word_meta_line', 'possessive_suffix')


def setUpModule():
    if shutil.which('msgfmt') is None:
        raise unittest.SkipTest('msgfmt not available; install the gettext tools')
    for po_path in sorted(LOCALES_DIR.glob('*/LC_MESSAGES/messages.po')):
        locale_code = po_path.relative_to(LOCALES_DIR).parts[0]
        target_dir = FRESHLY_COMPILED_DIR / locale_code / 'LC_MESSAGES'
        target_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(['msgfmt', '--check', '-o', str(target_dir / 'messages.mo'), str(po_path)],
                       check=True)


def tearDownModule():
    shutil.rmtree(FRESHLY_COMPILED_DIR, ignore_errors=True)


class CatalogTest(unittest.TestCase):
    """Validate the catalogs compiled fresh from the committed .po sources."""

    def catalog(self, locale: str):
        return gettext.translation('messages', FRESHLY_COMPILED_DIR, [locale])

    def test_every_locale_has_all_codes(self):
        for locale in ('de', 'en', 'ru'):
            catalog = self.catalog(locale)
            for code in EXPECTED_CODES:
                self.assertNotEqual(catalog.gettext(code), code, f'{locale}: missing {code}')

    def test_plural_pairs_resolve_in_both_forms(self):
        for locale in ('de', 'en', 'ru'):
            catalog = self.catalog(locale)
            for singular in PLURAL_SINGULAR_CODES:
                for count in (1, 2, 5):
                    rendered = catalog.ngettext(singular, singular + '_plural', count)
                    self.assertNotEqual(rendered, singular, f'{locale}: missing singular of {singular}')
                    self.assertNotEqual(rendered, singular + '_plural', f'{locale}: missing plural of {singular}')

    def test_russian_selects_three_distinct_forms(self):
        # possessive_suffix inflects into three distinct Russian forms
        # (word_meta_line legitimately yields only two: раз/раза/раз).
        catalog = self.catalog('ru')
        forms = {catalog.ngettext('possessive_suffix', 'possessive_suffix_plural', count)
                 for count in (1, 3, 7)}
        self.assertEqual(len(forms), 3)

    def test_two_form_locales_select_two_distinct_forms(self):
        # Possessivform/Possessivformen and possessive/possessives differ;
        # word_meta_line forms coincide in German ({count}-mal is invariant).
        for locale in ('de', 'en'):
            catalog = self.catalog(locale)
            forms = {catalog.ngettext('possessive_suffix', 'possessive_suffix_plural', count)
                     for count in (1, 5)}
            self.assertEqual(len(forms), 2)

    def test_headers_declare_plural_rules(self):
        for locale in ('de', 'en', 'ru'):
            self.assertIn('plural-forms', self.catalog(locale).info())


class AdapterTest(unittest.TestCase):
    """End-to-end checks of ui.i18n against the committed catalogs."""

    def test_detect_system_locale(self):
        cases = (
            ({'LC_ALL': 'ru_RU.UTF-8'}, 'ru'),
            ({'LC_ALL': 'de_DE', 'LANG': 'en_US.UTF-8'}, 'de'),
            ({'LC_MESSAGES': 'en_GB.UTF-8'}, 'en'),
            ({'LANG': 'C'}, 'en'),
            ({'LANG': 'fr_FR.UTF-8'}, 'en'),
            ({}, 'en'),
        )
        for env, expected in cases:
            with unittest.mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(i18n.detect_system_locale(), expected, env)

    def test_setup_falls_back_to_default_for_unsupported_code(self):
        with unittest.mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(i18n.setup('fr'), 'en')

    def test_tr_interpolates_params(self):
        i18n.setup('en')
        self.assertEqual(i18n.tr('unable_to_load_file', path='x.srt'),
                         'Unable to load subtitles from file x.srt')

    def test_format_user_message_plural_convention(self):
        i18n.setup('en')
        rendered = i18n.format_user_message(UserMessage('no_parseable_subtitles', {'count': 3}))
        self.assertEqual(rendered, 'Unable to parse any subtitle file out of 3')

    def test_format_user_message_plain(self):
        i18n.setup('en')
        rendered = i18n.format_user_message(UserMessage('unable_to_load_file', {'path': 'x.srt'}))
        self.assertEqual(rendered, 'Unable to load subtitles from file x.srt')

    def test_russian_plural_forms_through_adapter(self):
        i18n.setup('ru')
        self.assertEqual(i18n.ntr('word_meta_line', 'word_meta_line_plural', 1, word='дом', count=1),
                         'Слово «дом» встречается 1 раз')
        self.assertEqual(i18n.ntr('word_meta_line', 'word_meta_line_plural', 3, word='дом', count=3),
                         'Слово «дом» встречается 3 раза')
        self.assertEqual(i18n.ntr('word_meta_line', 'word_meta_line_plural', 7, word='дом', count=7),
                         'Слово «дом» встречается 7 раз')

    def test_german_plural_forms_through_adapter(self):
        i18n.setup('de')
        self.assertEqual(i18n.ntr('possessive_suffix', 'possessive_suffix_plural', 1, count=1),
                         ', 1 Possessivform')
        self.assertEqual(i18n.ntr('possessive_suffix', 'possessive_suffix_plural', 3, count=3),
                         ', 3 Possessivformen')


if __name__ == '__main__':
    unittest.main()
