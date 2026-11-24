"""Sanitizing rules around line-wrap hyphens and their effect on entries."""
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.analyzer import (analyze_subtitles, parse_raw, sanitize_phrase_text,
                           tokenize_phrase)


class SanitizeTextTest(unittest.TestCase):
    def test_trailing_wrap_hyphen_is_stripped(self):
        self.assertEqual(sanitize_phrase_text('wants to know-'), 'wants to know')
        # the wrap may also sit at a line end inside one cue
        self.assertEqual(sanitize_phrase_text('wants to know-\nwho waits'),
                         'wants to know\nwho waits')

    def test_dialogue_and_inner_hyphens_are_kept(self):
        self.assertEqual(sanitize_phrase_text('- Hello there'), '- Hello there')
        self.assertEqual(sanitize_phrase_text('a well-known fact'), 'a well-known fact')
        self.assertEqual(sanitize_phrase_text('wait - and listen'), 'wait - and listen')

    def test_html_and_entities_still_stripped(self):
        self.assertEqual(sanitize_phrase_text('<i>Hi!</i> &amp; bye-'), 'Hi! & bye')


class WrappedWordEntryTest(unittest.TestCase):
    def test_wrapped_word_is_analyzed_as_clean_token(self):
        subs = parse_raw('1\n00:00:01,000 --> 00:00:02,000\nwants to know-\n\n')
        result = analyze_subtitles(subs, 'eng')
        self.assertNotIn('know-', result.words)
        entry = result.words['know']
        # the hyphen used to derail the tagger into a garbage NUM reading
        self.assertEqual(entry.pos, 'VERB')
        self.assertEqual(entry.context_phrase.words[-1].text, 'know')


class FullFormAnnotationTest(unittest.TestCase):
    def test_contraction_tokens_carry_derived_full_forms(self):
        phrase = tokenize_phrase("It's fine, don't worry.", 'eng')
        forms = {word.text: word.full_form for word in phrase}
        self.assertEqual(forms["'s"], 'is')
        self.assertEqual(forms["n't"], 'not')

    def test_plain_tokens_and_possessives_have_no_full_form(self):
        phrase = tokenize_phrase("The rug's color is fine.", 'eng')
        forms = {word.text: word.full_form for word in phrase}
        self.assertEqual(forms['The'], '')
        self.assertEqual(forms["'s"], '')  # possessive marker, not a contraction
        self.assertEqual(forms['is'], '')


if __name__ == '__main__':
    unittest.main()
