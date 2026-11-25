/* Web frontend wiring: fetching, state and rendering.
 *
 * Port of the Qt MainWindow rendering paths (word list heat colors, word
 * details pane, annotated context phrase, legend, symbol-system knob) over
 * the /api backend. All display text comes from the shared catalogs via the
 * i18n module; core events arrive as {code, params} and render client-side.
 */
import * as grammar from './grammar.js';
import * as i18n from './i18n.js';

const state = {
  languages: [],
  subtitleLanguage: 'eng',
  analysis: null,
  selectedWord: '',
  sourceLabel: '',
  listOpen: false,
  inspected: null,  // phrase token shown in the word card (touch)
  explained: null,  // 'word' or a category: the chip whose explanation is open
};

/* A fine pointer that can hover keeps the tooltip layer. Anything else, a
 * finger, gets the same builders in persistent surfaces: the word card under
 * the phrase, explanations that expand in place, a copy button. */
const hoverInput = window.matchMedia('(hover: hover) and (pointer: fine)');
const touchMode = () => !hoverInput.matches;

let warning = null;  // list of {code, params} core events or null
let busy = false;

/* Offline phrase translation (remote or local model engine) + Wiktionary
 * enrichment, lazily fetched per phrase and per UI locale; the resolved
 * payloads are what the tooltip builders and the translation line read. */
const phraseFetches = new Map();      // locale|language|text -> Promise<payload>
const phrasePayloads = new Map();     // same key -> resolved payload
const literalFetches = new Map();     // locale|language|text -> Promise<payload>
const literalPayloads = new Map();    // same key -> resolved payload
const dictionaryFetches = new Map();  // locale|language|word|lemma|pos -> Promise
const dictionaryPayloads = new Map(); // same key -> resolved payload
let phraseTranslationTimer = null;

/* QToolTip-style global bubble: a single body-level layer shown near the
 * hovered/focused token or chip and clamped to the viewport, so tooltips
 * never clip against pane edges the way inline positioned spans would. */
const tipBuilders = new WeakMap();  // element -> () => tooltip content nodes
let tooltip = null;
let tipTarget = null;

const els = {};

function el(id) {
  const node = document.getElementById(id);
  if (!node) throw new Error('missing element #' + id);
  return node;
}

/* Monoline control icons of the phone shell; the stroke follows the text. */
const ICONS = {
  chevron: '<path d="M6 9l6 6 6-6"/>',
  previous: '<path d="M15 5l-7 7 7 7"/>',
  next: '<path d="M9 5l7 7-7 7"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  settings: '<path d="M4 8h3.5M13 8h7M4 16h7M16 16h3.5"/><circle cx="10.5" cy="8" r="2.5"/>'
    + '<circle cx="13.5" cy="16" r="2.5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 8.2h.01M12 11.5V16"/>',
};

function iconSvg(name) {
  return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    + ' stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    + ICONS[name] + '</svg>';
}

/* ---------- busy / warning status line ---------- */

function spinnerNode() {
  const spinner = document.createElement('span');
  spinner.className = 'spinner';
  return spinner;
}

function renderStatus() {
  if (busy) {
    els.statusLine.className = 'busy';
    els.statusLine.replaceChildren(spinnerNode());
    els.statusLine.hidden = false;
  } else if (warning && warning.length) {
    els.statusLine.className = '';
    els.statusLine.textContent = warning.map((message) => i18n.formatMessage(message)).join(' ');
    els.statusLine.hidden = false;
  } else {
    els.statusLine.hidden = true;
  }
}

function setBusy(value) {
  busy = value;
  els.onlineSearchBtn.disabled = value;
  els.fileSelectBtn.disabled = value;
  renderStatus();
}

function renderWarning() {
  renderStatus();
}

/* ---------- localization (Language menu) ---------- */

async function applyLocale(code) {
  await i18n.setLocale(code);
  localStorage.setItem('ui_language', code);
  els.uiLanguage.value = code;
  document.documentElement.lang = code;
  applySymbolSystem();
  retranslate();
}

/* ---------- symbol-system knob (Symbols menu) ---------- */

function symbolSystemMode() {
  return localStorage.getItem('symbol_system') || 'ui';
}

function applySymbolSystem() {
  const mode = symbolSystemMode();
  const system = mode === 'subtitle' && state.subtitleLanguage
    ? grammar.systemForSubtitleLanguage(state.subtitleLanguage)
    : grammar.systemForUiLocale(i18n.locale());
  grammar.setActiveSystem(system);
  els.symbolSystem.value = mode;
}

function onSymbolSystemChanged() {
  localStorage.setItem('symbol_system', els.symbolSystem.value);
  applySymbolSystem();
  renderDetails();
}

/* ---------- retranslation ---------- */

