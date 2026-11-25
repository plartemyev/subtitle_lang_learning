/* Client-side counterpart of ui/i18n.py.
 *
 * Catalogs come from /api/i18n/<locale>, keyed by the same stable message
 * codes the core events and the Qt frontend use; plural pairs ship as
 * ordered translation arrays under the singular code. Lookup falls back
 * active locale -> en -> raw code, matching the server adapter's contract.
 */
export const LOCALES = ['de', 'en', 'ru', 'th'];
const FALLBACK_LOCALE = 'en';

/* gettext plural formulas per locale: n -> plural form index. */
const PLURAL_RULES = {
  de: (n) => (n !== 1 ? 1 : 0),
  en: (n) => (n !== 1 ? 1 : 0),
  ru: (n) => (n % 10 === 1 && n % 100 !== 11 ? 0
    : (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)) ? 1 : 2),
  th: () => 0,
};

const catalogs = {};  // locale -> messages object
let activeLocale = FALLBACK_LOCALE;

export function locale() {
  return activeLocale;
}

/* Best-effort UI locale from the browser, validated against LOCALES. */
export function detectLocale() {
  for (const candidate of navigator.languages || []) {
    const code = candidate.split('.')[0].split('_')[0].toLowerCase();
    if (LOCALES.includes(code)) return code;
  }
  return FALLBACK_LOCALE;
}

export async function setLocale(code) {
  if (!LOCALES.includes(code)) throw new Error('unsupported locale ' + code);
  if (!catalogs[code]) {
    const response = await fetch('api/i18n/' + code);
    if (!response.ok) throw new Error('catalog unavailable for ' + code);
    catalogs[code] = (await response.json()).messages;
  }
  activeLocale = code;
  return activeLocale;
}

function lookup(code) {
  const value = (catalogs[activeLocale] || {})[code];
  if (value !== undefined) return value;
  if (activeLocale !== FALLBACK_LOCALE) {
    const fallback = (catalogs[FALLBACK_LOCALE] || {})[code];
    if (fallback !== undefined) return fallback;
  }
  return null;
}

function interpolate(text, params) {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (match, key) =>
    (key in params ? String(params[key]) : match));
}

/* Singular message lookup (ui.i18n.tr). A plural-pair code without n falls
 * back to the raw code, same as calling gettext on a plural msgid. */
export function tr(code, params) {
  const value = lookup(code);
  if (value === null || Array.isArray(value)) return code;
  return interpolate(value, params);
}

/* Rich lookup: the localized template split around its {placeholder}s into
 * DOM nodes, with the interpolations named in boldKeys wrapped in <b> (the
 * tooltip emphasis Qt renders via rich text). Text nodes only - no HTML
 * parsing, values stay escaped by construction. */
export function trNodes(code, params, boldKeys) {
  const value = lookup(code);
  if (value === null || Array.isArray(value)) return [document.createTextNode(code)];
  const nodes = [];
  const pattern = /\{(\w+)\}/g;
  const keys = boldKeys || [];
  let cursor = 0;
  let match;
  while ((match = pattern.exec(value)) !== null) {
    if (match.index > cursor) {
      nodes.push(document.createTextNode(value.slice(cursor, match.index)));
    }
    const key = match[1];
    const text = params && key in params ? String(params[key]) : match[0];
    if (keys.includes(key)) {
      const bold = document.createElement('b');
      bold.textContent = text;
      nodes.push(bold);
    } else {
      nodes.push(document.createTextNode(text));
    }
    cursor = match.index + match[0].length;
  }
  if (cursor < value.length) nodes.push(document.createTextNode(value.slice(cursor)));
  return nodes;
}

/* Plural-aware lookup (ui.i18n.ntr): code -> array of plural forms. */
export function ntr(code, n, params) {
  const value = lookup(code);
  if (value === null) return code;
  const forms = Array.isArray(value) ? value : [value];
  const index = Math.min(PLURAL_RULES[activeLocale](n), forms.length - 1);
  return interpolate(forms[index], params);
}

/* Render a structured core event {code, params} into display text (port of
 * ui.i18n.format_user_message): a count parameter selects the plural forms. */
export function formatMessage(message) {
  if (message.params && 'count' in message.params) {
    return ntr(message.code, message.params.count, message.params);
  }
  return tr(message.code, message.params);
}
