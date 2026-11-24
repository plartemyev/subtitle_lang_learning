Learning languages by watching movies without translation.
======

This app was originally written as a helper tool to study English.
I think it is more productive to glance at the list of words used in the movie beforehand
and look at the translation of unfamiliar ones, instead of stopping in the middle to look up
some word. App provides a list of unique words with their ubiquity and the context in a phrase.
![app_screenshot]

LICENSE
-------
This is free software, distributed under the GPL v.3. If you want to discuss
a release under another license, please open an issue on GitHub

NOTES
-----
As usual with this kind of software :
This software is provided "AS-IS", without any guarantees. It should not do
any harm to your system, but if it does, the author, GitHub, etc... cannot
be held responsible. Use at your own risk. You have been warned.

Icons were taken from [KDE/breeze-icons](https://github.com/KDE/breeze-icons).
The application icon (`ui/qt/icon.svg`) is Breeze `application-x-srt`
(LGPL-3.0-or-later, `COPYING-ICONS` in that repository).

USAGE
-----
Simply enter movie name or some TV series identifier, like `mash s11e06`. Or you could select
a local file with subtitles in SRT format.
Supported subtitle languages: English (`eng`), German (`deu`), Russian (`rus`) - select the
language in the UI before loading, or pass `--language` to `cli.py`.
Words are arranged by their frequency.
Optionally, the selected word or its context phrase is looked up in the embedded
Google Translate view; the provider's interface language and the translation
target both follow the active interface language.

Selecting a word shows its context phrase annotated with pedagogical grammar symbols (the
classical Montessori shapes): every word carries its part-of-speech symbol, color and
underline style. Hover (or arrow-key to) any word for a lemma tooltip; hover the part-of-speech
chips for plain-language explanations. Clicking the context phrase copies its plain text
(subtitle line breaks collapsed) to the clipboard. Articles are told apart from other determiners
per language (`core.languages`). The tooltip carries the bold lemma, the token's
morphology, bold Wiktionary translations into the interface language plus a sense gloss;
contraction tokens spell their full form out next to the shorthand (`'s (is)`,
`'d (had)`, `n't (not)`), derived from the spaCy lemma + morphology of the very token,
with no per-contraction word lists (`core.full_forms`). The colors adapt to the
system theme (readability verified against the default light and dark palettes).
The `Symbols` menu chooses whose Montessori tradition paints the icons -
the interface language's (the student's) or the subtitle language's. The systems differ only
where the traditions genuinely differ (interjection: diamond vs exclamation keyhole,
pronoun: tripartite vs plain pyramid); Thai (`th`) Montessori uses the imported international
materials and renders like the reference set.
Interface languages: German (`de`), English (`en`), Russian (`ru`), Thai (`th`). The desktop app
follows the system locale and can be switched any time via the `Language`
menu (the choice is remembered). Pass `--ui-language {de,en,ru,th}` to `cli.py` to override
the terminal interface language.

WEB UI
------
The same analysis runs in the browser as a single-page app served by a FastAPI
backend (`web/`); the desktop presentation of the grammar symbols is ported
one-to-one. The whole stack ships as one container:

    docker compose up --build --detach
    # then open http://127.0.0.1:8000

The SPA shell and its static assets are served with `Cache-Control:
max-age=600` - repeat visits cost zero round trips (friendly to lossy
high-latency links), and a deploy reaches everyone within ten minutes
without a hard refresh. API answers are `no-store`.

Without Docker: `poetry install --with web` and run
`poetry run python -m uvicorn web.app:app --host 0.0.0.0 --port 8000`.
The page is plain HTML/JS/CSS from our own origin, no third-party scripts.
The API consumed by the page (handy for scripting):

* `GET /api/health`, `GET /api/languages`, `GET /api/i18n/<locale>`;
* `POST /api/analyze/file` - multipart `file` + `language` form fields;
* `POST /api/analyze/online` - JSON body `{"query": ..., "language": ...}`,
  returns `{analysis, messages}` where `messages` carry the localizable
  event codes;
