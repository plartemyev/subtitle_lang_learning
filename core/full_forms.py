"""Surface full forms of contracted tokens, derived from spaCy metadata.

spaCy splits contractions into their own tokens (it's -> it + 's) and
annotates each with a lemma and Person/Number/Tense morphology - the
inflected surface form (is/am/are) itself is not stored, so it is selected
from the tiny closed-class conjugations contraction tokens actually carry.
There are no per-contraction word lists: disambiguation ('s -> be vs have,
'd -> would vs had) comes from the per-usage lemma the model parsed. Lemmas
outside the closed classes (possessive 's, German merges like im) and
non-apostrophe tokens yield an empty string, i.e. no tooltip parenthetical.
"""

# Contraction tokens only ever carry these lemmas; each maps to its
# closed-class surface form ('ll -> will, 'd -> would, n't -> not and the
# let's -> 's lemma "us" come out of the spaCy lemma directly).
INVARIANT_FORMS = {'will': 'will', 'would': 'would', 'not': 'not', 'us': 'us'}


def full_form(text, lemma, morph):
    """Expanded surface form of a contracted token, or '' when the token is
    not a contraction or its lemma is outside the closed classes."""
    if "'" not in text:
        return ''
    if lemma in INVARIANT_FORMS:
        return INVARIANT_FORMS[lemma]
    if lemma == 'be':
        return _be_form(_features(morph))
    if lemma == 'have':
        return _have_form(_features(morph))
    return ''


def _features(morph):
    """UD features string -> {'Person': '3', ...} (missing features absent)."""
    return dict(item.split('=', 1) for item in morph.split('|') if '=' in item)


def _be_form(features):
    """Inflected present/past form of 'be' for the token's agreement features."""
    if features.get('Tense') == 'Past':
        if features.get('Number') == 'Plur' or features.get('Person') == '2':
            return 'were'
        return 'was'
    if features.get('Person') == '1' and features.get('Number') == 'Sing':
        return 'am'
    if features.get('Person') == '3' and features.get('Number') == 'Sing':
        return 'is'
    return 'are'


def _have_form(features):
    """Inflected form of 'have' for the token's agreement features."""
    if features.get('Tense') == 'Past':
        return 'had'
    if features.get('Person') == '3' and features.get('Number') == 'Sing':
        return 'has'
    return 'have'
