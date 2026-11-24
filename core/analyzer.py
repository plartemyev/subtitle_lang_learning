"""Subtitle reading, sanitizing and word frequency analysis.

UI-library agnostic: operates on plain strings and :mod:`srt` objects only.
The exact sanitizing and token-skip rules must stay in sync with the CLI
baseline outputs (see tmp/baseline_*.txt generation in the project history).
"""
import html
import logging
import re

import spacy
import srt
from chardet.universaldetector import UniversalDetector

from core.full_forms import full_form
from core.languages import Language, resolve_language
from core.models import AnalysisResult, AnnotatedPhrase, AnnotatedWord, WordEntry

logger = logging.getLogger(__name__)

html_tags_filter = re.compile(r'<.*?>')
whitespace_filter = re.compile(r'[^\S\n]+')
www_spam_filter = re.compile(r'www\.\w+', re.I)
# A hyphen glued to the last character of a line marks a word wrapped across
# cues or subtitle lines ('wants to know-'); it is never part of the word.
# Standalone dashes ('wait - and listen'), leading dialogue dashes ('- Hello')
# and inner compound hyphens ('well-known') do not match and are kept.
line_wrap_hyphen_filter = re.compile(r'(\S)-(?=\s|$)')

_nlp_cache = {}


def get_nlp(language: Language):
    if language.spacy_model not in _nlp_cache:
        _nlp_cache[language.spacy_model] = spacy.load(language.spacy_model, exclude=['parser', 'ner'])
    return _nlp_cache[language.spacy_model]


def normalize_lemma(token) -> str:
    return token.lemma_.strip('-').lstrip('.').lower()


def sanitize_phrase_text(raw_content: str) -> str:
    """Strip HTML tags, unescape entities and collapse whitespace of a phrase."""
    text = whitespace_filter.sub(
        ' ', html.unescape(html_tags_filter.sub('', raw_content))).strip()
    return line_wrap_hyphen_filter.sub(r'\1', text)


def _annotate_words(doc) -> list:
    """Result of the single spaCy pass over a phrase, kept for UI rendering and word lookups."""
    return [AnnotatedWord(text=token.text, lemma=normalize_lemma(token), pos=token.pos_,
                          morph=str(token.morph),
                          full_form=full_form(token.text, normalize_lemma(token),
                                              str(token.morph)),
                          start=token.idx, end=token.idx + len(token.text))
            for token in doc if not token.is_space]


def tokenize_phrase(text: str, language_code: str) -> list:
    """Token-annotate a single phrase for translation and dictionary lookups."""
    language = resolve_language(language_code)
    return _annotate_words(get_nlp(language)(text))


def read_subtitles_file(sub_file_path: str) -> str:
    logger.info(f'Reading file {sub_file_path}')
    detector = UniversalDetector()
    with open(sub_file_path, mode='rb') as sub_f:
        for line in sub_f:
            detector.feed(line)
            if detector.done:
                break
    detector.close()
    encoding = detector.result.get('encoding')
    if not encoding:
        raise RuntimeError(f'Unable to detect encoding for file {sub_file_path}')
    with open(sub_file_path, encoding=encoding) as sub_f:
        return sub_f.read()


def parse_raw(raw_subtitles: str) -> list:
    """Parse raw subtitle text into srt.Subtitle objects."""
    return list(srt.parse(raw_subtitles))


def analyze_subtitles(subs, language_code: str = 'eng', use_lemmas: bool = True) -> AnalysisResult:
    """Build the word frequency index out of parsed subtitle objects."""
    language = resolve_language(language_code)
    nlp = get_nlp(language)
    sub_texts = []
    sub_objects = []
    for sub_object in subs:
        sub_text = sanitize_phrase_text(sub_object.content)
        if www_spam_filter.search(sub_text):
            # Skipping whole phrase as spam
            continue
        sub_texts.append(sub_text)
        sub_objects.append(sub_object)
    unique_texts = list(dict.fromkeys(sub_texts))
    annotated_by_text = {}
    for text, doc in zip(unique_texts, nlp.pipe(unique_texts, batch_size=64)):
        annotated_by_text[text] = (doc, _annotate_words(doc))
    entries = {}
    for sub_object, sub_text in zip(sub_objects, sub_texts):
        doc, annotated_words = annotated_by_text[sub_text]
        phrase = AnnotatedPhrase(text=sub_text,
                                 start_sec=sub_object.start.total_seconds(),
                                 end_sec=sub_object.end.total_seconds(),
                                 words=annotated_words)
        for token in doc:
            if token.is_punct or token.is_space:
                continue
            word = normalize_lemma(token) if use_lemmas else token.lower_
            if token.tag_ == 'POS':
                # possessive marker: annotate the possessor's entry instead of a standalone word
                possessor_word = ''
                if token.i > 0:
                    possessor = doc[token.i - 1]
                    possessor_word = normalize_lemma(possessor) if use_lemmas else possessor.lower_
                possessor_entry = entries.get(possessor_word)
                if possessor_entry is not None:
                    possessor_entry.possessive_count += 1
                continue
            if not word or token.is_digit or "'" in word:
                continue
            entry = entries.get(word)
            if entry is None:
                entries[word] = WordEntry(word=word, count=1, pos=token.pos_,
                                          pos_counts={token.pos_: 1},
                                          occurrences={token.pos_: [phrase]})
            else:
                entry.count += 1
                entry.pos_counts[token.pos_] = entry.pos_counts.get(token.pos_, 0) + 1
                entry.occurrences.setdefault(token.pos_, []).append(phrase)
                if entry.pos_counts[token.pos_] > entry.pos_counts[entry.pos]:
                    # keeping the most frequent part of speech in the entry meta
                    entry.pos = token.pos_
    logger.info(f'Parsed {len(entries)} unique words')
    sorted_words = dict(sorted(entries.items(), key=lambda _kv: _kv[1].count, reverse=True))
    return AnalysisResult(language_code=language.code, words=sorted_words)


def analyze_file(sub_file_path: str, language_code: str = 'eng', use_lemmas: bool = True) -> AnalysisResult:
    """Convenience helper: read an SRT file and analyze it in one call."""
    return analyze_subtitles(parse_raw(read_subtitles_file(sub_file_path)),
                             language_code, use_lemmas)