* `POST /api/translate/phrase` - JSON body `{"text": ..., "language": ...,
  "target": ...}`, returns `{source_text, translation, words, cached}`; the
  current engines carry no word alignment (`words` is empty, per-word
  tooltips are dictionary-based) and `cached` marks sqlite LRU cache hits;
* `POST /api/translate/literal` - the same JSON body, returns `{literal}`,
  the instant word-by-word dictionary gloss of the phrase; 503
  `translation_unavailable` without the dictionary;
* `GET /api/dictionary/lookup?language=&target=&word=&lemma=&pos=` -
  Wiktionary glosses and translations for one word. The per-word tooltip
  translation is dictionary-first: surface-form entries are served only
  when they carry translations into the target locale, otherwise the
  lemma's entries win (inflected forms usually have their own Wiktionary
  row holding just a relational gloss).

OFFLINE TRANSLATION
-------------------
Phrase translation runs through a fallback chain of model engines. The
primary one is a remote OpenAI-compatible server - Ollama or llama.cpp
serving a large multilingual model (the reference deployment:
Qwen3.6-35B) - configured with `OLLAMA_BASE_URL`, `OLLAMA_MODEL` and
`OLLAMA_API_KEY` read from the gitignored `.env` (the Qt desktop frontend
loads that file itself at startup, compose reads it for the web stack);
thinking mode is explicitly disabled and the collapsed prompt protocol
follows the benchmark in docs/offline-translation-research.md. The
offline fallback is Tencent HY-MT1.5-1.8B (Q4_K_M GGUF, ~1.1 GB) under a
local llama.cpp subprocess, prepared once by `tools/prepare_hymt15.py`.
Switching is probe-driven: the remote's cached state is checked first,
then a 0.5 s connect probe and a 0.5 s slot-availability probe run - a busy
server is skipped for 10 s, an unreachable one for 10 minutes, and any
successful call clears the state. Between the cached states the chain
falls to the local model, and to 503 `translation_unavailable` (or the
same localized line in the desktop view) when nothing answers; per-word
tooltips are dictionary-based and unaffected. Phrase translation calls
are cached in an sqlite LRU cache (~2 GiB budget, counter based).

The web UI and the Qt desktop UI both ship this local-translation view;
the desktop one is built from native widgets only (no web engine, no
HTML/CSS) and translation is enabled out of the box with the local
engines in whole-phrase mode. Both frontends debounce phrase translation
at 300 ms and render the instant word-by-word dictionary view (the
"literal" column of the benchmark) alongside: longest-match idiom sweep,
surface/lemma/POS dictionary picks, a reverse index and transliteration
fallback - see docs/offline-translation-research.md.

Everything lives outside the repository in the data directory (`data/`
by default, override with `SUBTITLE_LEARNING_DATA_DIR`):

    data/models/hymt15-1.8b-q4km/    local fallback model GGUF
    data/dictionary/kaikki.sqlite    Wiktionary glosses/translations lookup
    data/dictionary/reverse.sqlite   translation term -> headword index
    data/cache/translations.sqlite   phrase translation LRU cache

Prepare once (the dictionary build streams ~3.4 GB of Wiktionary dumps;
a llama.cpp binary on PATH is needed for the local fallback - the
distribution `llama-server` package or a llama.cpp release build):

    poetry install --with web
    poetry run python tools/build_dictionary.py
    poetry run python tools/prepare_hymt15.py

A HuggingFace token speeds the model download up: put `HF_TOKEN=...` into
the gitignored `.env` file next to the repository. The pieces degrade
gracefully: without the remote server and the local model
`/api/translate/phrase` answers 503 `translation_unavailable`, without
the dictionary `/api/dictionary/lookup` returns no entries and the
literal view stays hidden. The docker compose stack mounts `./data` into
the container, so one directory serves a local and a containerized
backend.

Attribution: dictionary data is extracted from Wiktionary via
wiktextract/kaikki.org (CC BY-SA 4.0); HY-MT1.5 weights carry the Tencent
HY Community License (open weights with restrictions - the repository
ships no weights, every user downloads their own copy).

