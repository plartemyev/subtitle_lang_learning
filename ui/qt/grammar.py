"""Pedagogical grammar symbols (Montessori) and their mapping from spaCy tags.

Presentation-only concern of the Qt frontend: the symbol system, its colors and
the article/determiner split are display decisions, so this module must never
leak into :mod:`core`. Painting helpers are shared by the phrase view and the
header chip (both in :mod:`ui.qt.phrase_view`).

Shape names the category (readable without color, survives monochrome
printing); word text keeps an accessible darker variant of the canonical hue;
every symbol family owns one underline style. Underlines are drawn with plain
QPainter primitives - no rich-text HTML involved.
"""
from enum import Enum, auto

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainterPath, QPen

from core.languages import Language


class Category(Enum):
    NOUN = auto()
    PROP_NOUN = auto()
    ARTICLE = auto()
    ADJECTIVE = auto()
    VERB = auto()
    AUXILIARY = auto()
    PARTICLE = auto()
    PREPOSITION = auto()
    PRONOUN = auto()
    ADVERB = auto()
    CONJUNCTION = auto()
    INTERJECTION = auto()
    UNMARKED = auto()


class Underline(Enum):
    SOLID = auto()
    WAVY = auto()
    DASHED = auto()
    DOTTED = auto()
    DOUBLE = auto()
    NONE = auto()


# Canonical Montessori colors for the painted symbols.
SYMBOL_COLORS = {
    Category.NOUN: QColor('#18181b'),
    Category.PROP_NOUN: QColor('#18181b'),
    Category.ARTICLE: QColor('#38bdf8'),
    Category.ADJECTIVE: QColor('#1e40af'),
    Category.VERB: QColor('#dc2626'),
    Category.AUXILIARY: QColor('#dc2626'),
    Category.PARTICLE: QColor('#dc2626'),
    Category.PREPOSITION: QColor('#16a34a'),
    Category.PRONOUN: QColor('#9333ea'),
    Category.ADVERB: QColor('#ea580c'),
    Category.CONJUNCTION: QColor('#ec4899'),
    Category.INTERJECTION: QColor('#eab308'),
    Category.UNMARKED: QColor('#8e8e95'),
}

# Darker siblings of the canonical hues used for word text (contrast on white).
WORD_COLORS = {
    Category.NOUN: QColor('#18181b'),
    Category.PROP_NOUN: QColor('#18181b'),
    Category.ARTICLE: QColor('#0369a1'),
    Category.ADJECTIVE: QColor('#1e40af'),
    Category.VERB: QColor('#b91c1c'),
    Category.AUXILIARY: QColor('#b91c1c'),
    Category.PARTICLE: QColor('#b91c1c'),
    Category.PREPOSITION: QColor('#15803d'),
    Category.PRONOUN: QColor('#7e22ce'),
    Category.ADVERB: QColor('#b45309'),
    Category.CONJUNCTION: QColor('#be185d'),
    Category.INTERJECTION: QColor('#a16207'),
    Category.UNMARKED: QColor('#18181b'),
}

# Lightened siblings for dark system themes (contrast on near-black windows):
# every canonical hue swaps to its 300-level tailwind shade, the black nouns
# to near-white, so both the symbols and the word text keep their contrast.
SYMBOL_COLORS_DARK = {
    Category.NOUN: QColor('#e4e4e7'),
    Category.PROP_NOUN: QColor('#e4e4e7'),
    Category.ARTICLE: QColor('#7dd3fc'),
    Category.ADJECTIVE: QColor('#60a5fa'),
    Category.VERB: QColor('#f87171'),
    Category.AUXILIARY: QColor('#f87171'),
    Category.PARTICLE: QColor('#f87171'),
    Category.PREPOSITION: QColor('#4ade80'),
    Category.PRONOUN: QColor('#c084fc'),
    Category.ADVERB: QColor('#fb923c'),
    Category.CONJUNCTION: QColor('#f472b6'),
    Category.INTERJECTION: QColor('#facc15'),
    Category.UNMARKED: QColor('#a1a1aa'),
}

WORD_COLORS_DARK = {
    Category.NOUN: QColor('#e4e4e7'),
    Category.PROP_NOUN: QColor('#e4e4e7'),
    Category.ARTICLE: QColor('#7dd3fc'),
    Category.ADJECTIVE: QColor('#93c5fd'),
    Category.VERB: QColor('#fca5a5'),
    Category.AUXILIARY: QColor('#fca5a5'),
    Category.PARTICLE: QColor('#fca5a5'),
    Category.PREPOSITION: QColor('#86efac'),
    Category.PRONOUN: QColor('#d8b4fe'),
    Category.ADVERB: QColor('#fdba74'),
    Category.CONJUNCTION: QColor('#f9a8d4'),
    Category.INTERJECTION: QColor('#fde047'),
    Category.UNMARKED: QColor('#d4d4d8'),
}


