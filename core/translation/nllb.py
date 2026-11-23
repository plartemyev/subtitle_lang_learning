"""NLLB-200-distilled-600M under CTranslate2: the offline phrase translator.

One decoding pass produces the phrase translation and the cross-attention
matrix (``return_attention=True``), which :mod:`core.translation.alignment`
turns into per-word translations. Model files live in the data directory,
prepared once by ``tools/prepare_nllb.py``; the NLLB-200 weights are
CC-BY-NC-4.0 (noncommercial use only).
"""
import logging
import threading
from pathlib import Path

import ctranslate2
from transformers import AutoTokenizer

from core.translation import alignment
from core.translation.models import PhraseTranslation, WordTranslation

logger = logging.getLogger(__name__)

# subtitle language codes (core.languages) and UI locales (ui.i18n) share one
# FLORES-200 mapping; target locales are the lowercase two-letter forms
NLLB_LANGUAGE_CODES = {
    'eng': 'eng_Latn', 'en': 'eng_Latn',
    'deu': 'deu_Latn', 'de': 'deu_Latn',
    'rus': 'rus_Cyrl', 'ru': 'rus_Cyrl',
    'th': 'tha_Thai',
}
BEAM_SIZE = 4
EOS_TOKEN = '</s>'

_translators = {}  # model dir -> NllbTranslator, loaded once like _nlp_cache


def get_translator(model_dir):
    """Process-wide translator for ``model_dir``, loaded on first use."""
    key = str(Path(model_dir))
    if key not in _translators:
        logger.info(f'Loading offline translation model from {key}')
        _translators[key] = NllbTranslator(key)
    return _translators[key]


class NllbTranslator:
    """Offline phrase translator with attention-derived word alignment."""

    def __init__(self, model_dir, compute_type='int8'):
        self._translator = ctranslate2.Translator(str(model_dir), device='cpu',
                                                  compute_type=compute_type)
        self._tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        # one phrase at a time: predictable latency under uvicorn's threadpool
        self._lock = threading.Lock()

    def translate(self, text, source_code, target_locale, words):
        """Translate ``text`` and align its ``words`` (AnnotatedWord tokens).

        Returns a :class:`PhraseTranslation`; words without confident
        attention carry translation=None, score=None.
        """
        source_lang = NLLB_LANGUAGE_CODES[source_code]
        target_lang = NLLB_LANGUAGE_CODES[target_locale]
        encoding = self._tokenizer(text, add_special_tokens=False,
                                   return_offsets_mapping=True)
        piece_tokens = self._tokenizer.convert_ids_to_tokens(encoding['input_ids'])
        piece_offsets = encoding['offset_mapping']
        # NLLB source format: [source language code] + pieces + [</s>]
        source_tokens = [source_lang] + piece_tokens + [EOS_TOKEN]
        keep_mask = [False] + [True] * len(piece_tokens) + [False]
        with self._lock:
            results = self._translator.translate_batch(
                [source_tokens], target_prefix=[[target_lang]],
                beam_size=BEAM_SIZE, return_attention=True)
        result = results[0]
        # hypotheses start with the target language prefix and end with </s>
        target_tokens = result.hypotheses[0]
        attention = result.attention[0]
        target_text = self._detokenize_target(target_tokens, target_lang)
        return self._build_translation(text, words, target_text, target_tokens,
                                       attention, target_lang, keep_mask,
                                       piece_offsets)

    def _detokenize_target(self, target_tokens, target_lang):
        body = [token for token in target_tokens
                if token != target_lang and token != EOS_TOKEN]
        ids = self._tokenizer.convert_tokens_to_ids(body)
        return self._tokenizer.decode(ids, skip_special_tokens=True).strip()

    def _build_translation(self, text, words, target_text, target_tokens,
                           attention, target_lang, keep_mask, piece_offsets):
        body_rows = [(token, vector) for token, vector in zip(target_tokens, attention)
                     if token != target_lang and token != EOS_TOKEN]
        piece_vectors = alignment.drop_special_columns(
            [vector for _token, vector in body_rows], keep_mask)
        target_words = alignment.merge_target_pieces(
            [token for token, _vector in body_rows], piece_vectors)
        piece_to_word = alignment.group_source_pieces(piece_offsets, words)
        content_mask = [not alignment.is_punctuation(word_text)
                        for word_text, _vector in target_words]
        votes = alignment.pick_target_words(
            [vector for _word, vector in target_words], piece_to_word,
            len(words), content_mask)
        aligned = []
        for index, word in enumerate(words):
            target_index, score = votes[index]
            translation = target_words[target_index][0] if target_index is not None else None
            aligned.append(WordTranslation(text=word.text, lemma=word.lemma, pos=word.pos,
                                           start=word.start, end=word.end, morph=word.morph,
                                           translation=translation, score=score))
        return PhraseTranslation(source_text=text, target_text=target_text, words=aligned)