Engine replacement research (Nov 2026): fifteen offline engines were
benchmarked against real subtitle phrases with a 3 s/phrase latency budget
and per-stage atop contamination audits - procedure, tools and results in
`docs/offline-translation-research.md`, harness in
`tools/benchmark_translation.py`.

ARCHITECTURE
------------
All application logic is UI-agnostic and lives in the `core/` package, which must never
import a UI framework (`PyQt6` or any other). Frontends live on their own:

* `main.py` + `ui/qt/` - PyQt6 desktop frontend (the graphical application), with the
  local-translation view rendered by native widgets and wired to the same engine
  chain, dictionary and translation cache as the web backend (`ui.qt.local_translation`);
* `cli.py` - terminal frontend, same analysis pipeline without any GUI;
* `web/` + `web/static/` - FastAPI backend and the browser single-page UI;
  analysis results are serialized to JSON (`web/serializers.py`), UI catalogs
  are served as JSON by `/api/i18n`, user-facing outcomes stay structured
  message codes localized in the browser;
* `ui/i18n.py` - gettext-based localization adapter shared by every frontend;
* `locales/` - the UI catalogs (ISO-639-1 `de`/`en`/`ru`/`th`), keyed by stable message
  codes; `en` is the reference locale and every locale ships a complete catalog;
* `core/` - languages registry (neutral ISO-like codes `eng`/`deu`/`rus`), subtitle
  analyzer, OpenSubtitles.org client, translation helpers (the Google Translate URL
  builder, the offline engine chain in `core/translation/`, the Wiktionary
  dictionary in `core/dictionary.py` - POS matching is UPOS-mapped with
  AUX→VERB/SCONJ→CCONJ siblings so auxiliary `do` never resolves through an
  unrelated noun row) and
  `AppController` orchestrating it all. User-facing events are emitted as structured messages
  (code + params) and rendered by the frontend, keeping the core free of display
  text - that is the groundwork for localization and additional UI targets.

LOCALIZATION
------------
Catalogs live in `locales/<lang>/LC_MESSAGES/messages.po`; msgids are frontend-neutral
message codes, plural pairs use gettext plurals. The compiled `.mo` binaries are
committed, so end users need no gettext toolchain. After editing a `.po` file,
recompile and commit both:

    tools/compile_locales.sh

Run the checks (catalog completeness, plural rules, Qt retranslation) with:

    poetry run python3 -m unittest discover tests

(the catalog tests need `msgfmt` from the gettext tools; Qt tests run offscreen).

GUI visual verification renders the real main window on Qt's offscreen
platform - no display server needed - under the default light palette and
the standard dark Fusion palette, and saves composited screenshots of every
screen (word list, details + phrase + local translation, a token tooltip,
both menus, source and translation tabs) into `tmp/screenshots/`:

    poetry run python tools/visual_check.py {light,dark} [--locale ru]

QWebEngineView is stubbed by the tool (it core-dumps offscreen), so the
online tab captures show an empty native pane; everything this repository
paints itself is fully rendered.

The web frontend has the counterpart `tools/web_check.py`: playwright
(system package) drives `/usr/bin/chromium` against a running backend,
uploads a sample, selects words, hovers a contraction token and reports the
translation view state plus any console errors - the SPA degrades silently
on API failures, so the error count is the signal:

    python3 tools/web_check.py --url http://127.0.0.1:8000

REQUIREMENTS
-------------
The Python environment is managed with **Poetry 2.x** (see `pyproject.toml`;
an in-project `.venv` is created automatically) and requires **python>=3.14**.
Install per use case: `poetry install` (CLI/core), `--with desktop` (Qt GUI),
`--with web` (web backend), `--with tools` (optional faster dictionary build).
SpaCy ships the English, German and Russian language models as pinned wheels.

SYSTEM DEPENDENCIES
-------------------
* **llama.cpp** (`llama-server`) - only for the local HY-MT1.5 fallback
  engine. Resolved from `PATH`, an explicit `LLAMA_SERVER_BIN`, or the
  release build placed in `data/bin/llama-cpp/` (any llama.cpp release
  tarball works: unpack it there). Not needed when only the remote engine
  is used.