def is_dark_palette(palette) -> bool:
    """True when the widget palette paints a dark window background."""
    window = palette.color(palette.ColorRole.Window)
    return window.lightness() < 128


def word_color(category: Category, dark: bool) -> QColor:
    """Theme-resolved text color of a category."""
    return WORD_COLORS_DARK[category] if dark else WORD_COLORS[category]


def symbol_color(category: Category, dark: bool) -> QColor:
    """Theme-resolved painted-symbol color of a category."""
    return SYMBOL_COLORS_DARK[category] if dark else SYMBOL_COLORS[category]

# One underline style per symbol family, with its pen width.
UNDERLINES = {
    Category.NOUN: (Underline.SOLID, 2.0),
    Category.PROP_NOUN: (Underline.SOLID, 2.0),
    Category.VERB: (Underline.WAVY, 1.5),
    Category.AUXILIARY: (Underline.WAVY, 1.5),
    Category.PARTICLE: (Underline.WAVY, 1.5),
    Category.ADJECTIVE: (Underline.DASHED, 1.5),
    Category.ARTICLE: (Underline.DASHED, 1.5),
    Category.ADVERB: (Underline.DOTTED, 1.5),
    Category.PREPOSITION: (Underline.DOUBLE, 1.0),
    Category.PRONOUN: (Underline.DOTTED, 2.0),
    Category.CONJUNCTION: (Underline.DASHED, 2.0),
    Category.INTERJECTION: (Underline.WAVY, 2.0),
    Category.UNMARKED: (Underline.NONE, 0.0),
}

# Painted symbol height per category, px (widths follow from the shapes).
SYMBOL_SIZES = {
    Category.NOUN: 13,
    Category.PROP_NOUN: 15,
    Category.ARTICLE: 8,
    Category.ADJECTIVE: 11,
    Category.VERB: 12,
    Category.AUXILIARY: 12,
    Category.PARTICLE: 8,
    Category.PREPOSITION: 13,
    Category.PRONOUN: 13,
    Category.ADVERB: 9,
    Category.CONJUNCTION: 7,
    Category.INTERJECTION: 12,
    Category.UNMARKED: 0,
}

# Trailing part of the 'pos_name_<suffix>' / 'pos_tip_<suffix>' message codes.
MESSAGE_SUFFIXES = {
    Category.NOUN: 'noun',
    Category.PROP_NOUN: 'propn',
    Category.ARTICLE: 'art',
    Category.ADJECTIVE: 'adj',
    Category.VERB: 'verb',
    Category.AUXILIARY: 'aux',
    Category.PARTICLE: 'part',
    Category.PREPOSITION: 'adp',
    Category.PRONOUN: 'pron',
    Category.ADVERB: 'adv',
    Category.CONJUNCTION: 'conj',
    Category.INTERJECTION: 'intj',
}

# spaCy coarse (UPOS) tags that carry a Montessori symbol; DET is resolved
# separately through the language's article set, everything else stays unmarked.
_UPOS_CATEGORIES = {
    'ADJ': Category.ADJECTIVE,
    'ADP': Category.PREPOSITION,
    'ADV': Category.ADVERB,
    'AUX': Category.AUXILIARY,
    'CCONJ': Category.CONJUNCTION,
    'INTJ': Category.INTERJECTION,
    'NOUN': Category.NOUN,
    'NUM': Category.ADJECTIVE,  # grammar boxes treat numerals as adjectives
    'PART': Category.PARTICLE,
    'PRON': Category.PRONOUN,
    'PROPN': Category.PROP_NOUN,
    'SCONJ': Category.CONJUNCTION,
    'VERB': Category.VERB,
}


def category_for(upos: str, token_lower: str, language: Language) -> Category:
    """Map a spaCy coarse tag to its pedagogical symbol category."""
    if upos == 'DET':
        if token_lower in language.article_words:
            return Category.ARTICLE
        return Category.ADJECTIVE
    return _UPOS_CATEGORIES.get(upos, Category.UNMARKED)


