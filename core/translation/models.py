"""Result models of offline phrase translation.

Pure data, UI-library agnostic and serializable, mirroring the style of
:mod:`core.models`.
"""
from dataclasses import dataclass, field


@dataclass
class WordTranslation:
    """Source token with its per-word translation from an aligning engine.

    Carries the same identity fields as ``core.models.AnnotatedWord`` (text,
    lemma, pos, start, end, morph). ``translation``/``score`` are None when
    the engine did not align this token. Neither current engine aligns (the
    attention-based NLLB engine was replaced): both ship ``words=[]``.
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
    """Whole-phrase translation, with per-word alignments only from an
    aligning engine: ``words`` is empty from the current ones."""
    source_text: str
    target_text: str
    words: list = field(default_factory=list)  # list[WordTranslation]

    def to_payload(self) -> dict:
        """JSON-friendly dict (translation-cache and serializer shape)."""
        return {
            'source_text': self.source_text,
            'translation': self.target_text,
            'words': [{
                'text': word.text, 'lemma': word.lemma, 'pos': word.pos,
                'start': word.start, 'end': word.end, 'morph': word.morph,
                'translation': word.translation, 'score': word.score,
            } for word in self.words],
        }
