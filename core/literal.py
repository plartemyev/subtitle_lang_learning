"""Literal word-by-word dictionary view of a phrase, no model involved.

The pedagogical counterpart to the model translation: shows how a phrase
would be assembled from dictionary pieces, so a student can see where an
idiom stops being word-composable ("Твою мать!" is literally "your
mother!", but "ups and downs" only makes sense as its own dictionary
headword). Resolution per token, in order: a longest-match sweep over
consecutive tokens reads multi-word headwords (up to :data:`MAX_NGRAM`
tokens) first; single tokens then try the surface form, the analyzer lemma
and pymorphy3 normal forms (spaCy misses Russian case forms like
вам -> вы); among an entry's target translations the first one that is not
just a transliteration of the source wins ("мужик" -> "man", not
"muzhik"); a reverse dictionary index plugs single-word data gaps (the
English edition carries no ru translations for the pronoun "I", the
Russian edition's "я" entry translates back to "I"); algorithmic
transliteration is the last resort. Punctuation passes through; the output
is a space-joined source-order gloss (also for Thai, where the spaces mark
gloss boundaries).
"""
import logging

from core.dictionary import KaikkiDictionary, ReverseDictionaryIndex

logger = logging.getLogger(__name__)

MAX_NGRAM = 6
GLOSSARY_POS = {'NOUN', 'VERB', 'ADJ', 'ADV', 'PROPN', 'NUM'}

CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'}
LATIN_TO_CYRILLIC_DIGRAPHS = {
    'sch': 'щ', 'shch': 'щ', 'ch': 'ч', 'sh': 'ш', 'zh': 'ж', 'kh': 'х',
    'ts': 'ц', 'ck': 'к', 'th': 'т', 'ph': 'ф', 'oo': 'у', 'ee': 'и',
    'ya': 'я', 'yu': 'ю', 'yo': 'ё', 'ja': 'я', 'ju': 'ю'}
LATIN_TO_CYRILLIC = {
    'a': 'а', 'b': 'б', 'c': 'к', 'd': 'д', 'e': 'е', 'f': 'ф', 'g': 'г',
    'h': 'х', 'i': 'и', 'j': 'дж', 'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н',
    'o': 'о', 'p': 'п', 'q': 'к', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у',
    'v': 'в', 'x': 'кс', 'y': 'ы', 'z': 'з'}
LATIN_TO_THAI_DIGRAPHS = {
    'kh': 'ค', 'ph': 'พ', 'th': 'ท', 'ch': 'ช', 'sh': 'ช', 'ng': 'ง',
    'ck': 'ก', 'oo': 'ู'}
LATIN_TO_THAI = {
    'k': 'ก', 'g': 'ก', 't': 'ต', 'd': 'ด', 'n': 'น', 'b': 'บ', 'p': 'ป',
    'f': 'ฟ', 'v': 'ว', 's': 'ส', 'h': 'ห', 'j': 'จ', 'z': 'ซ', 'm': 'ม',
    'y': 'ย', 'r': 'ร', 'l': 'ล', 'w': 'ว', 'c': 'ก', 'x': 'กซ',
    'a': 'า', 'e': 'เอ', 'i': 'อิ', 'o': 'โอ', 'u': 'อุ',
    'A': 'า', 'E': 'เอ', 'I': 'อิ', 'O': 'โอ', 'U': 'อุ'}

_morph_analyzer = None


def _is_cyrillic(text):
    return any('а' <= ch.lower() <= 'я' or ch.lower() == 'ё'
               for ch in text)


def _latinize_cyrillic(word):
    """Cyrillic -> Latin, keeping the word's capitalization (Ч -> Ch)."""
    out = []
    for ch in word:
        mapped = CYRILLIC_TO_LATIN.get(ch.lower())
        if mapped is None:
            out.append(ch)
        elif ch.isupper():
            out.append(mapped.capitalize())
        else:
            out.append(mapped)
    return ''.join(out)


