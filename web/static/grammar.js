/* Pedagogical grammar symbols (Montessori) and their mapping from spaCy tags.
 *
 * Faithful port of ui/qt/grammar.py: the same categories, canonical colors,
 * word-text variants, per-family underline styles and painted symbol
 * geometry (PyQt shapes redrawn as inline SVG). The active symbol system
 * selects whose Montessori tradition paints interjections and pronouns.
 * Pure renderer: display strings come from the caller via the i18n module.
 */

export const Category = Object.freeze({
  NOUN: 'noun',
  PROP_NOUN: 'propn',
  ARTICLE: 'art',
  ADJECTIVE: 'adj',
  VERB: 'verb',
  AUXILIARY: 'aux',
  PARTICLE: 'part',
  PREPOSITION: 'adp',
  PRONOUN: 'pron',
  ADVERB: 'adv',
  CONJUNCTION: 'conj',
  INTERJECTION: 'intj',
  UNMARKED: 'unmarked',
});

/* Canonical Montessori colors for the painted symbols (symbol fill). */
export const SYMBOL_COLORS = Object.freeze({
  [Category.NOUN]: '#18181b',
  [Category.PROP_NOUN]: '#18181b',
  [Category.ARTICLE]: '#38bdf8',
  [Category.ADJECTIVE]: '#1e40af',
  [Category.VERB]: '#dc2626',
  [Category.AUXILIARY]: '#dc2626',
  [Category.PARTICLE]: '#dc2626',
  [Category.PREPOSITION]: '#16a34a',
  [Category.PRONOUN]: '#9333ea',
  [Category.ADVERB]: '#ea580c',
  [Category.CONJUNCTION]: '#ec4899',
  [Category.INTERJECTION]: '#eab308',
  [Category.UNMARKED]: '#8e8e95',
});

/* Darker siblings of the canonical hues used for word text (contrast on white). */
export const WORD_COLORS = Object.freeze({
  [Category.NOUN]: '#18181b',
  [Category.PROP_NOUN]: '#18181b',
  [Category.ARTICLE]: '#0369a1',
  [Category.ADJECTIVE]: '#1e40af',
  [Category.VERB]: '#b91c1c',
  [Category.AUXILIARY]: '#b91c1c',
  [Category.PARTICLE]: '#b91c1c',
  [Category.PREPOSITION]: '#15803d',
  [Category.PRONOUN]: '#7e22ce',
  [Category.ADVERB]: '#b45309',
  [Category.CONJUNCTION]: '#be185d',
  [Category.INTERJECTION]: '#a16207',
  [Category.UNMARKED]: '#18181b',
});

/* Painted symbol height per category, px (widths follow from the shapes). */
export const SYMBOL_SIZES = Object.freeze({
  [Category.NOUN]: 13,
  [Category.PROP_NOUN]: 15,
  [Category.ARTICLE]: 8,
  [Category.ADJECTIVE]: 11,
  [Category.VERB]: 12,
  [Category.AUXILIARY]: 12,
  [Category.PARTICLE]: 8,
  [Category.PREPOSITION]: 13,
  [Category.PRONOUN]: 13,
  [Category.ADVERB]: 9,
  [Category.CONJUNCTION]: 7,
  [Category.INTERJECTION]: 12,
  [Category.UNMARKED]: 0,
});

/* Trailing part of the 'pos_name_<suffix>' / 'pos_tip_<suffix>' codes;
 * the category ids double as suffixes, so this is the identity map. */
export function messageSuffix(category) {
  return category;
}

/* spaCy coarse (UPOS) tags that carry a Montessori symbol; DET is resolved
 * separately through the language's article set, everything else unmarked. */
const UPOS_CATEGORIES = Object.freeze({
  ADJ: Category.ADJECTIVE,
  ADP: Category.PREPOSITION,
  ADV: Category.ADVERB,
  AUX: Category.AUXILIARY,
  CCONJ: Category.CONJUNCTION,
  INTJ: Category.INTERJECTION,
  NOUN: Category.NOUN,
  NUM: Category.ADJECTIVE,  // grammar boxes treat numerals as adjectives
  PART: Category.PARTICLE,
  PRON: Category.PRONOUN,
  PROPN: Category.PROP_NOUN,
  SCONJ: Category.CONJUNCTION,
  VERB: Category.VERB,
});

export function categoryFor(upos, tokenLower, language) {
  if (upos === 'DET') {
    return language.article_words.includes(tokenLower) ? Category.ARTICLE : Category.ADJECTIVE;
  }
  return UPOS_CATEGORIES[upos] || Category.UNMARKED;
}

