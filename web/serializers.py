"""Serialize core analysis results into compact JSON for the web frontend.

The Qt details pane renders ``WordEntry.context_phrase`` only, so each unique
context phrase ships once in a pool and word entries reference it by index -
one phrase is shared by every word it introduces. Pure core data in, plain
JSON-able dicts out: no FastAPI or browser concepts here.
"""
from core.models import AnalysisResult


def analysis_to_dict(result: AnalysisResult) -> dict:
    phrases = []
    phrase_indexes = {}  # id(context phrase object) -> pool index
    words = {}
    for word, entry in result.words.items():
        phrase = entry.context_phrase
        index = None
        if phrase is not None:
            key = id(phrase)
            if key not in phrase_indexes:
                phrase_indexes[key] = len(phrases)
                phrases.append({
                    'text': phrase.text,
                    'start_sec': phrase.start_sec,
                    'end_sec': phrase.end_sec,
                    'words': [word_to_dict(token) for token in phrase.words],
                })
            index = phrase_indexes[key]
        words[word] = {
            'word': word,
            'count': entry.count,
            'pos': entry.pos,
            'pos_counts': entry.pos_counts,
            'possessive_count': entry.possessive_count,
            'phrase': index,
        }
    return {'language_code': result.language_code, 'phrases': phrases, 'words': words}


def word_to_dict(token) -> dict:
    return {'text': token.text, 'lemma': token.lemma, 'pos': token.pos,
            'morph': token.morph, 'full_form': token.full_form,
            'start': token.start, 'end': token.end}


def phrase_translation_to_dict(translation) -> dict:
    """Serialize a core.translation.PhraseTranslation for the web frontend.

    Words keep their analysis identity (text/lemma/pos/morph/offsets) plus
    the aligned translation from the same model pass; translation/score are
    null when attention was not confident enough for that token.
    """
    return translation.to_payload()