function retranslate() {
  const title = i18n.tr('window_title');
  document.title = title;
  els.appTitle.textContent = title;
  els.tabOnline.textContent = i18n.tr('tab_online_source');
  els.tabFile.textContent = i18n.tr('tab_file_source');
  els.fileSelectBtn.textContent = i18n.tr('button_select_srt');
  els.onlineSearchBtn.textContent = i18n.tr('button_search');
  els.searchTitle.placeholder = i18n.tr('placeholder_subtitle_file');
  els.contextLabel.textContent = i18n.tr('context_label');
  els.legendLabel.textContent = i18n.tr('legend_in_phrase');
  renderHint();
  els.phraseTranslationLabel.textContent = i18n.tr('translation_label');
  els.phraseLiteralLabel.textContent = i18n.tr('translation_literal_label');
  els.symbolsMenuTitle.textContent = i18n.tr('menu_symbols');
  els.languageMenuTitle.textContent = i18n.tr('menu_language');
  els.intro.textContent = i18n.tr('intro_text');
  els.aboutLink.title = i18n.tr('button_about');
  els.aboutLink.setAttribute('aria-label', i18n.tr('button_about'));
  for (const option of els.symbolSystem.options) {
    if (option.value === 'ui') option.textContent = i18n.tr('symbol_system_ui');
    if (option.value === 'subtitle') option.textContent = i18n.tr('symbol_system_subtitle');
  }
  populateSubtitleLanguages();
  retranslateShell();
  renderWarning();
  renderDetails();
  // the translation target follows the UI locale: refetch under the new one
  schedulePhraseTranslation();
}

function populateSubtitleLanguages() {
  els.subtitleLanguage.replaceChildren();
  for (const language of state.languages) {
    const option = document.createElement('option');
    option.value = language.code;
    option.textContent = i18n.tr('language_name_' + language.code);
    els.subtitleLanguage.append(option);
  }
  els.subtitleLanguage.value = state.subtitleLanguage;
}

/* ---------- subtitle language select ---------- */

function currentLanguage() {
  return state.languages.find((language) => language.code === state.subtitleLanguage)
    || {code: state.subtitleLanguage, article_words: []};
}

function onSubtitleLanguageChanged() {
  state.subtitleLanguage = els.subtitleLanguage.value;
  renderSourceSummary();
  // in subtitle mode the painted tradition follows the language selector
  if (symbolSystemMode() === 'subtitle') {
    applySymbolSystem();
    renderDetails();
  }
}

/* ---------- word list (heat colors, port of populate_words_list) ---------- */

/* 250 -> 0 hue over 1..cap, the desktop create_range_interpolator mapping. */
function hueFor(value, cap) {
  const span = Math.max(cap - 1, 1);
  const clamped = Math.min(Math.max(value, 1), cap > 1 ? cap : 1);
  return Math.round(250 + ((clamped - 1) / span) * -250);
}

/* The desktop list paints hsv(hue, 70/255, 100%), which is hsl(hue, 100%, 86%). */
function heatColor(value, cap) {
  return 'hsl(' + hueFor(value, cap) + ', 100%, 86%)';
}

function populateWordsList() {
  els.wordsList.replaceChildren();
  els.wordsList.scrollTop = 0;
  const result = state.analysis;
  if (!result || !Object.keys(result.words).length) return;
  const topCount = Object.values(result.words)[0].count;
  const cap = Math.round(topCount / 5);
  const fragment = document.createDocumentFragment();
  for (const [word, entry] of Object.entries(result.words)) {
    const item = document.createElement('li');
    item.tabIndex = 0;
    item.dataset.word = word;
    const count = document.createElement('span');
    count.className = 'word-count';
    count.textContent = entry.count;
    item.append(word, count);
    const value = entry.count > topCount / 5 ? cap : entry.count;
    item.style.background = heatColor(value, cap);
    item.addEventListener('click', () => chooseWord(word));
    item.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        chooseWord(word);
      }
    });
    fragment.append(item);
  }
  els.wordsList.append(fragment);
}

/* picked in the list: the list panel has done its job */
function chooseWord(word) {
  state.listOpen = false;
  selectWord(word);
}

function selectWord(word) {
  state.selectedWord = word;
  state.inspected = null;
  state.explained = null;
  const previous = els.wordsList.querySelector('.selected');
  if (previous) previous.classList.remove('selected');
  const item = els.wordsList.querySelector('[data-word="' + CSS.escape(word) + '"]');
  if (item) item.classList.add('selected');
  revealSelectedRow();
  renderDetails();
  renderDock();
  els.details.scrollTop = 0;
  schedulePhraseTranslation();
}

/* ---------- word details pane (port of _render_word_meta) ---------- */

function entryPhrase(entry) {
  return entry.phrase === null || entry.phrase === undefined
    ? null : state.analysis.phrases[entry.phrase];
}

/* Part of speech of the occurrence highlighted in the context phrase: the
 * details chip describes this very usage, the aggregate counts move to the
 * subline ('34× · также …'). */
function occurrencePos(entry) {
  const phrase = entryPhrase(entry);
  if (phrase) {
    for (const word of phrase.words) {
      if (isTokenSelected(word, entry)) return word.pos;
    }
  }
  return entry.pos;
}

function entrySubline(entry, language, chipPos) {
  const parts = [];
  const others = Object.entries(entry.pos_counts)
    .filter(([pos]) => pos !== chipPos)
    .sort((a, b) => b[1] - a[1]);
  if (others.length) {
    const items = others
      .map(([pos, count]) => posDisplay(pos, entry.word, language) + ' (' + count + '\u00d7)')
      .join(', ');
    parts.push(i18n.tr('pos_also_line', {items: items}));
  }
  if (entry.possessive_count) {
    const possessive = i18n.ntr('possessive_suffix', entry.possessive_count,
                                {count: entry.possessive_count});
    parts.push(possessive.replace(/^[, ]+/, ''));
  }
  return parts.join(' \u00b7 ');
}

