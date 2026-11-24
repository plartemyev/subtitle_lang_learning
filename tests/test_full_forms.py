"""Full-form derivation for contracted tokens (core.full_forms)."""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.full_forms import full_form

BE_PRES_3SG = 'Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin'
BE_PRES_1SG = 'Mood=Ind|Number=Sing|Person=1|Tense=Pres|VerbForm=Fin'
BE_PAST_3SG = 'Mood=Ind|Number=Sing|Person=3|Tense=Past|VerbForm=Fin'


class FullFormTests(unittest.TestCase):
    def test_be_inflects_by_person_and_number(self):
        self.assertEqual(full_form("'s", 'be', BE_PRES_3SG), 'is')
        self.assertEqual(full_form("'m", 'be', BE_PRES_1SG), 'am')
        # spaCy often carries no person/number on 're: default plural reading
        self.assertEqual(full_form("'re", 'be', 'Mood=Ind|Tense=Pres|VerbForm=Fin'),
                         'are')

    def test_be_inflects_past_tense(self):
        self.assertEqual(full_form("'s", 'be', BE_PAST_3SG), 'was')
        self.assertEqual(full_form("'re", 'be', 'Mood=Ind|Number=Plur|Tense=Past|VerbForm=Fin'),
                         'were')

    def test_have_inflects_by_person_and_tense(self):
        self.assertEqual(full_form("'ve", 'have', 'Mood=Ind|Tense=Pres|VerbForm=Fin'),
                         'have')
        self.assertEqual(full_form("'s", 'have', BE_PRES_3SG), 'has')
        self.assertEqual(full_form("'d", 'have', 'Mood=Ind|Tense=Past|VerbForm=Fin'),
                         'had')

    def test_invariant_lemmas_pass_through(self):
        self.assertEqual(full_form("'ll", 'will', 'VerbType=Mod'), 'will')
        self.assertEqual(full_form("'d", 'would', 'VerbForm=Fin'), 'would')
        self.assertEqual(full_form("n't", 'not', 'Polarity=Neg'), 'not')
        self.assertEqual(full_form("'s", 'us', 'PronType=Prs'), 'us')

    def test_non_apostrophe_tokens_stay_empty(self):
        self.assertEqual(full_form('is', 'be', BE_PRES_3SG), '')
        self.assertEqual(full_form('im', 'in', 'Case=Dat'), '')

    def test_lemmas_outside_the_closed_classes_stay_empty(self):
        self.assertEqual(full_form("'s", "'s", ''), '')  # possessive marker
        self.assertEqual(full_form("geht's", "geht's", 'Foreign=Yes'), '')
        self.assertEqual(full_form("n't", 'zzzqx', ''), '')


if __name__ == '__main__':
    unittest.main()
