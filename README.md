Learning languages by watching movies without translation.
======

This app was originally written as a helper tool to study English.
I think it is more productive to glance at the list of words used in the movie beforehand
and look at the translation of unfamiliar ones, instead of stopping in the middle to look up
some word. App provides a list of unique words with they ubiquity and the context in a phrase.
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

Icons were taken from [KDE/breeze-icons](https://github.com/KDE/breeze-icons)

USAGE
-----
Simply enter movie name or some TV series identifier, like `mash s11e06`. Or you could select
a local file with subtitles in SRT format.
Supported subtitle languages: English (`eng`), German (`deu`), Russian (`rus`) - select the
language in the UI before loading, or pass `--language` to `cli.py`.
Words are arranged by they frequency.

Selecting a word shows its context phrase annotated with pedagogical grammar symbols (the
classical Montessori shapes): every word carries its part-of-speech symbol, color and
underline style. Hover (or arrow-key to) any word for a lemma tooltip; hover the part-of-speech
chips for plain-language explanations. Articles are told apart from other determiners
per language (`core.languages`).
Interface languages: German (`de`), English (`en`), Russian (`ru`). The desktop app
follows the system locale and can be switched any time via the `Language · Язык · Sprache`
menu (the choice is remembered). Pass `--ui-language {de,en,ru}` to `cli.py` to override
the terminal interface language.

ARCHITECTURE
------------
All application logic is UI-agnostic and lives in the `core/` package, which must never
import a UI framework (`PyQt6` or any other). Frontends live on their own:

* `main.py` + `ui/qt/` - PyQt6 desktop frontend (the graphical application);
* `cli.py` - terminal frontend, same analysis pipeline without any GUI;
* `ui/i18n.py` - gettext-based localization adapter shared by every frontend;
* `locales/` - the UI catalogs (ISO-639-1 `de`/`en`/`ru`), keyed by stable message
  codes; `en` is the reference locale and every locale ships a complete catalog;
* `core/` - languages registry (neutral ISO-like codes `eng`/`deu`/`rus`), subtitle
  analyzer, OpenSubtitles.org client, translation helpers and `AppController`
  orchestrating it all. User-facing events are emitted as structured messages
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

    python3 -m unittest discover tests

(the catalog tests need `msgfmt` from the gettext tools; Qt tests run offscreen).

REQUIREMENTS
-------------
App requires **python>=3.8**, **PyQt6**, **PyQt6-WebEngine**, **chardet**, **srt** and **spacy**
(with English, German and Russian language models).

INSTALLATION
------------
### On Linux:
* Install Python 3.x and PIP via your distribution package manager.
* Clone or download this repository. 
* Try to install requirements also with package manager. And only if some
requirements are still missing - install them with PIP:  
**pip3 install --user -r subtitle_lang_learning/requirements.txt**
* Run the GUI application: `python3 main.py`  
Or analyze subtitles in the terminal: `python3 cli.py <SRT-file-or-title> --language deu`

### On Windows:
* Install x86-64 Python 3.x: From [https://www.python.org/downloads/windows/]  
select "Download Windows x86-64 executable installer".  
When installing, check "Add Python to PATH";
* Download this program from this page by clicking on the "Clone or download" button
and selecting "Download ZIP". Then unpack the archive.
* Install requirements with PIP, E. G. Open a command prompt and execute:  
**pip3 install --user -r Downloads/subtitle_lang_learning-master/requirements.txt**
* Run the program from the command prompt: `python main.py`

### On macOS 10.9 and later
* Download and install the latest **macOS 64-bit universal2 installer** from the official website
[https://www.python.org/downloads/macos/] 
* Check that you have Git installed [https://github.com/git-guides/install-git/] 
* Open the command prompt "terminal" and execute `git clone git@github.com:plartemyev/subtitle_lang_learning.git`
* Then execute `pip3 install --user -r subtitle_lang_learning/requirements.txt`
* And run the program by executing `python3 main.py`


TODO
----
* [ ] Embed some local dictionary.
* [x] Use lemmas to eliminate redundant word forms (done with spaCy, for English, German and Russian).
* [ ] Add ability to save already remembered words to exclude it from further searches.
* [ ] Embed video player, to be able to load video files with subtitles and jump to
the moment when a phrase is being spoken at the click on selected word.
* [x] Localization (desktop Qt + CLI; catalog converters for web/Android pending).
* [ ] Package for Android.
* [ ] Package for Windows.
* [ ] Package for macOS.

CONTRIBUTING
------------
Here's how you can help : 
* You can clone the git repository and start hacking with the code. Pull requests are most welcome

[app_screenshot]: screenshot.jpg "Usage illustration"
