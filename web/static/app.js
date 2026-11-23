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
};

let warning = null;  // list of {code, params} core events or null
let busy = false;

/* Offline phrase translation (NLLB) + Wiktionary enrichment, lazily fetched
 * per phrase and per UI locale; the resolved payloads are what the tooltip
 * builders and the translation line read. */
const phraseFetches = new Map();      // locale|language|text -> Promise<payload>
const phrasePayloads = new Map();     // same key -> resolved payload
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
  els.legendHint.textContent = i18n.tr('legend_hint');
  els.phraseTranslationLabel.textContent = i18n.tr('translation_label');
  els.symbolsMenuTitle.textContent = i18n.tr('menu_symbols');
  els.languageMenuTitle.textContent = i18n.tr('menu_language');
  for (const option of els.symbolSystem.options) {
    if (option.value === 'ui') option.textContent = i18n.tr('symbol_system_ui');
    if (option.value === 'subtitle') option.textContent = i18n.tr('symbol_system_subtitle');
  }
  populateSubtitleLanguages();
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
    item.textContent = word;
    item.tabIndex = 0;
    item.dataset.word = word;
    const value = entry.count > topCount / 5 ? cap : entry.count;
    item.style.background = 'hsl(' + hueFor(value, cap) + ', 100%, 65%)';
    item.addEventListener('click', () => selectWord(word));
    item.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectWord(word);
      }
    });
    fragment.append(item);
  }
  els.wordsList.append(fragment);
}

function selectWord(word) {
  state.selectedWord = word;
  const previous = els.wordsList.querySelector('.selected');
  if (previous) previous.classList.remove('selected');
  const item = els.wordsList.querySelector('[data-word="' + CSS.escape(word) + '"]');
  if (item) item.classList.add('selected');
  renderDetails();
  schedulePhraseTranslation();
}

/* ---------- word details pane (port of _render_word_meta) ---------- */

function entrySubline(entry, language) {
  const parts = [];
  const others = Object.entries(entry.pos_counts)
    .filter(([pos]) => pos !== entry.pos)
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
}

function renderDetails() {
  if (!state.selectedWord) return;
  const entry = state.analysis && state.analysis.words[state.selectedWord];
  if (!entry) return;
  const language = currentLanguage();
  els.details.hidden = false;
  els.wordLabel.textContent = entry.word;
  els.wordCount.textContent = entry.count + '\u00d7';
  const category = grammar.categoryFor(entry.pos, entry.word.toLowerCase(), language);
  let subline = '';
  if (category === grammar.Category.UNMARKED) {
    els.wordChip.hidden = true;
    if (entry.pos) {
      subline = i18n.tr('pos_suffix', {pos: entry.pos.toLowerCase()}).replace(/^[, ]+/, '');
    }
  } else {
    els.wordChip.hidden = false;
    setChip(els.wordChip, category,
            i18n.tr('pos_name_' + grammar.messageSuffix(category)),
            i18n.tr('pos_tip_' + grammar.tipMessageSuffix(category)));
    subline = entrySubline(entry, language);
  }
  els.wordSubline.textContent = subline;
  els.wordSubline.hidden = !subline;
  renderPhrase(entry, language);
}

/* ---------- annotated context phrase (port of _render_phrase) ---------- */

function isTokenSelected(word, entry) {
  return word.lemma === entry.word || word.text.toLowerCase() === entry.word.toLowerCase();
}

function tokenTip(word, entry, language, phrase) {
  const category = grammar.categoryFor(word.pos, word.text.toLowerCase(), language);
  if (category === grammar.Category.UNMARKED) return null;
  const posName = i18n.tr('pos_name_' + grammar.messageSuffix(category));
  const selected = isTokenSelected(word, entry);
  const nodes = [document.createElement('b'), document.createElement('br'),
                 document.createTextNode(i18n.tr('token_lemma_line',
                                                 {lemma: word.lemma, pos: posName}))];
  nodes[0].textContent = word.text;
  const morphology = grammar.morphologyLine(word.morph, i18n.tr);
  if (morphology) {
    nodes.push(document.createElement('br'), document.createTextNode(morphology));
  }
  appendTranslationLines(nodes, word, language, phrase);
  if (selected) {
    nodes.push(document.createElement('br'), document.createTextNode(entry.count + '\u00d7'));
  }
  return nodes;
}

/* Wiktionary translations of the hovered token (primary line) + gloss, both
 * into the active UI locale; the model's aligned word fills in only when the
 * dictionary has nothing for the token - the NLLB cross-attention alignment
 * is too unreliable to show beside real translations. */
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
               document.createTextNode(i18n.tr('token_dictionary_line',
                                               {translations: ordered.join(', ')})));
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
  const tipNodes = tokenTip(word, entry, language, phrase);
  if (tipNodes) tipBuilders.set(token, () => tokenTip(word, entry, language, phrase));
  return token;
}

