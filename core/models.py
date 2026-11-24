"""Typed analysis result models.

Pure data, UI-library agnostic and serializable, so any frontend (Qt, web, mobile)
can consume analysis results without touching spaCy or subtitle parsing details.
"""
from dataclasses import dataclass, field


@dataclass
class AnnotatedWord:
    """Single token of a phrase with its spaCy annotation."""
    text: str
    lemma: str
    pos: str
    start: int  # character offset within the phrase text
    end: int
    # Universal Dependencies features string, e.g. 'Number=Sing|Person=3|Tense=Pres';
    # empty for tokens without morphology (punctuation, uninflected words).
    morph: str = ''
    # Expanded surface form of a contracted token ('s -> is) derived from the
    # lemma + morphology above; empty for non-contractions.
    full_form: str = ''


@dataclass
class AnnotatedPhrase:
    """A subtitle phrase with per-word spaCy annotation and playback timings."""
    text: str
    start_sec: float
    end_sec: float
    words: list = field(default_factory=list)  # list[AnnotatedWord]


@dataclass
class WordEntry:
    """Aggregated statistics for a single unique word."""
    word: str
    count: int = 0
    pos: str = ''  # most frequent part of speech
    pos_counts: dict = field(default_factory=dict)  # pos -> occurrence count
    occurrences: dict = field(default_factory=dict)  # pos -> list[AnnotatedPhrase]
    possessive_count: int = 0  # how often the word is used as a possessive marker's possessor

    @property
    def context_phrase(self):
        """Phrase of the first occurrence of the word, in subtitle order."""
        for phrases in self.occurrences.values():
            if phrases:
                return phrases[0]
        return None


@dataclass
class AnalysisResult:
    """Word frequency analysis of one subtitle source."""
    language_code: str
    words: dict = field(default_factory=dict)  # word -> WordEntry, sorted by count desc

    @property
    def top_count(self) -> int:
        if not self.words:
            return 0
        return next(iter(self.words.values())).count