# Universal Dependencies morphological feature values rendered as readable
# words in word tooltips ('morph_<feature>_<value>' message codes). Values
# outside this set are skipped instead of leaking raw 'Feature=Value' text.
MORPH_FEATURE_VALUES = frozenset({
    ('person', '1'), ('person', '2'), ('person', '3'),
    ('number', 'sing'), ('number', 'plur'),
    ('tense', 'pres'), ('tense', 'past'), ('tense', 'fut'), ('tense', 'imp'),
    ('verbform', 'fin'), ('verbform', 'inf'), ('verbform', 'part'), ('verbform', 'conv'),
    ('verbform', 'ger'),
    ('mood', 'ind'), ('mood', 'imp'), ('mood', 'sub'), ('mood', 'cnd'),
    ('aspect', 'imp'), ('aspect', 'perf'), ('aspect', 'prog'),
    ('degree', 'pos'), ('degree', 'cmp'), ('degree', 'sup'),
    ('case', 'nom'), ('case', 'acc'), ('case', 'dat'), ('case', 'gen'),
    ('case', 'ins'), ('case', 'loc'), ('case', 'voc'),
    ('gender', 'fem'), ('gender', 'masc'), ('gender', 'neut'),
    ('animacy', 'anim'), ('animacy', 'inan'),
    ('voice', 'act'), ('voice', 'mid'), ('voice', 'pass'),
    ('definite', 'def'), ('definite', 'ind'),
    ('prontype', 'prs'), ('prontype', 'dem'), ('prontype', 'int'), ('prontype', 'rel'),
    ('prontype', 'ind'), ('prontype', 'tot'), ('prontype', 'neg'),
    ('poss', 'yes'), ('reflex', 'yes'), ('polarity', 'neg'),
    ('numtype', 'card'), ('numtype', 'ord'),
})


def parse_morph(morph: str) -> list:
    """Split a UD features string into lowercased (feature, value) pairs."""
    pairs = []
    for item in morph.split('|'):
        feature, separator, value = item.partition('=')
        if separator and feature and value:
            pairs.append((feature.lower(), value.lower()))
    return pairs


def morphology_line(morph: str, translate) -> str:
    """Readable localized morphology line; empty when nothing is renderable.

    ``translate`` maps a 'morph_<feature>_<value>' message code to display
    text (ui.i18n.tr keeps the localization decision out of this module).
    """
    fragments = []
    for feature, value in parse_morph(morph):
        if (feature, value) in MORPH_FEATURE_VALUES:
            fragments.append(translate(f'morph_{feature}_{value}'))
    return ' \u00b7 '.join(fragments)


def message_suffix(category: Category):
    """Message-code suffix ('pos_name_<suffix>' / 'pos_tip_<suffix>') or None."""
    return MESSAGE_SUFFIXES.get(category)


# Grammar-symbol systems follow the Montessori tradition of a locale. The
# anglo set is the reference rendering; other systems deviate only where the
# traditions genuinely differ (interjection: diamond vs classical exclamation
# keyhole, pronoun: tripartite vs plain pyramid). Colors, sizes and underline
# styles are agreed across the modern material sets and stay shared.
# Thai Montessori uses the imported international materials verbatim (no
# documented indigenous deviation), hence the reference rendering.
INTERJECTION_EXCLAIM = 'exclaim'
PRONOUN_PLAIN = 'plain'

SYSTEM_VARIANTS = {
    'en': {},
    'ru': {'intj': INTERJECTION_EXCLAIM, 'pron': PRONOUN_PLAIN},
    'de': {'intj': INTERJECTION_EXCLAIM, 'pron': PRONOUN_PLAIN},
    'th': {},
}

# Subtitle language (core.languages codes) -> symbol system.
SUBTITLE_LANGUAGE_SYSTEMS = {'eng': 'en', 'deu': 'de', 'rus': 'ru'}

_active_system = 'en'


def set_active_system(system: str) -> None:
    """Select whose Montessori tradition paints the symbols ('en'/'ru'/'de'/'th')."""
    global _active_system
    _active_system = system if system in SYSTEM_VARIANTS else 'en'


def active_system() -> str:
    return _active_system


def system_for_ui_locale(locale_code: str) -> str:
    """UI locales double as symbol systems; unknown locales get the reference."""
    return locale_code if locale_code in SYSTEM_VARIANTS else 'en'


def system_for_subtitle_language(language_code: str) -> str:
    return SUBTITLE_LANGUAGE_SYSTEMS.get(language_code, 'en')


def variant_suffix(category: Category) -> str:
    """Per-system drawing variant of a category ('exclaim', 'plain') or ''."""
    return SYSTEM_VARIANTS.get(_active_system, {}).get(MESSAGE_SUFFIXES.get(category, ''), '')


def tip_message_suffix(category: Category) -> str:
    """Message-code suffix of the variant-aware 'pos_tip_<suffix>' message."""
    suffix = message_suffix(category)
    variant = variant_suffix(category)
    return f'{suffix}_{variant}' if suffix and variant else suffix


