"""Offline translation engine bake-off on real subtitle phrases.

Phrases are extracted with the real analysis pipeline (the same sanitizing,
spam filtering and spaCy tokenization the web backend uses), engines
translate the last N cues of each sample file into the remaining UI
locales, every result is cached per engine/pair under tmp/bench/results/
so interrupted runs resume, and ``--report`` renders a side-by-side
markdown/HTML comparison.

Usage:
    poetry run python tools/benchmark_translation.py --extract
    poetry run python tools/benchmark_translation.py --engine madlad3b
    poetry run python tools/benchmark_translation.py --all
    poetry run python tools/benchmark_translation.py --report
"""
import argparse
import json
import logging
import os
import sqlite3
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from core import analyzer  # noqa: E402
from core.dictionary import KaikkiDictionary  # noqa: E402

logger = logging.getLogger('benchmark')

RESULTS_DIR = REPO / 'tmp' / 'bench' / 'results'
LLAMA_BIN = REPO / 'tmp' / 'bench' / 'bin' / 'llama-b12651' / 'llama-server'
MODELS_DIR = Path(os.environ.get('SUBTITLE_LEARNING_DATA_DIR',
                                 REPO / 'data')) / 'models'
DICTIONARY_DB = Path(os.environ.get('SUBTITLE_LEARNING_DATA_DIR',
                                    REPO / 'data')) / 'dictionary' / 'kaikki.sqlite'

SAMPLES = [
    ('samples/The Big Lebowski (1998) 1080p Bluray x264 {Hindi Org DD 5.1} '
     '{English DTS 5.1} ESubs.srt', 'eng'),
    ('samples/The Big Lebowski (1998) DE.srt', 'deu'),
    ('samples/The Big Lebowski (1998) RU.srt', 'rus'),
]
SOURCE_LOCALE = {'eng': 'en', 'deu': 'de', 'rus': 'ru'}
UI_LOCALES = ('en', 'de', 'ru', 'th')
PHRASES_PER_FILE = 30

LANG_NAMES = {'en': 'English', 'de': 'German', 'ru': 'Russian', 'th': 'Thai'}
LANG_TAGS = {'en': 'en', 'de': 'de', 'ru': 'ru', 'th': 'th'}
NLLB_CODES = {'en': 'eng_Latn', 'de': 'deu_Latn', 'ru': 'rus_Cyrl',
              'th': 'tha_Thai'}
MADLAD_CODES = {'en': '<2en>', 'de': '<2de>', 'ru': '<2ru>', 'th': '<2th>'}

GLOSSARY_POS = {'NOUN', 'VERB', 'ADJ', 'ADV', 'PROPN', 'NUM'}
GLOSSARY_LIMIT = 8

SUBTITLE_SYSTEM = (
    'You are a professional subtitle translator. Translate subtitle lines '
    'accurately, preserving tone, register and colloquial style. '
    'Output only the translation.')


def load_env():
    """Minimal .env reader: KEY=VALUE lines, no quoting."""
    env = {}
    env_file = REPO / '.env'
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env[key.strip()] = value.strip()
    return env


# ---------------------------------------------------------------------------
# phrase extraction (real pipeline)