def transliterate(word, target_locale):
    """Pure-algorithm script conversion for dictionary misses."""
    if target_locale in ('en', 'de'):
        return _latinize_cyrillic(word)
    latin = _latinize_cyrillic(word) if _is_cyrillic(word) else word
    if target_locale == 'ru':
        out, index = [], 0
        lowered = latin.lower()
        while index < len(latin):
            for size in (4, 3, 2):
                piece = lowered[index:index + size]
                if piece in LATIN_TO_CYRILLIC_DIGRAPHS:
                    out.append(LATIN_TO_CYRILLIC_DIGRAPHS[piece])
                    index += size
                    break
            else:
                out.append(LATIN_TO_CYRILLIC.get(lowered[index],
                                                 latin[index]))
                index += 1
        return ''.join(out)
    if target_locale == 'th':
        out, index = [], 0
        lowered = latin.lower()
        while index < len(latin):
            for size in (3, 2):
                piece = lowered[index:index + size]
                if piece in LATIN_TO_THAI_DIGRAPHS:
                    out.append(LATIN_TO_THAI_DIGRAPHS[piece])
                    index += size
                    break
            else:
                out.append(LATIN_TO_THAI.get(lowered[index],
                                             LATIN_TO_THAI.get(latin[index],
                                                               latin[index])))
                index += 1
        return ''.join(out)
    return word


def _lemma_candidates(word):
    """Extra lookup candidates: pymorphy3 normal forms for Cyrillic words."""
    global _morph_analyzer
    if not _is_cyrillic(word):
        return []
    if _morph_analyzer is None:
        try:
            import pymorphy3
            _morph_analyzer = pymorphy3.MorphAnalyzer()
        except ImportError:
            logger.warning('pymorphy3 unavailable; Cyrillic lemma '
                           'candidates disabled.')
            _morph_analyzer = False
    if not _morph_analyzer:
        return []
    return list(dict.fromkeys(parse.normal_form
                              for parse in _morph_analyzer.parse(word)[:4]))


class LiteralDictionary:
    """Word-by-word glossing over the dictionary, the pedagogical view
    that pairs with a model translation in the UI."""

    MAX_NGRAM = MAX_NGRAM

    def __init__(self, dictionary, reverse=None):
        self.dictionary = dictionary
        self.reverse = reverse

    def translate(self, text, source_code, target_locale, words):
        """Space-joined source-order gloss of ``text``; ``words`` are the
        analyzer-annotated tokens of the phrase (objects or dicts)."""
        if words and not isinstance(words[0], dict):
            words = [{'text': w.text, 'lemma': w.lemma, 'pos': w.pos}
                     for w in words]
        glosses = []
        index = 0
        while index < len(words):
            word = words[index]
            if word['pos'] == 'PUNCT':
                glosses.append(word['text'])
                index += 1
                continue
            multi = self._multi_word(source_code, target_locale, words, index)
            if multi is not None:
                translation, size = multi
                glosses.append(translation)
                index += size
                continue
            glosses.append(self._single_word(source_code, target_locale, word))
            index += 1
        return ' '.join(glosses)

    def _multi_word(self, source_code, target_locale, words, index):
        """(translation, token count) of the longest dictionary headword
        starting at ``index``, or None."""
        for size in range(min(MAX_NGRAM, len(words) - index), 1, -1):
            chunk = words[index:index + size]
            if any(w['pos'] == 'PUNCT' for w in chunk):
                continue
            ngram = ' '.join(w['text'] for w in chunk)
            translation = self._translated(source_code, target_locale,
                                           [ngram],
                                           transliterate(ngram, target_locale))
            if translation is not None:
                return translation, size
        return None

    def _single_word(self, source_code, target_locale, word):
        translation = self._translated(
            source_code, target_locale,
            [word['text'], word['lemma'], *_lemma_candidates(word['text'])],
            transliterate(word['text'], target_locale),
            pos=word['pos'])
        if translation is not None:
            return translation
        if self.reverse is not None:
            matched = self.reverse.lookup(source_code, target_locale,
                                          word['text'])
            if matched is not None:
                return matched
        return transliterate(word['text'], target_locale)

    def _translated(self, source_code, target_locale, candidates, naive,
                    pos=None):
        """First target translation of any candidate headword that is not
        just the naive transliteration of the source, or None."""
        for candidate in candidates:
            result = self.dictionary.lookup(source_code, target_locale,
                                            candidate, lemma=candidate,
                                            pos=pos)
            for entry in result['entries']:
                options = [term for term in entry['translations']
                           if term.strip().casefold() != naive.casefold()]
                if options:
                    return options[0]
        return None