function posDisplay(upos, tokenLower, language) {
  const category = grammar.categoryFor(upos, tokenLower.toLowerCase(), language);
  if (category === grammar.Category.UNMARKED) return upos.toLowerCase();
  return i18n.tr('pos_name_' + grammar.messageSuffix(category));
}

function setChip(chip, category, label, tip) {
  chip.className = 'chip cat-' + category;
  chip.replaceChildren();
  const symbol = document.createElement('span');
  symbol.className = 'sym';
  symbol.innerHTML = grammar.symbolSvg(category);
  chip.append(symbol, document.createTextNode(label));
  if (tip) tipBuilders.set(chip, () => [document.createTextNode(tip)]);
  chip.dataset.category = category;
  if (touchMode()) {  // without a hover the chip is a toggle for its explanation
    chip.setAttribute('role', 'button');
    chip.tabIndex = 0;
  }
}

function renderDetails() {
  if (!state.selectedWord) return;
  const entry = state.analysis && state.analysis.words[state.selectedWord];
  if (!entry) return;
  const language = currentLanguage();
  els.details.hidden = false;
  els.wordLabel.textContent = entry.word;
  const pos = occurrencePos(entry);
  const category = grammar.categoryFor(pos, entry.word.toLowerCase(), language);
  let subline = entry.count + '\u00d7';
  if (category === grammar.Category.UNMARKED) {
    els.wordChip.hidden = true;
    if (pos) {
      subline += ' \u00b7 ' + i18n.tr('pos_suffix', {pos: pos.toLowerCase()}).replace(/^[, ]+/, '');
    }
  } else {
    els.wordChip.hidden = false;
    setChip(els.wordChip, category,
            i18n.tr('pos_name_' + grammar.messageSuffix(category)),
            i18n.tr('pos_tip_' + grammar.tipMessageSuffix(category)));
    const details = entrySubline(entry, language, pos);
    if (details) subline += ' \u00b7 ' + details;
  }
  els.wordSubline.textContent = subline;
  const open = state.explained === 'word' && !els.wordChip.hidden;
  els.wordChip.setAttribute('aria-pressed', String(open));
  showExplanation(els.wordExplain,
                  open ? i18n.tr('pos_tip_' + grammar.tipMessageSuffix(category)) : '');
  renderPhrase(entry, language);
  renderHint();
}

/* ---------- annotated context phrase (port of _render_phrase) ---------- */

function isTokenSelected(word, entry) {
  return word.lemma === entry.word || word.text.toLowerCase() === entry.word.toLowerCase();
}

function tokenTip(word, language, phrase) {
  const category = grammar.categoryFor(word.pos, word.text.toLowerCase(), language);
  if (category === grammar.Category.UNMARKED) return null;
  const posName = i18n.tr('pos_name_' + grammar.messageSuffix(category));
  const header = document.createElement('b');
  header.textContent = word.text;
  const nodes = [header];
  if (word.full_form) {
    const full = document.createElement('b');
    full.textContent = '(' + word.full_form + ')';
    nodes.push(document.createTextNode(' '), full);
  }
  nodes.push(document.createElement('br'),
    ...i18n.trNodes('token_lemma_line', {lemma: word.lemma, pos: posName}, ['lemma']));
  const morphology = grammar.morphologyLine(word.morph, i18n.tr);
  if (morphology) {
    nodes.push(document.createElement('br'), document.createTextNode(morphology));
  }
  appendTranslationLines(nodes, word, language, phrase);
  return nodes;
}

/* Wiktionary translations of the hovered token (primary line) + gloss, both
 * into the active UI locale; the model's aligned word fills in only when the
 * dictionary has nothing for the token - model providers carry no alignment. */
function appendTranslationLines(nodes, word, language, phrase) {
  const payload = phrase ? phrasePayloads.get(phraseKey(phrase)) : null;
  const index = phrase ? phrase.words.indexOf(word) : -1;
  const aligned = payload && payload.words && payload.words[index]
    ? payload.words[index].translation : null;
  const dictionary = dictionaryPayloads.get(dictionaryKey(word, language));
  const terms = [];
  let gloss = null;
  if (dictionary && dictionary.entries.length) {
    for (const item of dictionary.entries) {
      terms.push(...item.translations);
      if (!gloss && item.glosses.length) gloss = item.glosses[0];
    }
  }
  if (terms.length) {
    const ordered = contextualTerms(terms, payload ? payload.translation : null);
    nodes.push(document.createElement('br'),
      ...i18n.trNodes('token_dictionary_line',
                      {translations: ordered.join(', ')}, ['translations']));
  } else if (aligned) {
    nodes.push(document.createElement('br'),
               document.createTextNode(i18n.tr('token_translation_line',
                                               {translation: aligned})));
  }
  if (gloss) {
    nodes.push(document.createElement('br'),
               document.createTextNode(i18n.tr('token_gloss_line', {gloss: gloss})));
  }
}

/* Dictionary terms whose stem occurs in the phrase translation first: the
 * dictionary lists every sense, the translation picked one (жертва among
 * жертвах, хирург among хирургов). A stem match is a shared prefix long
 * enough to cover the inflected ending; Wiktionary stress marks are
 * stripped before comparing. */