* **gettext toolchain** (`msgfmt`) - developer-only, to recompile locale
  catalogs after editing `.po` files (`tools/compile_locales.sh`; the
  compiled `.mo` files are committed).
* **ripgrep/grep** and ~3.4 GB of network - only for the one-time
  dictionary build (`tools/build_dictionary.py` streams the kaikki.org
  dumps; downloads are cached under `tmp/dict-build/`).

EXTERNAL LLM WIRING
-------------------
The remote engine speaks the OpenAI chat-completions dialect of an
Ollama or llama.cpp server on the LAN. All wiring belongs in the
gitignored `.env` next to the repository (secrets never enter it):

    OLLAMA_BASE_URL    server endpoint, e.g. http://<host>:8011/v1
    OLLAMA_MODEL       model id/path as the server reports it
    OLLAMA_API_KEY     bearer token; omit when the server has none

Local fallback wiring (all optional, defaults in parentheses):

    LLAMA_LOCAL_MODEL  GGUF path (data/models/hymt15-1.8b-q4km/HY-MT1.5-...)
    LLAMA_LOCAL_PORT   llama-server port (8802)
    LLAMA_SERVER_BIN   server binary (PATH, then data/bin/llama-cpp/)

Also read from `.env`/environment: `HF_TOKEN` (faster model downloads),
`SUBTITLE_LEARNING_DATA_DIR` (data directory override) and
`SUBTITLE_LEARNING_CACHE_MAX_BYTES` (translation LRU budget). With no
remote wiring and no local model the phrase endpoint answers 503 and the
UI keeps the dictionary view; nothing requires an online service.

INSTALLATION
------------
### On Linux:
* Install Python 3.14+ and Poetry 2.x via your distribution package manager.
* Clone or download this repository.
* Install the environment for your frontend: `poetry install` (CLI),
  `poetry install --with desktop` (GUI) or `poetry install --with web` (web backend).
* Run the GUI application: `poetry run python main.py`
Or analyze subtitles in the terminal: `poetry run python cli.py <SRT-file-or-title> --language deu`

### On Windows:
* Install x86-64 Python 3.14+: From [https://www.python.org/downloads/windows/]
  select "Download Windows x86-64 executable installer".
  When installing, check "Add Python to PATH";
* Install Poetry: [https://python-poetry.org/docs/#installation]
* Download this program from this page by clicking on the "Clone or download" button
  and selecting "Download ZIP". Then unpack the archive.
* In a command prompt inside the unpacked directory run: `poetry install --with desktop`
* Run the program from the command prompt: `poetry run python main.py`

### On macOS 10.9 and later
* Download and install the latest **macOS 64-bit universal2 installer** from the official website
  [https://www.python.org/downloads/macos/]
* Check that you have Git installed [https://github.com/git-guides/install-git/]
* Open the command prompt "terminal" and execute `git clone git@github.com:plartemyev/subtitle_lang_learning.git`
* Change into the directory and run: `poetry install --with desktop`
* And run the program by executing `poetry run python3 main.py`


TODO
----
* [x] Embed a local dictionary (Wiktionary via kaikki.org; see OFFLINE TRANSLATION).
* [x] Use lemmas to eliminate redundant word forms (done with spaCy, for English, German and Russian).
* [ ] Add ability to save already remembered words to exclude it from further searches.
* [ ] Embed video player, to be able to load video files with subtitles and jump to
the moment when a phrase is being spoken at the click on selected word.
* [x] Localization (desktop Qt + CLI; the web frontend consumes the same catalogs
via `/api/i18n`, catalog converters for Android pending).
* [x] Web frontend served as a docker compose stack.
* [ ] Package for Android.
* [ ] Package for Windows.
* [ ] Package for macOS.

CONTRIBUTING
------------
Here's how you can help : 
* You can clone the git repository and start hacking with the code. Pull requests are most welcome

[app_screenshot]: screenshot.jpg "Usage illustration"