/* Universal Dependencies morphological feature values rendered as readable
 * words in word tooltips ('morph_<feature>_<value>' message codes). Values
 * outside this set are skipped instead of leaking raw 'Feature=Value' text. */
const MORPH_FEATURE_VALUES = new Set([
  'person/1', 'person/2', 'person/3',
  'number/sing', 'number/plur',
  'tense/pres', 'tense/past', 'tense/fut', 'tense/imp',
  'verbform/fin', 'verbform/inf', 'verbform/part', 'verbform/conv', 'verbform/ger',
  'mood/ind', 'mood/imp', 'mood/sub', 'mood/cnd',
  'aspect/imp', 'aspect/perf', 'aspect/prog',
  'degree/pos', 'degree/cmp', 'degree/sup',
  'case/nom', 'case/acc', 'case/dat', 'case/gen',
  'case/ins', 'case/loc', 'case/voc',
  'gender/fem', 'gender/masc', 'gender/neut',
  'animacy/anim', 'animacy/inan',
  'voice/act', 'voice/mid', 'voice/pass',
  'definite/def', 'definite/ind',
  'prontype/prs', 'prontype/dem', 'prontype/int', 'prontype/rel',
  'prontype/ind', 'prontype/tot', 'prontype/neg',
  'poss/yes', 'reflex/yes', 'polarity/neg',
  'numtype/card', 'numtype/ord',
]);

function parseMorph(morph) {
  return morph.split('|')
    .map((item) => {
      const separator = item.indexOf('=');
      if (separator <= 0 || separator === item.length - 1) return null;
      return [item.slice(0, separator).toLowerCase(), item.slice(separator + 1).toLowerCase()];
    })
    .filter(Boolean);
}

export function morphologyLine(morph, translate) {
  const fragments = [];
  for (const [feature, value] of parseMorph(morph)) {
    if (MORPH_FEATURE_VALUES.has(feature + '/' + value)) {
      fragments.push(translate('morph_' + feature + '_' + value));
    }
  }
  return fragments.join(' \u00b7 ');
}

/* Grammar-symbol systems follow the Montessori tradition of a locale (port of
 * ui/qt/grammar.py SYSTEM_VARIANTS): the anglo set is the reference rendering;
 * ru/de deviate for interjection (exclamation keyhole) and pronoun (plain
 * pyramid). Thai uses the imported international materials verbatim. */
const SYSTEM_VARIANTS = Object.freeze({
  en: Object.freeze({}),
  ru: Object.freeze({ intj: 'exclaim', pron: 'plain' }),
  de: Object.freeze({ intj: 'exclaim', pron: 'plain' }),
  th: Object.freeze({}),
});

/* Subtitle language (core.languages codes) -> symbol system. */
const SUBTITLE_LANGUAGE_SYSTEMS = Object.freeze({ eng: 'en', deu: 'de', rus: 'ru' });

let activeSystem = 'en';

export function setActiveSystem(system) {
  activeSystem = system in SYSTEM_VARIANTS ? system : 'en';
}

export function getActiveSystem() {
  return activeSystem;
}

export function systemForUiLocale(localeCode) {
  return localeCode in SYSTEM_VARIANTS ? localeCode : 'en';
}

export function systemForSubtitleLanguage(languageCode) {
  return SUBTITLE_LANGUAGE_SYSTEMS[languageCode] || 'en';
}

function variantSuffix(category) {
  const variants = SYSTEM_VARIANTS[activeSystem] || {};
  return variants[category] || '';
}

/* Message-code suffix of the variant-aware 'pos_tip_<suffix>' message. */
export function tipMessageSuffix(category) {
  const suffix = messageSuffix(category);
  const variant = variantSuffix(category);
  return suffix && variant ? suffix + '_' + variant : suffix;
}

/* ---------- symbol painting (inline SVG, 1px = 1px like the Qt shapes) ---------- */

/* SVG coordinates: two decimals, no float noise. */
function n(value) {
  return Number(value.toFixed(2));
}

function pyramid(w, h) {
  return `<path d="M${n(w / 2)} 0 L${n(w)} ${n(h)} L0 ${n(h)} Z" fill="currentColor"/>`;
}

function sphere(cx, cy, r) {
  return `<circle cx="${n(cx)}" cy="${n(cy)}" r="${n(r)}" fill="currentColor"/>`;
}