function contextualTerms(terms, translation) {
  if (!translation) return terms;
  const words = translation.toLowerCase().split(/[^\p{L}\p{N}]+/u);
  const stem = (term) => term.toLowerCase().normalize('NFD').replace(/\u0301/g, '');
  return terms.map((term, index) => ({term, index, score: contextScore(stem(term), words)}))
    .sort((a, b) => b.score - a.score || a.index - b.index)
    .map((item) => item.term);
}

function contextScore(stem, words) {
  let best = 0;
  for (const word of words) {
    let shared = 0;
    const bound = Math.min(stem.length, word.length);
    while (shared < bound && stem[shared] === word[shared]) shared += 1;
    if (shared >= Math.min(4, stem.length) && shared > best) best = shared;
  }
  return best;
}

function buildToken(word, category, entry, language, phrase) {
  const token = document.createElement('span');
  token.className = 'tok cat-' + category;
  token.tabIndex = 0;
  const symbol = document.createElement('span');
  symbol.className = 'sym';
  symbol.innerHTML = grammar.symbolSvg(category);
  const label = document.createElement('span');
  label.className = 'lbl';
  label.textContent = word.text;
  token.append(symbol, label);
  if (isTokenSelected(word, entry)) token.classList.add('sel');
  const tipNodes = tokenTip(word, language, phrase);
  if (tipNodes) tipBuilders.set(token, () => tokenTip(word, language, phrase));
  return token;
}

function renderPhrase(entry, language) {
  els.phraseView.replaceChildren();
  const categories = [];  // first-occurrence order, unmarked tokens skipped
  const phrase = entryPhrase(entry);
  if (phrase) {
    let group = null;
    phrase.words.forEach((word, index) => {
      const category = grammar.categoryFor(word.pos, word.text.toLowerCase(), language);
      // a token written tight against the previous one in the source ('ll, commas)
      const attached = index > 0 && word.start === phrase.words[index - 1].end;
      if (!group || !attached) {
        group = document.createElement('span');
        group.className = 'tok-grp';
        if (index) els.phraseView.append(document.createTextNode(' '));
        els.phraseView.append(group);
      }
      group.append(buildToken(word, category, entry, language, phrase));
      if (category !== grammar.Category.UNMARKED && !categories.includes(category)) {
        categories.push(category);
      }
    });
  }
  rebuildLegend(categories);
  renderInspection();
}

function rebuildLegend(categories) {
  for (const child of [...els.legend.children]) {
    if (child !== els.legendLabel && child !== els.legendExplain) child.remove();
  }
  let explanation = '';
  for (const category of categories) {
    const tip = i18n.tr('pos_tip_' + grammar.tipMessageSuffix(category));
    const chip = document.createElement('span');
    setChip(chip, category, i18n.tr('pos_name_' + grammar.messageSuffix(category)), tip);
    const open = state.explained === category;
    chip.setAttribute('aria-pressed', String(open));
    if (open) explanation = tip;
    els.legend.append(chip);
  }
  showExplanation(els.legendExplain, explanation);
}

/* ---------- touch: word card, chip explanations, copy button ---------- */

function showExplanation(node, text) {
  node.hidden = !text;
  node.textContent = text;
}

/* Hint under the phrase: a finger cannot hover, and the card explains itself. */
function renderHint() {
  const touch = touchMode();
  els.legendHint.textContent = i18n.tr(touch ? 'legend_hint_touch' : 'legend_hint');
  els.legendHint.hidden = touch && state.inspected !== null;
}

/* The tooltip lines of the inspected token in a persistent card under the
 * phrase: the first line (word, full form) heads it and every following
 * line is a block of its own. */
function renderInspection() {
  const tokens = [...els.phraseView.querySelectorAll('.tok')];
  const builder = state.inspected !== null && tipBuilders.get(tokens[state.inspected]);
  if (!builder) state.inspected = null;
  tokens.forEach((token, index) => token.classList.toggle('active', index === state.inspected));
  els.wordCard.hidden = !builder;
  if (!builder) return;
  const lines = [[]];
  for (const node of builder()) {
    if (node.nodeName === 'BR') lines.push([]);
    else lines[lines.length - 1].push(node);
  }
  els.cardTitle.replaceChildren(...lines[0]);
  els.cardBody.replaceChildren(...lines.slice(1).filter((line) => line.length).map(cardLine));
  const token = tokens[state.inspected];
  const offset = token.getBoundingClientRect().left + token.offsetWidth / 2
    - els.wordCard.getBoundingClientRect().left;
  els.wordCard.style.setProperty('--notch',
    Math.max(14, Math.min(offset, els.wordCard.offsetWidth - 14)) + 'px');
}

function cardLine(nodes) {
  const line = document.createElement('div');
  line.className = 'card-line';
  line.append(...nodes);
  return line;
}

function toggleInspection(index) {
  state.inspected = state.inspected === index ? null : index;
  state.explained = null;
  renderDetails();
  const token = els.phraseView.querySelectorAll('.tok')[index];
  if (token) token.focus({preventScroll: true});
}

