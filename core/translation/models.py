"""Result models of offline phrase translation.

Pure data, UI-library agnostic and serializable, mirroring the style of
:mod:`core.models`.
"""
from dataclasses import dataclass, field


@dataclass
class WordTranslation:
    """Source token with its aligned translation from the same model pass.

    Carries the same identity fields as ``core.models.AnnotatedWord`` (text,
    lemma, pos, start, end, morph). ``translation``/``score`` are None when
    the cross-attention was not confident enough for this token - the UI can
    fall back to the dictionary gloss in that case.
    """
    text: str
    lemma: str
    pos: str
    start: int
    end: int
    morph: str = ''
    translation: str = None
    score: float = None


@dataclass
class PhraseTranslation:
    """Whole-phrase translation with per-word alignments."""
    source_text: str
    target_text: str
    words: list = field(default_factory=list)  # list[WordTranslation]