function renderPhrase(entry, language) {
  els.phraseView.replaceChildren();
  const categories = [];  // first-occurrence order, unmarked tokens skipped
  const phrase = entry.phrase === null || entry.phrase === undefined
    ? null : state.analysis.phrases[entry.phrase];
  if (phrase) {
    for (const word of phrase.words) {
      const category = grammar.categoryFor(word.pos, word.text.toLowerCase(), language);
      els.phraseView.append(buildToken(word, category, entry, language, phrase));
      if (category !== grammar.Category.UNMARKED && !categories.includes(category)) {
        categories.push(category);
      }
    }
  }
  rebuildLegend(categories);
}

function rebuildLegend(categories) {
  for (const child of [...els.legend.children]) {
    if (child !== els.legendLabel) child.remove();
  }
  for (const category of categories) {
    const chip = document.createElement('span');
    setChip(chip, category,
            i18n.tr('pos_name_' + grammar.messageSuffix(category)),
            i18n.tr('pos_tip_' + grammar.tipMessageSuffix(category)));
    els.legend.append(chip);
  }
}

/* phrase tokens: arrow-key navigation with tooltip, port of keyPressEvent */
function onPhraseKeydown(event) {
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
    const request = fetch('/api/translate/phrase', {
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
    const request = fetch('/api/dictionary/lookup?' + query)
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

function schedulePhraseTranslation() {
  clearTimeout(phraseTranslationTimer);
  phraseTranslationTimer = setTimeout(updatePhraseTranslation, 300);
}

async function updatePhraseTranslation() {
  const phrase = selectedPhrase();
  if (!phrase) {
    els.phraseTranslation.hidden = true;
    return;
  }
  renderPhraseTranslation(phrase, null);  // spinner while the model decodes
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
  phraseFetches.clear();
  phrasePayloads.clear();
  dictionaryFetches.clear();
  dictionaryPayloads.clear();
  els.details.hidden = true;
  els.phraseTranslation.hidden = true;
  populateWordsList();
}

async function loadOnline(event) {
  event.preventDefault();
  warning = null;
  setBusy(true);
  try {
    const response = await fetch('/api/analyze/online', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: els.searchTitle.value.trim(),
                            language: state.subtitleLanguage}),
    });
    const payload = await response.json();
    if (payload.analysis) applyAnalysis(payload.analysis);
    warning = payload.messages;
  } catch (error) {
    console.error(error);
    warning = [{code: 'subtitles_service_error', params: {}}];
  } finally {
    setBusy(false);
  }
}

async function loadFile(file) {
  warning = null;
  setBusy(true);
  try {
    const form = new FormData();
    form.append('file', file);
    form.append('language', state.subtitleLanguage);
    const response = await fetch('/api/analyze/file', {method: 'POST', body: form});
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      warning = [detail && detail.detail && detail.detail.message
        ? detail.detail.message
        : {code: 'unable_to_load_file', params: {path: file.name}}];
    } else {
      applyAnalysis(await response.json());
    }
  } catch (error) {
    console.error(error);
    warning = [{code: 'unable_to_load_file', params: {path: file.name}}];
  } finally {
    setBusy(false);
  }
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

function initTooltipLayer() {
  tooltip = document.createElement('div');
  tooltip.id = 'tooltip';
  tooltip.setAttribute('role', 'tooltip');
  tooltip.hidden = true;
  document.body.append(tooltip);

  document.addEventListener('mouseover', (event) => {
    const element = tipElementFor(event.target);
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
    const element = tipElementFor(event.target);
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
}

async function init() {
  els.appTitle = el('app-title');
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
  els.wordCount = el('selected-word-count-label');
  els.wordSubline = el('selected-word-subline');
  els.contextLabel = el('context-label');
  els.phraseView = el('phrase-view');
  els.phraseTranslation = el('phrase-translation');
  els.phraseTranslationLabel = el('phrase-translation-label');
  els.phraseTranslationText = el('phrase-translation-text');
  els.legend = el('legend');
  els.legendLabel = el('legend-label');
  els.legendHint = el('legend-hint');

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
  initTooltipLayer();

  state.languages = await (await fetch('/api/languages')).json();
  const stored = localStorage.getItem('ui_language');
  await applyLocale(stored && i18n.LOCALES.includes(stored)
    ? stored : i18n.detectLocale());
}

init().catch((error) => console.error('init failed', error));