/* A chip tap toggles its explanation in place (the word chip: 'word'). */
function onChipActivate(event) {
  const chip = event.target.closest('.chip');
  if (!chip || !touchMode()) return;
  const wordChip = chip === els.wordChip;
  const key = wordChip ? 'word' : chip.dataset.category;
  state.explained = state.explained === key ? null : key;
  renderDetails();
  const again = wordChip ? els.wordChip
    : [...els.legend.querySelectorAll('.chip')].find((node) => node.dataset.category === key);
  if (again) again.focus({preventScroll: true});
}

function onChipKeydown(event) {
  const chip = event.target.closest('.chip');
  if (chip && touchMode() && (event.key === 'Enter' || event.key === ' ')) {
    event.preventDefault();
    onChipActivate(event);
  }
}

let copyTimer = null;  // the button confirms a copy for two seconds

function onCopyPhrase() {
  const phrase = selectedPhrase();
  if (!phrase) return;
  copyText(phraseText(phrase.text));
  els.copyLabel.textContent = i18n.tr('phrase_copied');
  clearTimeout(copyTimer);
  copyTimer = setTimeout(() => { els.copyLabel.textContent = i18n.tr('button_copy_phrase'); }, 2000);
}

/* phrase tokens: arrow-key navigation with tooltip, port of keyPressEvent */
function onPhraseKeydown(event) {
  const token = event.target.closest('.tok');
  if (token && touchMode() && (event.key === 'Enter' || event.key === ' ')) {
    // a keyboard on a touch device: Enter toggles the focused token's card
    event.preventDefault();
    toggleInspection([...els.phraseView.querySelectorAll('.tok')].indexOf(token));
    return;
  }
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
  const tokens = [...els.phraseView.querySelectorAll('.tok')];
  if (!tokens.length) return;
  const index = tokens.indexOf(document.activeElement);
  const next = event.key === 'ArrowRight'
    ? Math.max(index, 0) + 1 >= tokens.length ? tokens.length - 1 : Math.max(index, 0) + 1
    : Math.max(Math.min(index, tokens.length - 1) - 1, 0);
  tokens[next].focus();
  event.preventDefault();
}

/* ---------- phrase clipboard: click-to-copy and clean selection ---------- */

/* The source text with whitespace runs (subtitle line breaks, spaces a
 * sloppy drag picks up) collapsed and trimmed. */
function phraseText(text) {
  return text.replace(/\s+/g, ' ').trim();
}

/* Clipboard write for plain-HTTP origins too, where the async clipboard API
 * is not exposed: a temporary textarea selection does there (and whenever
 * the API refuses). */
function copyText(text) {
  const legacyCopy = () => {
    const helper = document.createElement('textarea');
    helper.value = text;
    helper.style.cssText = 'position:fixed;opacity:0';
    document.body.append(helper);
    helper.select();
    document.execCommand('copy');
    helper.remove();
  };
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).catch(legacyCopy);
    return;
  }
  legacyCopy();
}

function onPhraseCopy(event) {
  const selection = window.getSelection();
  if (!els.phraseView.contains(selection.anchorNode)
      || !els.phraseView.contains(selection.focusNode)) return;
  event.clipboardData.setData('text/plain', phraseText(selection.toString()));
  event.preventDefault();
}

/* A finger lands between words as often as on them, and the shortest ones
 * ("a", "of") can never be wide enough: the phrase is one tap surface and
 * the nearest token to the tap wins. */
function nearestToken(point) {
  const tokens = [...els.phraseView.querySelectorAll('.tok')];
  let nearest = -1;
  let best = Infinity;
  tokens.forEach((token, index) => {
    const box = token.getBoundingClientRect();
    const dx = point.clientX - (box.left + box.width / 2);
    const dy = (point.clientY - (box.top + box.height / 2)) * 2;
    const score = dx * dx + dy * dy;
    if (score < best) {
      best = score;
      nearest = index;
    }
  });
  return {index: nearest, token: tokens[nearest]};
}

function onPhraseClick(event) {
  if (window.getSelection().toString()) return;  // a drag-select ended here
  if (touchMode()) {
    // a tap inspects the word; tokens without a tooltip (punctuation) only close
    const nearest = nearestToken(event);
    if (tipBuilders.has(nearest.token)) toggleInspection(nearest.index);
    else if (state.inspected !== null) toggleInspection(state.inspected);
    return;
  }
  const phrase = selectedPhrase();
  if (phrase) copyText(phraseText(phrase.text));
}

/* ---------- offline phrase translation + dictionary enrichment ---------- */

function selectedPhrase() {
  const entry = state.analysis && state.analysis.words[state.selectedWord];
  return entry && entry.phrase !== null && entry.phrase !== undefined
    ? state.analysis.phrases[entry.phrase] : null;
}

function dictionaryKey(word, language) {
  return [i18n.locale(), language.code, word.text.toLowerCase(), word.lemma, word.pos].join('|');
}

function phraseKey(phrase) {
  return [i18n.locale(), state.analysis.language_code, phrase.text].join('|');
}

function fetchPhraseTranslation(phrase) {
  const key = phraseKey(phrase);
  if (!phraseFetches.has(key)) {
    const request = fetch('api/translate/phrase', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: phrase.text,
                            language: state.analysis.language_code,
                            target: i18n.locale()}),
    }).then(async (response) => {
      const payload = response.ok ? await response.json() : {unavailable: true};
      phrasePayloads.set(key, payload);
      return payload;
    }).catch(() => {
      const payload = {unavailable: true};
      phrasePayloads.set(key, payload);
      return payload;
    });
    phraseFetches.set(key, request);
  }
  return phraseFetches.get(key);
}