def extract_phrase_sets():
    """Last PHRASES_PER_FILE sanitized cues per sample, spaCy-annotated."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    sets = {}
    for rel_path, code in SAMPLES:
        subs = analyzer.parse_raw(analyzer.read_subtitles_file(str(REPO / rel_path)))
        texts = [analyzer.sanitize_phrase_text(sub.content) for sub in subs]
        texts = [text for text in texts
                 if text and not analyzer.www_spam_filter.search(text)]
        texts = texts[-PHRASES_PER_FILE:]
        annotated = [{**{'text': text},
                      'words': [{'text': w.text, 'lemma': w.lemma, 'pos': w.pos,
                                 'morph': w.morph, 'start': w.start, 'end': w.end}
                                for w in analyzer.tokenize_phrase(text, code)]}
                     for text in texts]
        sets[code] = {'file': rel_path, 'phrases': annotated}
        logger.info('%s (%s): %d phrases', rel_path, code, len(annotated))
    out = RESULTS_DIR / 'phrases.json'
    out.write_text(json.dumps(sets, ensure_ascii=False, indent=1))
    logger.info('Wrote %s', out)


def load_phrase_sets():
    return json.loads((RESULTS_DIR / 'phrases.json').read_text())


def pairs_for(code):
    return [locale for locale in UI_LOCALES if locale != SOURCE_LOCALE[code]]


# ---------------------------------------------------------------------------
# glossary (POE metadata + Wiktionary dictionary -> term list)


def build_glossary(dictionary, source_code, target_locale, words):
    """Term list for glossary-augmented prompting; empty when nothing found."""
    glossary = []
    for word in words:
        if word['pos'] not in GLOSSARY_POS or len(glossary) >= GLOSSARY_LIMIT:
            continue
        result = dictionary.lookup(source_code, target_locale, word['text'],
                                   lemma=word['lemma'], pos=word['pos'])
        for entry in result['entries']:
            # lookup already prefers rows carrying target-locale translations
            # and _entry_to_dict narrows 'translations' to that locale's list
            translations = entry['translations']
            if translations:
                glossary.append(f"{word['text']} -> {translations[0]}")
                break
            if entry['glosses']:
                glossary.append(f"{word['text']} -> {entry['glosses'][0]}")
                break
    return glossary


# ---------------------------------------------------------------------------
# engines


class CT2Engine:
    """In-process CTranslate2 encoder-decoder (NLLB or MADLAD flavor)."""

    def __init__(self, key, model_dir, kind, pairs=None):
        self.key = key
        self.model_dir = MODELS_DIR / model_dir
        self.kind = kind
        self.pairs = pairs
        self._translator = None
        self._tokenizer = None

    def _load(self):
        if self._translator is not None:
            return
        import ctranslate2
        self._translator = ctranslate2.Translator(str(self.model_dir),
                                                  device='cpu')
        if self.kind == 'nllb':
            from transformers import AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
        else:
            import sentencepiece
            self._tokenizer = sentencepiece.SentencePieceProcessor(
                model_file=str(self.model_dir / 'spiece.model'))
        logger.info('%s: model loaded (%s)', self.key, self.model_dir)

    def translate(self, text, source_code, target_locale, words):
        self._load()
        target = NLLB_CODES[target_locale] if self.kind == 'nllb' \
            else MADLAD_CODES[target_locale]
        start = time.perf_counter()
        if self.kind == 'nllb':
            pieces = self._tokenizer.tokenize(text)
            source = [NLLB_CODES[SOURCE_LOCALE[source_code]]] + pieces + ['</s>']
            result = self._translator.translate_batch(
                [source], target_prefix=[[target]], beam_size=4)
            output = result[0].hypotheses[0]
            body = [token for token in output if token != target and token != '</s>']
            ids = self._tokenizer.convert_tokens_to_ids(body)
            translation = self._tokenizer.decode(ids, skip_special_tokens=True)
        else:
            pieces = self._tokenizer.encode(text, out_type=str)
            source = [target] + pieces
            result = self._translator.translate_batch([source], beam_size=4)
            body = [token for token in result[0].hypotheses[0]
                    if token != '</s>']
            translation = self._tokenizer.decode(body).replace('▁', ' ')
        return translation.strip(), (time.perf_counter() - start) * 1000


class HTTPError(Exception):
    pass


def _post_json(url, payload, timeout, headers=None):
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json', **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def _get_ok(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.status == 200


def _strip_reasoning(text):
    for tag in ('think', 'thinking', 'reasoning'):
        for open_tag, close_tag in ((f'<{tag}>', f'</{tag}>'),
                                    (f'<{tag}_thought>', f'</{tag}_thought>')):
            while open_tag in text and close_tag in text:
                head, rest = text.split(open_tag, 1)
                _block, text = rest.split(close_tag, 1)
                text = head + text
    return text.strip()


# ---------------------------------------------------------------------------
# literal word-by-word "translation" (dictionary glossing, no model)

CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'}
LATIN_TO_CYRILLIC_DIGRAPHS = {
    'ch': 'ч', 'sh': 'ш', 'sch': 'щ', 'shch': 'щ', 'zh': 'ж', 'kh': 'х',
    'ts': 'ц', 'ck': 'к', 'th': 'т', 'ph': 'ф', 'oo': 'у', 'ee': 'и',
    'ya': 'я', 'yu': 'ю', 'yo': 'ё', 'ja': 'я', 'ju': 'ю', 'w': 'в'}
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
    'a': 'า', 'e': 'เอ', 'i': 'อิ', 'o': 'โอ', 'u': 'อุ', 'q': '',
    'A': 'า', 'E': 'เอ', 'I': 'อิ', 'O': 'โอ', 'U': 'อุ'}


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


class LiteralDictionaryEngine:
    """Word-for-word dictionary glossing, no model at all.

    Per token, in order: dictionary lookup of the surface form, the annotated
    lemma and pymorphy3 normal forms (spaCy misses Russian case forms like
    вам -> вы); among an entry's target translations prefer the first one
    that is not just a transliteration of the source (мужик -> man, not
    muzhik); a reverse index over the dictionary plugs single-word data gaps
    (the English edition lacks ru translations for "I", the Russian edition's
    "я" entry translates back to "I"); algorithmic transliteration is the
    last resort. Punctuation passes through; output is space-joined
    source-order word glosses (also for Thai, where spaces mark gloss
    boundaries).
    """

    def __init__(self, key):
        self.key = key
        self.pairs = None

    def translate(self, text, source_code, target_locale, words):
        start = time.perf_counter()
        dictionary = _shared_dictionary()
        reverse = _shared_reverse_index()
        glosses = []
        for word in words:
            if word['pos'] == 'PUNCT':
                glosses.append(word['text'])
                continue
            naive = transliterate(word['text'],
                                  target_locale).strip().casefold()
            translation = None
            candidates = dict.fromkeys([word['text'], word['lemma'],
                                        *_lemma_candidates(word['text'])])
            for candidate in candidates:
                result = dictionary.lookup(source_code, target_locale,
                                           candidate, lemma=candidate,
                                           pos=word['pos'])
                for entry in result['entries']:
                    options = [term for term in entry['translations']
                               if term.strip().casefold() != naive]
                    if options:
                        translation = options[0]
                        break
                if translation is not None:
                    break
            if translation is None:
                translation = (reverse.lookup(source_code, target_locale,
                                              word['text'])
                               or transliterate(word['text'], target_locale))
            glosses.append(translation)
        return ' '.join(glosses), (time.perf_counter() - start) * 1000


_morph_analyzer = None


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
            _morph_analyzer = False
    if not _morph_analyzer:
        return []
    return list(dict.fromkeys(parse.normal_form
                              for parse in _morph_analyzer.parse(word)[:4]))


TARGET_EDITION = {'en': 'eng', 'de': 'deu', 'ru': 'rus', 'th': None}


class ReverseDictionaryIndex:
    """(edition, locale, translation term) -> headword, built once from the
    kaikki database. For a missed source word it finds the target-language
    headword whose translations contain that word."""

    def __init__(self, path):
        self._db = sqlite3.connect(str(path), check_same_thread=False)

    def lookup(self, source_code, target_locale, term):
        edition = TARGET_EDITION[target_locale]
        if edition is None:
            return None
        row = self._db.execute(
            'SELECT word FROM reverse WHERE edition=? AND locale=? AND '
            'term=? ORDER BY word LIMIT 1',
            (edition, target_locale, term.strip().casefold())).fetchone()
        return row[0] if row else None


_reverse_index_instance = None


def _shared_reverse_index():
    global _reverse_index_instance
    if _reverse_index_instance is None:
        path = RESULTS_DIR / 'reverse.sqlite'
        if not path.exists():
            _build_reverse_index(path)
        _reverse_index_instance = ReverseDictionaryIndex(path)
    return _reverse_index_instance


def _build_reverse_index(path):
    logger.info('building reverse translation index (one-time) ...')
    source = sqlite3.connect(f'file:{DICTIONARY_DB}?mode=ro', uri=True)
    target = sqlite3.connect(str(path))
    target.execute('CREATE TABLE reverse (edition TEXT, locale TEXT, '
                   'term TEXT, word TEXT, PRIMARY KEY (edition, locale, '
                   'term, word))')
    batch = []
    for source_code, word, translations_json in source.execute(
            'SELECT source, word, translations FROM entries'):
        for locale, terms in json.loads(translations_json).items():
            for term in terms:
                batch.append((source_code, locale,
                              term.strip().casefold(), word))
        if len(batch) >= 50_000:
            target.executemany('INSERT OR IGNORE INTO reverse VALUES '
                               '(?, ?, ?, ?)', batch)
            batch.clear()
    if batch:
        target.executemany('INSERT OR IGNORE INTO reverse VALUES '
                           '(?, ?, ?, ?)', batch)
    target.commit()
    target.close()
    source.close()
    logger.info('reverse index ready: %s', path)


class LlamaServerEngine:
    """GGUF model served by a local llama-server subprocess (one per run)."""

    def __init__(self, key, gguf_path, port, mode='chat', system=None,
                 user_template=None, raw_template=None, sampling=None,
                 stop_sequences=None, server_args=None, glossary=False,
                 pairs=None):
        self.key = key
        self.gguf_path = gguf_path
        self.port = port
        self.mode = mode
        self.system = system
        self.user_template = user_template
        self.raw_template = raw_template
        self.sampling = sampling or {'temperature': 0.0}
        self.stop_sequences = stop_sequences
        self.server_args = server_args or []
        self.glossary = glossary
        self.pairs = pairs
        self._process = None

    def _base_url(self):
        return f'http://127.0.0.1:{self.port}'

    def start(self):
        gguf = Path(self.gguf_path)
        if not gguf.exists():
            raise FileNotFoundError(f'{self.key}: missing {gguf}')
        command = [str(LLAMA_BIN), '-m', str(gguf), '--port', str(self.port),
                   '-t', '8', '-c', '2048', '-ngl', '0', '--jinja', '--no-warmup',
                   *self.server_args]
        logger.info('%s: starting llama-server (port %d)', self.key, self.port)
        log_file = open(RESULTS_DIR / f'server-{self.key}.log', 'w')
        self._process = subprocess.Popen(command, stdout=log_file,
                                         stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise RuntimeError(f'{self.key}: llama-server exited, '
                                   f'see tmp/bench/results/server-{self.key}.log')
            try:
                if _get_ok(f'{self._base_url()}/health', timeout=2):
                    return
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(1)
        self.stop()
        raise RuntimeError(f'{self.key}: llama-server did not become healthy')

    def stop(self):
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        logger.info('%s: llama-server stopped', self.key)

    def _prompt(self, text, source_code, target_locale, words):
        """Chat instruction or raw completion prompt for one phrase."""
        if self.glossary:
            glossary = build_glossary(_shared_dictionary(), source_code,
                                      target_locale, words)
        else:
            glossary = []
        source_name = LANG_NAMES[SOURCE_LOCALE[source_code]]
        target_name = LANG_NAMES[target_locale]
        if self.mode == 'chat':
            if self.user_template:
                return self.user_template.format(source=source_name,
                                                 target=target_name, text=text)
            return f'Translate subtitle into {target_name}: {text}'
        context = {'source_tag': LANG_TAGS[SOURCE_LOCALE[source_code]],
                   'target_tag': LANG_TAGS[target_locale],
                   'source': source_name, 'target': target_name, 'text': text}
        if glossary:
            context['text'] = f"{context['text']} (glossary: {', '.join(glossary)})"
        return self.raw_template.format(**context)

    def translate(self, text, source_code, target_locale, words):
        instruction = self._prompt(text, source_code, target_locale, words)
        start = time.perf_counter()
        if self.mode == 'chat':
            messages = []
            if self.system:
                messages.append({'role': 'system', 'content': self.system})
            messages.append({'role': 'user', 'content': instruction})
            payload = {'messages': messages, 'max_tokens': 256,
                       'cache_prompt': True, **self.sampling}
            result = _post_json(f'{self._base_url()}/v1/chat/completions',
                                payload, timeout=300)
            output = result['choices'][0]['message']['content']
        else:
            payload = {'prompt': instruction, 'n_predict': 256,
                       'cache_prompt': True, **self.sampling}
            if self.stop_sequences:
                payload['stop'] = self.stop_sequences
            result = _post_json(f'{self._base_url()}/completion',
                                payload, timeout=300)
            output = result['content']
        latency = (time.perf_counter() - start) * 1000
        return _strip_reasoning(output.strip()), latency


class RemoteOpenAIEngine:
    """OpenAI-compatible endpoint (the llama server on the LAN box)."""

    def __init__(self, key, base_url, api_key, model, glossary=False,
                 extra_body=None, pairs=None):
        self.key = key
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.glossary = glossary
        self.extra_body = extra_body or {}
        self.pairs = pairs
        self._warm = False

    def translate(self, text, source_code, target_locale, words):
        instruction = (f'Translate subtitle into {LANG_NAMES[target_locale]}: '
                       f'{text}')
        payload = {'model': self.model,
                   'messages': [{'role': 'user', 'content': instruction}],
                   'max_tokens': 512, 'temperature': 0.0, **self.extra_body}
        start = time.perf_counter()
        result = _post_json(f'{self.base_url}/chat/completions', payload,
                            timeout=300,
                            headers={'Authorization': f'Bearer {self.api_key}'})
        latency = (time.perf_counter() - start) * 1000
        if not self._warm:
            self._warm = True
            logger.info('%s: reachable, first call %.0f ms', self.key, latency)
        return _strip_reasoning(
            result['choices'][0]['message']['content'].strip()), latency


_shared_dictionary_instance = None


def _shared_dictionary():
    global _shared_dictionary_instance
    if _shared_dictionary_instance is None:
        _shared_dictionary_instance = KaikkiDictionary(str(DICTIONARY_DB))
    return _shared_dictionary_instance


# Sampling settings and prompt formats follow the model cards verbatim;
# dedicated translation models use their own instruction styles instead of
# the generic subtitle prompt. -gloss engines augment the generic prompt
# with the Wiktionary/lemma term list (the POE-metadata reuse mode).
HUNYUAN_SAMPLING = {'temperature': 0.7, 'top_p': 0.6, 'top_k': 20,
                    'repeat_penalty': 1.05}
HUNYUAN_TEMPLATE = ('Translate the following segment into {target}, '
                    'without additional explanation.\n\n{text}')
GEMMAX_TEMPLATE = ('Translate this from {source} to {target}:\n'
                   '{source}: {text}\n{target}:')
TOWER_PAIRS = [(source, target)
               for source in ('eng', 'deu', 'rus')
               for target in pairs_for(source)
               if target != 'th']  # Tower-Plus has no Thai


def build_engines(env):
    models = MODELS_DIR
    engines = {
        'literal': LiteralDictionaryEngine('literal'),
        'nllb600': CT2Engine('nllb600', 'nllb-600m-ct2', 'nllb'),
        'madlad3b': CT2Engine('madlad3b', 'madlad400-3b-mt-ct2-int8', 'madlad'),
        'qwen36-35b': RemoteOpenAIEngine(
            'qwen36-35b', env['LLAMA_TRANSLATE_BASE_URL'],
            env['LLAMA_TRANSLATE_API_KEY'], env['LLAMA_TRANSLATE_MODEL'],
            extra_body={'chat_template_kwargs': {'enable_thinking': False}}),
        'qwen36-35b-gloss': RemoteOpenAIEngine(
            'qwen36-35b-gloss', env['LLAMA_TRANSLATE_BASE_URL'],
            env['LLAMA_TRANSLATE_API_KEY'], env['LLAMA_TRANSLATE_MODEL'],
            glossary=True,
            extra_body={'chat_template_kwargs': {'enable_thinking': False}}),
        'qwen3-4b': LlamaServerEngine(
            'qwen3-4b', models / 'qwen3-4b-instruct-2507-q4km'
            / 'Qwen3-4B-Instruct-2507-Q4_K_M.gguf', 8801),
        'hymt15-18b': LlamaServerEngine(
            'hymt15-18b', models / 'hymt15-1.8b-q4km'
            / 'HY-MT1.5-1.8B-Q4_K_M.gguf', 8802,
            user_template=HUNYUAN_TEMPLATE, sampling=HUNYUAN_SAMPLING),
        'hymt15-7b': LlamaServerEngine(
            'hymt15-7b', models / 'hymt15-7b-q4km'
            / 'HY-MT1.5-7B-Q4_K_M.gguf', 8810,
            user_template=HUNYUAN_TEMPLATE, sampling=HUNYUAN_SAMPLING),
        'hunyuan-mt-7b': LlamaServerEngine(
            'hunyuan-mt-7b', models / 'hunyuan-mt-7b-q4km'
            / 'Hunyuan-MT-7B.Q4_K_M.gguf', 8803,
            user_template=HUNYUAN_TEMPLATE, sampling=HUNYUAN_SAMPLING),
        'gemmax2-2b': LlamaServerEngine(
            'gemmax2-2b', models / 'gemmax2-28-2b-q4km'
            / 'GemmaX2-28-2B-v0.1.i1-Q4_K_M.gguf', 8804, mode='raw',
            raw_template=GEMMAX_TEMPLATE, stop_sequences=['\n']),
        'milmmt-12b': LlamaServerEngine(
            'milmmt-12b', models / 'milmmt-46-12b-q4km'
            / 'MiLMMT-46-12B-v1.0.Q4_K_M.gguf', 8805, mode='raw',
            raw_template=GEMMAX_TEMPLATE, stop_sequences=['\n']),
        'tower-plus-9b': LlamaServerEngine(
            'tower-plus-9b', models / 'tower-plus-9b-q4km'
            / 'Tower-Plus-9B.Q4_K_M.gguf', 8806,
            user_template=('Translate the following {source} source text to '
                           '{target}:\n{source}: {text}\n{target}: '),
            pairs=TOWER_PAIRS),
        'seed-x-7b': LlamaServerEngine(
            'seed-x-7b', models / 'seed-x-7b-q4km'
            / 'ByteDance-Seed.Seed-X-Instruct-7B.Q4_K_M.gguf', 8807,
            mode='raw',
            raw_template=('Translate the following {source} sentence into '
                          '{target}:\n{text} <{target_tag}>')),
        'gemma3-4b': LlamaServerEngine(
            'gemma3-4b', models / 'gemma3-4b-it-q4km'
            / 'gemma-3-4b-it.Q4_K_M.gguf', 8808, system=SUBTITLE_SYSTEM),
        'typhoon-15-4b': LlamaServerEngine(
            'typhoon-15-4b', models / 'typhoon-translate15-4b-q4km'
            / 'typhoon-translate1.5-4b-q4_k_m.gguf', 8809,
            user_template=('Translate the following {source} text into '
                           '{target}, strictly following the rules below and '
                           'return only the translated text.\n'
                           '1. Preserve the tone, register and colloquial '
                           'style of a movie subtitle.\n'
                           'Source Text:\n\n{text}'),
            sampling={'temperature': 0.2}, pairs=[('eng', 'th')]),
    }
    return engines


# ---------------------------------------------------------------------------
# runner


def results_path(engine_key, code, target):
    directory = RESULTS_DIR / engine_key
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f'{code}-{target}.json'


def _cpu_ticks():
    with open('/proc/stat') as stat_file:
        fields = stat_file.readline().split()
    ticks = [int(value) for value in fields[1:]]
    idle = ticks[3] + (ticks[4] if len(ticks) > 4 else 0)  # idle + iowait
    return idle, sum(ticks)


def wait_for_quiet_machine(quiet_seconds=10, threshold=40.0):
    """Hold until the CPU has been mostly idle for ``quiet_seconds``: latency
    must not be measured while an external process holds the machine."""
    quiet = 0
    while quiet < quiet_seconds:
        before = _cpu_ticks()
        time.sleep(1)
        after = _cpu_ticks()
        busy = 100 * (1 - (after[0] - before[0]) / max(1, after[1] - before[1]))
        if busy < threshold:
            quiet += 1
        else:
            quiet = 0
            logger.info('waiting for quiet machine: busy=%.0f%%', busy)


PHRASE_BUDGET_MS = 3000
PROBE_PHRASES = 5


def run_engine(engine, phrase_sets, only=None, probe=True):
    """Translate every missing (file, pair, phrase); cached results skipped.

    After PROBE_PHRASES fresh translations the median latency is checked
    against the PHRASE_BUDGET_MS: an engine that cannot translate a phrase
    within budget is marked SKIPPED and dropped - the interactive app cannot
    afford it on this machine. ``probe=False`` measures the full matrix
    regardless (used for re-shot runs where the budget is applied to the
    final medians instead).
    """
    started = False
    probe_ms = []
    warmup_done = False
    try:
        for code, phrase_set in phrase_sets.items():
            for target in pairs_for(code):
                if only and (code, target) != only:
                    continue
                if engine.pairs is not None and (code, target) not in engine.pairs:
                    continue
                if isinstance(engine, CT2Engine) and not engine.model_dir.exists():
                    logger.warning('%s: model missing, skipping (%s)',
                                   engine.key, engine.model_dir)
                    return
                if isinstance(engine, LlamaServerEngine) and not started:
                    engine.start()
                    started = True
                out_path = results_path(engine.key, code, target)
                cached = json.loads(out_path.read_text()) if out_path.exists() else {}
                phrases = phrase_set['phrases']
                pending = [p for p in phrases if p['text'] not in cached]
                if not pending:
                    continue
                logger.info('%s: %s->%s, %d/%d phrases to go', engine.key,
                            code, target, len(pending), len(phrases))
                for index, phrase in enumerate(phrases):
                    if phrase['text'] in cached:
                        continue
                    words = phrase['words']
                    try:
                        translation, latency = engine.translate(
                            phrase['text'], code, target, words)
                    except Exception as error:
                        logger.error('%s: phrase failed: %s', engine.key, error)
                        translation, latency = f'<ERROR: {error}>', 0.0
                    cached[phrase['text']] = {'target': translation,
                                              'ms': round(latency, 1),
                                              'at': time.time()}
                    if not warmup_done:
                        # cold start (model load, graph allocation) is not
                        # the engine's steady state - translate one phrase
                        # unmeasured before the elimination probe
                        warmup_done = True
                        logger.info('%s: warmup done in %.0f ms (unmeasured)',
                                    engine.key, latency)
                        continue
                    probe_ms.append(latency)
                    if probe and len(probe_ms) >= PROBE_PHRASES:
                        probe_median = statistics.median(probe_ms)
                        if probe_median > PHRASE_BUDGET_MS:
                            logger.warning(
                                '%s: SKIPPED - median %.0f ms/phrase over '
                                'the %.0f ms budget', engine.key, probe_median,
                                PHRASE_BUDGET_MS)
                            (RESULTS_DIR / engine.key
                             / 'SKIPPED').write_text(
                                f'median {probe_median:.0f} ms/phrase over '
                                f'the first {PROBE_PHRASES} phrases exceeds '
                                f'the {PHRASE_BUDGET_MS:.0f} ms budget\n')
                            return
                    out_path.write_text(json.dumps(
                        cached, ensure_ascii=False, indent=1))
                    logger.info('%s: %d/%d done (%.0f ms)', engine.key,
                                index + 1, len(phrases), latency)
    finally:
        if started:
            engine.stop()


# ---------------------------------------------------------------------------
# report


def _cell(text):
    return ' '.join(str(text).split()).replace('|', '\\|')


def render_report():
    """Side-by-side markdown/HTML comparison + latency table from the cache."""
    phrase_sets = load_phrase_sets()
    engines = sorted({directory.name for directory in RESULTS_DIR.iterdir()
                      if directory.is_dir()})
    skipped = {}
    for directory in RESULTS_DIR.iterdir():
        marker = directory / 'SKIPPED' if directory.is_dir() else None
        if marker is not None and marker.exists():
            skipped[directory.name] = marker.read_text().strip()
    md = ['# Offline translation bake-off - Big Lebowski samples',
          '',
          'Phrases: last 30 cues per file through the real analyzer pipeline. '
          'Latency is per-phrase wall time in milliseconds. The literal '
          'column is word-by-word dictionary glossing (surface form first, '
          'then lemma, POS-disambiguated among translations, transliteration '
          'fallback) - no model, kept as a pedagogical view.',
          '']
    if skipped:
        md += ['Engines skipped by the 3 s/phrase budget:']
        md += [f'- {name}: {reason}' for name, reason in skipped.items()]
        md += ['']
    html = ['<!doctype html><html><head><meta charset="utf-8">',
            '<title>Translation bake-off</title>',
            '<style>body{font-family:sans-serif;margin:2rem}'
            'table{border-collapse:collapse;margin:1rem 0;width:100%}'
            'td,th{border:1px solid #ccc;padding:.35rem .5rem;'
            'text-align:left;vertical-align:top}'
            'th{background:#eee}td.src{color:#666}</style></head><body>']
    if skipped:
        html.append('<h2>Skipped engines</h2><ul>'
                    + ''.join(f'<li><b>{name}</b>: {reason}</li>'
                              for name, reason in skipped.items())
                    + '</ul>')
    latency_rows = []
    for code, phrase_set in phrase_sets.items():
        for target in pairs_for(code):
            available = [key for key in engines
                         if results_path(key, code, target).exists()]
            if not available:
                continue
            header = (f'## {code} -> {target} '
                      f'({LANG_NAMES[SOURCE_LOCALE[code]]} to '
                      f'{LANG_NAMES[target]})')
            md += [header, '']
            html.append(f'<h2>{header[3:]}</h2>')
            columns = ['source'] + available
            md.append('| ' + ' | '.join(columns) + ' |')
            md.append('|' + '|'.join(['---'] * len(columns)) + '|')
            html.append('<table><tr>'
                        + ''.join(f'<th>{col}</th>' for col in columns)
                        + '</tr>')
            latencies = {key: [] for key in available}
            for phrase in phrase_set['phrases']:
                row = [_cell(phrase['text'])]
                html_row = [f'<td class="src">{phrase["text"]}</td>']
                for key in available:
                    cached = json.loads(
                        results_path(key, code, target).read_text())
                    entry = cached.get(phrase['text'])
                    if entry is None:
                        row.append('')
                        html_row.append('<td></td>')
                        continue
                    latencies[key].append(entry['ms'])
                    row.append(_cell(entry['target']))
                    html_row.append(f'<td>{entry["target"]}</td>')
                md.append('| ' + ' | '.join(row) + ' |')
                html.append('<tr>' + ''.join(html_row) + '</tr>')
            html.append('</table>')
            md.append('')
            latency_line = ' | '.join(
                f'{key}: {statistics.mean(values) / 1000:.1f}s/phrase'
                if values else f'{key}: -'
                for key, values in latencies.items())
            md.append(f'Latency: {latency_line}')
            md.append('')
            latency_rows.append((code, target,
                                 {key: statistics.mean(values) / 1000
                                  for key, values in latencies.items()
                                  if values}))
    md += ['## Latency summary (s/phrase average)', '',
           '| pair | ' + ' | '.join(engines) + ' |',
           '|' + '|'.join(['---'] * (len(engines) + 1)) + '|']
    html.append('<h2>Latency summary (s/phrase average)</h2><table><tr><th>pair</th>'
                + ''.join(f'<th>{key}</th>' for key in engines) + '</tr>')
    for code, target, averages in latency_rows:
        cells = [f'{averages.get(key, float("nan")):.1f}' if key in averages
                 else '' for key in engines]
        md.append(f'| {code}->{target} | ' + ' | '.join(cells) + ' |')
        html.append('<tr><td>' + f'{code}-&gt;{target}' + '</td>'
                    + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr>')
    html.append('</table></body></html>')
    md_path = RESULTS_DIR / 'report.md'
    md_path.write_text('\n'.join(md) + '\n')
    html_path = RESULTS_DIR / 'report.html'
    html_path.write_text('\n'.join(html))
    logger.info('Wrote %s and %s', md_path, html_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract', action='store_true',
                        help='build tmp/bench/results/phrases.json and exit')
    parser.add_argument('--engine', action='append',
                        help='engine key to run (repeatable)')
    parser.add_argument('--all', action='store_true', help='run every engine')
    parser.add_argument('--list', action='store_true',
                        help='list engine keys and exit')
    parser.add_argument('--pair', help='restrict to SOURCE-TARGET, e.g. eng-th')
    parser.add_argument('--no-probe', action='store_true',
                        help='measure the full matrix without the 3 s '
                             'elimination probe')
    parser.add_argument('--report', action='store_true',
                        help='render the side-by-side report from cache')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')

    if args.extract:
        extract_phrase_sets()
        return
    if args.list:
        for key in build_engines(load_env()):
            print(key)
        return
    if args.report:
        render_report()
        return

    if not (RESULTS_DIR / 'phrases.json').exists():
        parser.error('no phrases.json - run --extract first')
    phrase_sets = load_phrase_sets()
    engines = build_engines(load_env())
    if args.all:
        selected = list(engines)
    elif args.engine:
        selected = []
        for key in args.engine:
            if key not in engines:
                parser.error(f'unknown engine {key} (see --list)')
            selected.append(key)
    else:
        parser.error('nothing to do: use --extract, --engine, --all or --report')

    only = None
    if args.pair:
        source, target = args.pair.split('-')
        only = (source, target)

    for key in selected:
        logger.info('=== engine %s ===', key)
        if isinstance(engines[key], (LlamaServerEngine, CT2Engine)):
            wait_for_quiet_machine()
        run_engine(engines[key], phrase_sets, only=only,
                   probe=not args.no_probe)
    logger.info('done')


if __name__ == '__main__':
    main()