def draw_symbol(painter, center_x: float, top_y: float, category: Category,
                dark: bool = False):
    """Paint the category symbol with its top edge at ``top_y``; centered on x."""
    size = SYMBOL_SIZES[category]
    if size <= 0:
        return
    color = symbol_color(category, dark)
    variant = variant_suffix(category)
    if category == Category.PREPOSITION:
        _draw_crescent(painter, center_x, top_y, size, color)
    elif category == Category.PROP_NOUN:
        _draw_starred_pyramid(painter, center_x, top_y, size, color)
    elif category == Category.PRONOUN and variant != PRONOUN_PLAIN:
        _draw_tripartite(painter, QRectF(center_x - size / 2, top_y, size, size), color)
    elif category == Category.INTERJECTION and variant == INTERJECTION_EXCLAIM:
        _draw_exclaim(painter, center_x, top_y, size, color)
    else:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        rect = QRectF(center_x - size / 2, top_y, size, size)
        if category in (Category.NOUN, Category.ARTICLE, Category.ADJECTIVE, Category.PRONOUN):
            painter.fillPath(_pyramid_path(rect), color)
        elif category in (Category.VERB, Category.ADVERB, Category.PARTICLE):
            painter.drawEllipse(rect)
        elif category == Category.AUXILIARY:
            pen = QPen(color)
            pen.setWidthF(size * 0.28)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            margin = size * 0.14
            painter.drawEllipse(rect.adjusted(margin, margin, -margin, -margin))
        elif category == Category.CONJUNCTION:
            painter.drawRoundedRect(QRectF(center_x - size, top_y, size * 2, size), 1.0, 1.0)
        elif category == Category.INTERJECTION:
            path = QPainterPath()
            path.moveTo(center_x, top_y)
            path.lineTo(center_x + size / 2, top_y + size / 2)
            path.lineTo(center_x, top_y + size)
            path.lineTo(center_x - size / 2, top_y + size / 2)
            path.closeSubpath()
            painter.fillPath(path, color)


def _pyramid_path(rect: QRectF) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(rect.center().x(), rect.top())
    path.lineTo(rect.right(), rect.bottom())
    path.lineTo(rect.left(), rect.bottom())
    path.closeSubpath()
    return path


def _draw_crescent(painter, center_x: float, top_y: float, size: float, color: QColor):
    """Moon opening upward: two circles, odd-even fill, rotated upright."""
    painter.save()
    painter.translate(center_x, top_y + size / 2)
    painter.rotate(-90)
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.OddEvenFill)
    path.addEllipse(QRectF(-size / 2, -size / 2, size, size))
    inner = size * 0.62
    path.addEllipse(QRectF(-size / 2 + size * 0.18, -inner / 2, inner, inner))
    painter.fillPath(path, color)
    painter.restore()


def _draw_starred_pyramid(painter, center_x: float, top_y: float, size: float, color: QColor):
    """Proper-noun extension: the noun pyramid with a small star dot above."""
    dot_radius = size * 0.09
    pyramid_height = size * 0.8
    pyramid_rect = QRectF(center_x - pyramid_height * 0.55, top_y + size - pyramid_height,
                          pyramid_height * 1.1, pyramid_height)
    painter.fillPath(_pyramid_path(pyramid_rect), color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QPointF(center_x, top_y + dot_radius + 0.5), dot_radius, dot_radius)


def _draw_tripartite(painter, rect: QRectF, color: QColor):
    """Pronoun: the pyramid divided into three parts by two white lines."""
    painter.fillPath(_pyramid_path(rect), color)
    pen = QPen(QColor('#ffffff'))
    pen.setWidthF(max(1.0, rect.height() * 0.11))
    painter.setPen(pen)
    center_x = rect.center().x()
    for fraction in (0.45, 0.70):
        half = fraction * rect.width() / 2 - rect.width() * 0.06
        y = rect.top() + rect.height() * fraction
        painter.drawLine(QPointF(center_x - half, y), QPointF(center_x + half, y))


def _draw_exclaim(painter, center_x: float, top_y: float, size: float, color: QColor):
    """Classical interjection form (ru/de systems): circle above a tapering
    point - reads as the golden exclamation mark / keyhole of the albums."""
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    circle_size = size * 0.58
    painter.drawEllipse(QRectF(center_x - circle_size / 2, top_y, circle_size, circle_size))
    base_y = top_y + circle_size * 0.82
    base_half = size * 0.34
    path = QPainterPath()
    path.moveTo(center_x - base_half, base_y)
    path.lineTo(center_x + base_half, base_y)
    path.lineTo(center_x, top_y + size)
    path.closeSubpath()
    painter.fillPath(path, color)
    painter.restore()