function fetchDictionaryEntry(word, language) {
  const key = dictionaryKey(word, language);
  if (!dictionaryFetches.has(key)) {
    const query = new URLSearchParams({language: language.code, target: i18n.locale(),
                                       word: word.text, lemma: word.lemma, pos: word.pos});
    const request = fetch('api/dictionary/lookup?' + query)
      .then(async (response) => {
        const payload = response.ok ? await response.json() : {entries: []};
        dictionaryPayloads.set(key, payload);
        return payload;
      }).catch(() => {
        const payload = {entries: []};
        dictionaryPayloads.set(key, payload);
        return payload;
      });
    dictionaryFetches.set(key, request);
  }
  return dictionaryFetches.get(key);
}

/* instant word-by-word dictionary view: served before the model answers */
function fetchLiteralTranslation(phrase) {
  const key = phraseKey(phrase);
  if (!literalFetches.has(key)) {
    const request = fetch('api/translate/literal', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: phrase.text,
                            language: state.analysis.language_code,
                            target: i18n.locale()}),
    }).then(async (response) => {
      const payload = response.ok ? await response.json() : {unavailable: true};
      literalPayloads.set(key, payload);
      return payload;
    }).catch(() => {
      const payload = {unavailable: true};
      literalPayloads.set(key, payload);
      return payload;
    });
    literalFetches.set(key, request);
  }
  return literalFetches.get(key);
}

function renderLiteralTranslation(phrase, payload) {
  els.phraseLiteral.hidden = !payload || !payload.literal;
  if (payload && payload.literal) {
    els.phraseLiteralText.textContent = payload.literal;
  }
}

function schedulePhraseTranslation() {
  clearTimeout(phraseTranslationTimer);
  phraseTranslationTimer = setTimeout(updatePhraseTranslation, 300);
}

async function updatePhraseTranslation() {
  const phrase = selectedPhrase();
  if (!phrase) {
    els.phraseTranslation.hidden = true;
    els.phraseLiteral.hidden = true;
    return;
  }
  renderPhraseTranslation(phrase, null);  // spinner while the model generates
  renderLiteralTranslation(phrase, await fetchLiteralTranslation(phrase));
  const payload = await fetchPhraseTranslation(phrase);
  if (selectedPhrase() !== phrase) return;  // selection moved on meanwhile
  renderPhraseTranslation(phrase, payload);
  // tooltips read the dictionary caches lazily, so just warm them per token
  const language = currentLanguage();
  for (const word of phrase.words) {
    if (grammar.categoryFor(word.pos, word.text.toLowerCase(), language)
        !== grammar.Category.UNMARKED) {
      fetchDictionaryEntry(word, language);
    }
  }
}

function renderPhraseTranslation(phrase, payload) {
  els.phraseTranslation.hidden = false;
  const text = els.phraseTranslationText;
  text.className = '';
  if (!payload) {
    text.replaceChildren(spinnerNode(), document.createTextNode(' '));
    return;
  }
  if (payload.unavailable) {
    text.className = 'unavailable';
    text.textContent = i18n.tr('translation_unavailable');
    return;
  }
  text.textContent = payload.translation;
}

/* ---------- analysis loading ---------- */

function applyAnalysis(analysis) {
  state.analysis = analysis;
  state.selectedWord = '';
  state.inspected = null;
  state.explained = null;
  state.listOpen = true;  // the words are what comes first
  phraseFetches.clear();
  phrasePayloads.clear();
  literalFetches.clear();
  literalPayloads.clear();
  dictionaryFetches.clear();
  dictionaryPayloads.clear();
  els.intro.hidden = true;  // the start-screen description has served its purpose
  els.details.hidden = true;
  els.phraseTranslation.hidden = true;
  els.phraseLiteral.hidden = true;
  populateWordsList();
  renderDock();
}

async function loadOnline(event) {
  event.preventDefault();
  warning = null;
  const query = els.searchTitle.value.trim();
  setBusy(true);
  try {
    const response = await fetch('api/analyze/online', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query,
                            language: state.subtitleLanguage}),
    });
    const payload = await response.json();
    if (payload.analysis) {
      applyAnalysis(payload.analysis);
      state.sourceLabel = query;
    }
    warning = payload.messages;
  } catch (error) {
    console.error(error);
    warning = [{code: 'subtitles_service_error', params: {}}];
  } finally {
    setBusy(false);
  }
  sourceLoaded();
}

async function loadFile(file) {
  warning = null;
  setBusy(true);
  try {
    const form = new FormData();
    form.append('file', file);
    form.append('language', state.subtitleLanguage);
    const response = await fetch('api/analyze/file', {method: 'POST', body: form});
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      warning = [detail && detail.detail && detail.detail.message
        ? detail.detail.message
        : {code: 'unable_to_load_file', params: {path: file.name}}];
    } else {
      applyAnalysis(await response.json());
      state.sourceLabel = file.name;
    }
  } catch (error) {
    console.error(error);
    warning = [{code: 'unable_to_load_file', params: {path: file.name}}];
  } finally {
    setBusy(false);
  }
  sourceLoaded();
}

/* ---------- global tooltip layer ---------- */

function hideTip() {
  tipTarget = null;
  tooltip.hidden = true;
}

