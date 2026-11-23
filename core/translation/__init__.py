"""Offline translation: NLLB-200 under CTranslate2 with attention word alignment.

UI-library agnostic like the rest of ``core/``: one decoding pass produces the
phrase translation and the cross-attention matrix, which :mod:`core.translation.alignment`
turns into per-word translations. The model itself is not part of the
repository - prepare it once with ``tools/prepare_nllb.py`` (NLLB-200 weights
are CC-BY-NC-4.0, noncommercial use only).
"""
from core.translation.cache import TranslationCache, cache_key
from core.translation.models import PhraseTranslation, WordTranslation
from core.translation.nllb import NLLB_LANGUAGE_CODES, NllbTranslator, get_translator
