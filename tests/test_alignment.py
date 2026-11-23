"""Attention-matrix to word alignment helpers (synthetic fixtures, no model)."""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.models import AnnotatedWord
from core.translation import alignment


def word(text, start):
    return AnnotatedWord(text=text, lemma=text.lower(), pos='NOUN',
                         start=start, end=start + len(text))


class GroupSourcePiecesTests(unittest.TestCase):
    def test_pieces_map_to_their_containing_words(self):
        words = [word('ab', 0), word('cd', 3)]  # phrase "ab cd"
        offsets = [(0, 2), (3, 5)]
        self.assertEqual(alignment.group_source_pieces(offsets, words), [0, 1])

    def test_piece_between_words_maps_to_none(self):
        words = [word('ab', 0), word('cd', 3)]
        self.assertEqual(alignment.group_source_pieces([(2, 3)], words), [None])

    def test_empty_word_list_maps_everything_to_none(self):
        self.assertEqual(alignment.group_source_pieces([(0, 2)], []), [None])


class MergeTargetPiecesTests(unittest.TestCase):
    def test_pieces_merge_at_the_sentinel_boundary(self):
        tokens = ['▁Hel', 'lo', '▁world']
        vectors = [[1, 0], [0.5, 0], [0, 1]]
        merged = alignment.merge_target_pieces(tokens, vectors)
        self.assertEqual([text for text, _vector in merged], ['Hello', 'world'])
        self.assertEqual(merged[0][1], [1.5, 0])
        self.assertEqual(merged[1][1], [0, 1])

    def test_punctuation_pieces_stay_separate_words(self):
        tokens = ['▁today', '?', '▁быть', '.']
        vectors = [[1, 0], [0, 0.5], [0, 1], [0, 0.5]]
        merged = alignment.merge_target_pieces(tokens, vectors)
        self.assertEqual([text for text, _vector in merged],
                         ['today', '?', 'быть', '.'])
        self.assertEqual(merged[0][1], [1, 0])

    def test_leading_piece_without_sentinel_starts_the_first_word(self):
        merged = alignment.merge_target_pieces(['abc', 'def'], [[1], [1]])
        self.assertEqual(merged, [('abcdef', [2])])


class PickTargetWordsTests(unittest.TestCase):
    def test_strongest_target_word_wins_per_source_word(self):
        # pieces 0-1 belong to source word 0, piece 2 to word 1;
        # target word 0 carries more mass on both source words
        votes = alignment.pick_target_words(
            [[0.1, 0.2, 0.9], [0.0, 0.0, 0.2]], [0, 0, 1], 2, [True, True])
        self.assertEqual(votes[0], (0, 1.0))
        self.assertAlmostEqual(votes[1][0], 0)
        self.assertAlmostEqual(votes[1][1], 0.9 / 1.1)

    def test_masked_target_words_neither_win_nor_dilute(self):
        # the punctuation-like target word 1 carries the bulk of the mass;
        # masked out, the content word wins with full confidence
        votes = alignment.pick_target_words(
            [[0.1, 0.9, 0.0], [0.0, 0.8, 0.05]], [0, 1, 2], 3, [True, False])
        self.assertEqual(votes[1], (0, 1.0))

    def test_ties_pick_the_earliest_target_word(self):
        votes = alignment.pick_target_words(
            [[0.5, 0.5], [0.5, 0.5]], [0, 1], 2, [True, True])
        self.assertEqual(votes, [(0, 0.5), (0, 0.5)])

    def test_split_attention_below_threshold_yields_none(self):
        # six target words split the mass evenly: 1/6 < 0.2 confidence
        vectors = [[1.0, 1.0]] * 6
        votes = alignment.pick_target_words(vectors, [0, 1], 2, [True] * 6)
        self.assertEqual(votes, [(None, None), (None, None)])

    def test_no_signal_yields_none(self):
        votes = alignment.pick_target_words([[0.0, 0.0]], [0, 1], 2, [True])
        self.assertEqual(votes, [(None, None), (None, None)])


class IsPunctuationTests(unittest.TestCase):
    def test_pure_punctuation_and_symbols_are_detected(self):
        self.assertTrue(alignment.is_punctuation('...'))
        self.assertTrue(alignment.is_punctuation('«'))
        self.assertTrue(alignment.is_punctuation('?'))

    def test_words_with_letters_or_digits_are_content(self):
        self.assertFalse(alignment.is_punctuation('Hello'))
        self.assertFalse(alignment.is_punctuation('42'))
        self.assertFalse(alignment.is_punctuation('не'))


class DropSpecialColumnsTests(unittest.TestCase):
    def test_keeps_only_masked_positions(self):
        self.assertEqual(alignment.drop_special_columns(
            [[1, 2, 3], [4, 5, 6]], [False, True, False]), [[2], [5]])


if __name__ == '__main__':
    unittest.main()