const DRAWERS = {
  [Category.NOUN]: (s) => pyramid(s, s),
  [Category.PROP_NOUN]: (s) => {
    // the noun pyramid with a small star dot above
    const dotRadius = s * 0.09;
    const pyramidHeight = s * 0.8;
    const halfWidth = pyramidHeight * 0.55;
    const baseY = s;
    return sphere(s / 2, dotRadius + 0.5, dotRadius)
      + `<path d="M${n(s / 2)} ${n(baseY - pyramidHeight)} L${n(s / 2 + halfWidth)} ${n(baseY)}`
        + ` L${n(s / 2 - halfWidth)} ${n(baseY)} Z" fill="currentColor"/>`;
  },
  [Category.ARTICLE]: (s) => pyramid(s, s),
  [Category.ADJECTIVE]: (s) => pyramid(s, s),
  [Category.PRONOUN]: (s) => {
    if (variantSuffix(Category.PRONOUN) === 'plain') return pyramid(s, s);
    // the pyramid divided into three parts by two white lines
    const lines = [0.45, 0.70].map((fraction) => {
      const half = fraction * s / 2 - s * 0.06;
      const y = s * fraction;
      return `<line x1="${n(s / 2 - half)}" y1="${n(y)}" x2="${n(s / 2 + half)}" y2="${n(y)}"`
        + ` stroke="#ffffff" stroke-width="${n(Math.max(1.0, s * 0.11))}"/>`;
    }).join('');
    return pyramid(s, s) + lines;
  },
  [Category.VERB]: (s) => sphere(s / 2, s / 2, s / 2),
  [Category.AUXILIARY]: (s) => {
    // hollow sphere: ring with the Qt pen width, margin adjusted
    const margin = s * 0.14;
    return `<circle cx="${n(s / 2)}" cy="${n(s / 2)}" r="${n(s / 2 - margin)}"`
      + ` fill="none" stroke="currentColor" stroke-width="${n(s * 0.28)}"/>`;
  },
  [Category.PARTICLE]: (s) => sphere(s / 2, s / 2, s / 2),
  [Category.PREPOSITION]: (s) => {
    // moon rotated upright: outer circle with an odd-even inner hole. The Qt
    // inner ellipse sits at rotated-frame x = -0.01s, and rotate(-90) maps
    // (x, y) -> (y, -x), so on screen the hole center lands just below the
    // circle center (thin side down), exactly like the QPainter odd-even fill.
    const inner = s * 0.62;
    const holeCenterY = s * 0.51;
    return `<path fill="currentColor" fill-rule="evenodd" d="`
      + `M${n(s / 2)} 0 A${n(s / 2)} ${n(s / 2)} 0 1 0 ${n(s / 2)} ${n(s)} A${n(s / 2)} ${n(s / 2)} 0 1 0 ${n(s / 2)} 0 Z `
      + `M${n(s / 2)} ${n(holeCenterY - inner / 2)} A${n(inner / 2)} ${n(inner / 2)} 0 1 0 ${n(s / 2)} ${n(holeCenterY + inner / 2)}`
      + ` A${n(inner / 2)} ${n(inner / 2)} 0 1 0 ${n(s / 2)} ${n(holeCenterY - inner / 2)} Z"/>`;
  },
  [Category.ADVERB]: (s) => sphere(s / 2, s / 2, s / 2),
  [Category.CONJUNCTION]: (s) => `<rect width="${n(s * 2)}" height="${n(s)}" rx="1" fill="currentColor"/>`,
  [Category.INTERJECTION]: (s) => {
    if (variantSuffix(Category.INTERJECTION) === 'exclaim') {
      // classical form: circle above a tapering point (the golden keyhole)
      const circleSize = s * 0.58;
      const baseY = circleSize * 0.82;
      const baseHalf = s * 0.34;
      return sphere(s / 2, circleSize / 2, circleSize / 2)
        + `<path d="M${n(s / 2 - baseHalf)} ${n(baseY)} L${n(s / 2 + baseHalf)} ${n(baseY)} L${n(s / 2)} ${n(s)} Z"`
          + ` fill="currentColor"/>`;
    }
    return `<path d="M${n(s / 2)} 0 L${n(s)} ${n(s / 2)} L${n(s / 2)} ${n(s)} L0 ${n(s / 2)} Z" fill="currentColor"/>`;
  },
};

function symbolWidth(category) {
  return category === Category.CONJUNCTION ? SYMBOL_SIZES[category] * 2 : SYMBOL_SIZES[category];
}

/* SVG markup of the category symbol (top edge at 0, centered), sized 1:1. */
export function symbolSvg(category) {
  const size = SYMBOL_SIZES[category] || 0;
  if (size <= 0) return '';
  const drawer = DRAWERS[category];
  const width = symbolWidth(category);
  return `<svg width="${width}" height="${size}" viewBox="0 0 ${width} ${size}"`
    + ` aria-hidden="true">${drawer(size)}</svg>`;
}