function showTipFor(element) {
  const builder = tipBuilders.get(element);
  if (!builder) return;
  tipTarget = element;
  tooltip.replaceChildren(...builder());
  tooltip.hidden = false;
  const tipRect = tooltip.getBoundingClientRect();
  const rect = element.getBoundingClientRect();
  const margin = 8;
  let left = rect.left + rect.width / 2 - tipRect.width / 2;
  left = Math.max(margin, Math.min(left, window.innerWidth - tipRect.width - margin));
  // tokens read above their symbol row, chips read below the pill; flip when
  // the preferred side has no room, then clamp into the viewport
  let above = rect.top - tipRect.height - 8;
  let below = rect.bottom + 8;
  let top = element.classList.contains('chip') ? below : above;
  if (element.classList.contains('chip') && below + tipRect.height > window.innerHeight - margin) {
    top = above;
  }
  if (!element.classList.contains('chip') && above < margin) {
    top = below;
  }
  top = Math.max(margin, Math.min(top, window.innerHeight - tipRect.height - margin));
  tooltip.style.left = Math.round(left) + 'px';
  tooltip.style.top = Math.round(top) + 'px';
}

function tipElementFor(target) {
  const element = target.closest('.tok, .chip');
  return element && tipBuilders.has(element) ? element : null;
}

/* the bubble belongs to pointers: a finger never opens it */
function hoverTipTarget(target) {
  return touchMode() ? null : tipElementFor(target);
}

function initTooltipLayer() {
  tooltip = document.createElement('div');
  tooltip.id = 'tooltip';
  tooltip.setAttribute('role', 'tooltip');
  tooltip.hidden = true;
  document.body.append(tooltip);

  document.addEventListener('mouseover', (event) => {
    const element = hoverTipTarget(event.target);
    if (element === tipTarget) return;
    if (!element) {
      hideTip();
      return;
    }
    showTipFor(element);
  });
  document.addEventListener('mouseout', (event) => {
    if (!tipTarget) return;
    if (event.relatedTarget && tipTarget.contains(event.relatedTarget)) return;
    hideTip();
  });
  document.addEventListener('focusin', (event) => {
    const element = hoverTipTarget(event.target);
    if (element) showTipFor(element);
  });
  document.addEventListener('focusout', () => hideTip());
  // fixed positioning goes stale when the pane scrolls under the cursor
  document.addEventListener('scroll', () => hideTip(), true);
}

/* ---------- wiring ---------- */

function switchSourceTab(activeTab, activePane) {
  for (const tab of [els.tabOnline, els.tabFile]) tab.classList.remove('active');
  activeTab.classList.add('active');
  els.paneOnline.classList.toggle('hidden', activePane !== els.paneOnline);
  els.paneFile.classList.toggle('hidden', activePane !== els.paneFile);
  renderSourceSummary();
}

/* ---------- phone shell: dock, list panel, collapsed header and source ---------- */

function wordOrder() {
  return state.analysis ? Object.keys(state.analysis.words) : [];
}

/* The list is the content until a word is picked; afterwards the bottom-bar
 * button unfolds it upwards, out of the details area, next to that button. */
function renderDock() {
  const order = wordOrder();
  const index = order.indexOf(state.selectedWord);
  els.dock.hidden = !order.length;
  els.wordPosition.textContent = index < 0 ? ''
    : i18n.tr('word_position', {current: index + 1, total: order.length});
  els.wordPrevious.disabled = index <= 0;
  els.wordNext.disabled = index === order.length - 1;
  els.listToggle.disabled = index < 0;
  els.listPanel.hidden = !order.length || !(state.listOpen || index < 0);
  els.listToggle.setAttribute('aria-expanded', String(!els.listPanel.hidden));
}

function revealSelectedRow() {
  const item = els.wordsList.querySelector('.selected');
  if (item) item.scrollIntoView({block: 'nearest'});
}

/* previous/next walk the frequency list without leaving the word */
function stepWord(step) {
  const order = wordOrder();
  const index = Math.max(order.indexOf(state.selectedWord), 0) + step;
  if (index < 0 || index >= order.length) return;
  selectWord(order[index]);
}

function renderSourceSummary() {
  const fileSource = !els.paneFile.classList.contains('hidden');
  els.sourceName.textContent = state.sourceLabel
    || i18n.tr(fileSource ? 'tab_file_source' : 'tab_online_source');
  els.sourceLanguage.textContent = i18n.tr('language_name_' + state.subtitleLanguage);
}

function setSourceOpen(open) {
  els.sourceSummary.setAttribute('aria-expanded', String(open));
}

/* after a load attempt: the summary names the source and folds the form; a
 * failure keeps it open for another try */
function sourceLoaded() {
  renderSourceSummary();
  setSourceOpen(warning && warning.length > 0);
}

function retranslateShell() {
  els.settingsToggle.setAttribute('aria-label', i18n.tr('menu_settings'));
  els.sourceCaption.textContent = i18n.tr('source_label');
  els.listToggleLabel.textContent = i18n.tr('word_list');
  els.wordPrevious.setAttribute('aria-label', i18n.tr('word_previous'));
  els.wordNext.setAttribute('aria-label', i18n.tr('word_next'));
  els.cardClose.setAttribute('aria-label', i18n.tr('button_close'));
  els.copyLabel.textContent = i18n.tr('button_copy_phrase');
  renderSourceSummary();
  renderDock();
}

/* a pointer appears or disappears (tablet with a trackpad, resized window) */
function onInputModeChange() {
  hideTip();
  state.inspected = null;
  state.explained = null;
  renderDetails();
  renderHint();
}

function collectShellElements() {
  els.menubar = el('menubar');
  els.settingsToggle = el('settings-toggle');
  els.sourceSummary = el('source-summary');
  els.sourceCaption = el('source-caption');
  els.sourceName = el('source-name');
  els.sourceLanguage = el('source-language');
  els.listPanel = el('list-panel');
  els.dock = el('dock');
  els.listToggle = el('list-toggle');
  els.listToggleLabel = el('list-toggle-label');
  els.wordPosition = el('word-position');
  els.wordPrevious = el('word-previous');
  els.wordNext = el('word-next');
  els.copyPhrase = el('copy-phrase');
  els.copyLabel = el('copy-phrase-label');
  els.wordCard = el('word-card');
  els.cardTitle = el('card-title');
  els.cardClose = el('card-close');
  els.cardBody = el('card-body');
  els.wordExplain = el('word-explain');
  els.legendExplain = el('legend-explain');
  for (const node of document.querySelectorAll('[data-icon]')) {
    node.innerHTML = iconSvg(node.dataset.icon);
  }
}

function wireShell() {
  els.settingsToggle.addEventListener('click', () => {
    const open = els.menubar.classList.toggle('settings-open');
    els.settingsToggle.setAttribute('aria-expanded', String(open));
  });
  els.sourceSummary.addEventListener('click', () => setSourceOpen(
    els.sourceSummary.getAttribute('aria-expanded') !== 'true'));
  els.listToggle.addEventListener('click', () => {
    state.listOpen = !state.listOpen;
    renderDock();
    revealSelectedRow();
  });
  els.wordPrevious.addEventListener('click', () => stepWord(-1));
  els.wordNext.addEventListener('click', () => stepWord(1));
  els.cardClose.addEventListener('click', () => toggleInspection(state.inspected));
  els.copyPhrase.addEventListener('click', onCopyPhrase);
  els.details.addEventListener('click', onChipActivate);
  els.details.addEventListener('keydown', onChipKeydown);
  hoverInput.addEventListener('change', onInputModeChange);
}

async function init() {
  els.appTitle = el('app-title');
  els.aboutLink = el('about-link');
  els.intro = el('intro');
  els.symbolsMenuTitle = el('symbols-menu-title');
  els.languageMenuTitle = el('language-menu-title');
  els.symbolSystem = el('symbol-system');
  els.uiLanguage = el('ui-language');
  els.tabOnline = el('tab-online');
  els.tabFile = el('tab-file');
  els.paneOnline = el('pane-online');
  els.paneFile = el('pane-file');
  els.searchTitle = el('online-search-title');
  els.subtitleLanguage = el('subtitle-language');
  els.onlineSearchBtn = el('online-search-btn');
  els.filePathDisplay = el('file-path-display');
  els.fileSelectBtn = el('file-select-btn');
  els.fileInput = el('file-input');
  els.statusLine = el('status-line');
  els.wordsList = el('words-list');
  els.details = el('details');
  els.wordLabel = el('selected-word-label');
  els.wordChip = el('selected-pos-chip');
  els.wordSubline = el('selected-word-subline');
  els.contextLabel = el('context-label');
  els.phraseView = el('phrase-view');
  els.phraseTranslation = el('phrase-translation');
  els.phraseTranslationLabel = el('phrase-translation-label');
  els.phraseTranslationText = el('phrase-translation-text');
  els.phraseLiteral = el('phrase-literal');
  els.phraseLiteralLabel = el('phrase-literal-label');
  els.phraseLiteralText = el('phrase-literal-text');
  els.legend = el('legend');
  els.legendLabel = el('legend-label');
  els.legendHint = el('legend-hint');
  collectShellElements();

  els.paneOnline.addEventListener('submit', loadOnline);
  els.tabOnline.addEventListener('click', () => switchSourceTab(els.tabOnline, els.paneOnline));
  els.tabFile.addEventListener('click', () => switchSourceTab(els.tabFile, els.paneFile));
  els.fileSelectBtn.addEventListener('click', () => els.fileInput.click());
  els.fileInput.addEventListener('change', () => {
    const file = els.fileInput.files[0];
    if (!file) return;
    els.filePathDisplay.textContent = file.name;
    loadFile(file);
  });
  els.subtitleLanguage.addEventListener('change', onSubtitleLanguageChanged);
  els.symbolSystem.addEventListener('change', onSymbolSystemChanged);
  els.uiLanguage.addEventListener('change', () => applyLocale(els.uiLanguage.value));
  els.phraseView.addEventListener('keydown', onPhraseKeydown);
  els.phraseView.addEventListener('copy', onPhraseCopy);
  els.phraseView.addEventListener('click', onPhraseClick);
  initTooltipLayer();
  wireShell();

  state.languages = await (await fetch('api/languages')).json();
  const stored = localStorage.getItem('ui_language');
  await applyLocale(stored && i18n.LOCALES.includes(stored)
    ? stored : i18n.detectLocale());
}

init().catch((error) => console.error('init failed', error));
