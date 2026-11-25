#!/usr/bin/env python3
"""Browser verification of the web frontend via playwright-controlled chromium.

Desktop run: loads the SPA against a running backend, uploads a subtitle
sample, selects words, hovers a contraction token and reports the
translation view state plus any console/page errors - the frontend degrades
silently on API failures (catch -> empty payloads), so error counting is the
point, not just looks.

Mobile run (--mobile): the same sample on the phone profiles below, with
touch emulation and no mouse at all. A finger picks a word, opens its card,
expands a chip, copies the phrase, steps to the next word and unfolds the
word list from the bottom bar; console errors and failed checks both count.

Usage (backend must be up):
    poetry run python -m uvicorn web.app:app --port 8123   # or docker compose
    python3 tools/web_check.py --url http://127.0.0.1:8123
    python3 tools/web_check.py --url http://127.0.0.1:8123 --mobile
    python3 tools/web_check.py --url http://127.0.0.1:8123 --mobile --device 360x780,390x844

Exit status: 1 with console errors (desktop), the number of problems found
(mobile).

Needs the system playwright package (python3 -c 'import playwright') and
/usr/bin/chromium; screenshots land in tmp/screenshots/ (--out).
"""
import argparse
import glob
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

# Phone profiles: the ten most common mobile viewports worldwide (StatCounter,
# October 2026; two of them at both of their pixel ratios) and the two
# best-selling iPhone 17 sizes, which are not in that top ten yet.
# key, width, height, pixel ratio
MOBILE_PROFILES = (
    ('414x896@2', 414, 896, 2),      # iPhone XR / 11
    ('414x896@3', 414, 896, 3),      # iPhone XS Max / 11 Pro Max
    ('360x800@2', 360, 800, 2),      # HD+ panels (Galaxy A07)
    ('360x800@3', 360, 800, 3),      # FHD+ at 480 dpi
    ('384x832', 384, 832, 2.8125),   # Galaxy S23-S26
    ('390x844', 390, 844, 3),        # iPhone 12-16, 16e, 17e
    ('393x873', 393, 873, 2.75),     # Pixel 7-9
    ('360x780', 360, 780, 3),
    ('412x915', 412, 915, 2.625),    # Pixel 6
    ('385x854', 385, 854, 2.8),
    ('384x854', 384, 854, 2.8125),
    ('412x892', 412, 892, 3.5),      # Pixel 6-9 Pro
    ('402x874', 402, 874, 3),        # iPhone 17 / 17 Pro
    ('440x956', 440, 956, 3),        # iPhone 17 Pro Max
)

READY = "() => document.querySelectorAll('#subtitle-language option').length > 0"
TRANSLATED = ("() => { const t = document.querySelector('#phrase-translation-text');"
              " return t && t.textContent.trim() && !t.querySelector('.spinner'); }")

# Subtitles are loaded and nothing is picked: the list is the whole content,
# from under the header down to the bar, which sits on the screen's bottom edge.
LOADED_STATE = r'''() => {
  const box = (selector) => document.querySelector(selector).getBoundingClientRect();
  const panel = box('#list-panel'), dock = box('#dock');
  return { fills: Math.abs(panel.bottom - dock.top) < 1.5
           && Math.abs(dock.bottom - window.innerHeight) < 1.5 };
}'''

# A word is picked and its translation has arrived: the list is folded away,
# the bar sits on the bottom edge and the phrase with its translation fits
# between the header and the bar.
WORD_STATE = r'''() => {
  const box = (selector) => document.querySelector(selector).getBoundingClientRect();
  const details = document.querySelector('#details');
  return {
    barAtBottom: Math.abs(box('#dock').bottom - window.innerHeight) < 1.5,
    aboveBar: box('#phrase-translation').bottom <= box('#dock').top,
    listFolded: document.querySelector('#list-panel').getClientRects().length === 0,
    fits: details.scrollWidth <= details.clientWidth + 1,
  };
}'''

# The word card is open: it marks one token and covers none.
CARD_STATE = r'''() => {
  const card = document.querySelector('#word-card').getBoundingClientRect();
  const under = [...document.querySelectorAll('#phrase-view .tok')].filter((token) => {
    const r = token.getBoundingClientRect();
    return r.left < card.right && card.left < r.right && r.top < card.bottom && card.top < r.bottom;
  }).length;
  return { under, active: document.querySelectorAll('#phrase-view .tok.active').length };
}'''

# The list is unfolded from the bottom bar: it sits on that bar, under the
# details, shows the selected row, and every bar button is a finger wide.
LIST_STATE = r'''() => {
  const box = (selector) => document.querySelector(selector).getBoundingClientRect();
  const panel = box('#list-panel'), dock = box('#dock'), details = box('#details');
  const row = box('#words-list .selected'), list = box('#words-list');
  const targets = [...document.querySelectorAll('#dock button, #copy-phrase')]
    .filter((el) => el.getClientRects().length);
  return {
    barAtBottom: Math.abs(dock.bottom - window.innerHeight) < 1.5,
    onBar: Math.abs(panel.bottom - dock.top) < 1.5 && details.bottom <= panel.top + 1.5,
    rowShown: row.top >= list.top - 1 && row.bottom <= list.bottom + 1,
    fits: ['#details', '#words-list'].every((selector) => {
      const el = document.querySelector(selector);
      return el.scrollWidth <= el.clientWidth + 1;
    }),
    small: targets.filter((el) => {
      const r = el.getBoundingClientRect();
      return r.width < 43.5 || r.height < 43.5;
    }).map((el) => el.id),
  };
}'''


def contraction_token(page):
    """The first token whose label carries an apostrophe, if any."""
    tokens = page.locator('#phrase-view .tok')
    for index in range(tokens.count()):
        label = tokens.nth(index).locator('.lbl').text_content()
        if label and "'" in label:
            return tokens.nth(index)
    return None


def hover_contraction_token(page):
    token = contraction_token(page)
    if token is None:
        return False
    token.hover()
    return True


def watch_errors(page, errors):
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
    page.on('pageerror', lambda error: errors.append(str(error)))


def check(problems, ok, message):
    """Count one problem unless the condition holds."""
    if not ok:
        problems.append(message)


def desktop_run(browser, args, sample):
    """The pointer layout at 1440x900: 1 with console errors, else 0."""
    errors = []
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    watch_errors(page, errors)
    page.goto(args.url + '/')
    page.wait_for_timeout(1500)
    if args.locale:
        page.select_option('#ui-language', args.locale)
        page.wait_for_timeout(1500)
    page.set_input_files('#file-input', sample)
    page.wait_for_timeout(3000)
    for word in args.words.split(','):
        page.locator('#words-list li', has_text=word.strip()).first.click()
        page.wait_for_timeout(4000)

    for selector in ('#phrase-translation-text', '#phrase-literal-text'):
        element = page.locator(selector)
        print(f'{selector:28} visible={element.is_visible()!s:5} '
              f'text={element.text_content()[:80]!r}')
    if hover_contraction_token(page):
        page.wait_for_timeout(700)
        tip = page.locator('#tooltip')
        print('tooltip visible:', tip.is_visible(), '|',
              tip.inner_text().replace('\n', ' | ')[:170])
    else:
        print('tooltip: no contraction token in the current phrase')
    page.screenshot(path=os.path.join(args.out, f'web-ui-{args.locale}-check.png'))
    print('console errors:', errors if errors else 'none')
    page.close()
    return 1 if errors else 0


def phone_shot(page, args, key, name):
    page.screenshot(path=os.path.join(args.out, f'mobile-{key}-{name}.png'))


def phone_walk(page, args, key, word):
    """Pick a word, read its card, copy, step, unfold the list from the bar."""
    problems = []
    phone_shot(page, args, key, 'loaded')
    check(problems, page.locator('#list-panel').is_visible()
          and page.locator('#list-toggle').is_disabled(),
          'the list is not the content before a pick')
    check(problems, page.evaluate(LOADED_STATE)['fills'],
          'the list does not fill the screen down to the bar before a pick')
    page.locator(f'#words-list li[data-word="{word}"]').tap()
    page.wait_for_function(TRANSLATED, timeout=90000)
    page.wait_for_timeout(300)
    state = page.evaluate(WORD_STATE)
    check(problems, state['listFolded'], 'the list stays open after a pick')
    check(problems, state['barAtBottom'], 'the bottom bar leaves the bottom edge after a pick')
    check(problems, state['aboveBar'], 'the translation needs scrolling under the bottom bar')
    check(problems, state['fits'], 'the word details overflow sideways')
    phone_shot(page, args, key, 'word')
    token = contraction_token(page)
    token.tap()
    page.wait_for_timeout(200)
    card = page.evaluate(CARD_STATE)
    check(problems, card['active'] == 1, 'a token tap does not open its card')
    check(problems, card['under'] == 0, 'the word card covers a phrase token')
    phone_shot(page, args, key, 'card')
    token.tap(force=True)  # forced: a card that wrongly covers the word must not hang the walk
    page.wait_for_timeout(200)
    check(problems, not page.locator('#word-card').is_visible(),
          'a second tap does not close the card')
    label = page.locator('#copy-phrase-label')
    before = label.inner_text()
    page.locator('#copy-phrase').tap()
    page.wait_for_timeout(150)
    check(problems, label.inner_text() != before, 'the copy button does not confirm')
    before = page.locator('#selected-word-label').inner_text()
    page.locator('#word-next').tap()
    page.wait_for_timeout(200)
    check(problems, page.locator('#selected-word-label').inner_text() != before,
          'next does not step to the next word')
    page.locator('#list-toggle').tap()
    page.wait_for_timeout(350)
    state = page.evaluate(LIST_STATE)
    check(problems, state['barAtBottom'], 'the bottom bar leaves the bottom edge with the list open')
    check(problems, state['onBar'], 'the unfolded list does not sit on the bottom bar')
    check(problems, state['rowShown'], 'the selected row is out of view in the list')
    check(problems, state['fits'], 'the unfolded list overflows sideways')
    check(problems, not state['small'], f'bar buttons under 44 px: {state["small"]}')
    phone_shot(page, args, key, 'list')
    second = page.locator('#words-list li').nth(1)
    expected = second.get_attribute('data-word')
    second.tap()
    page.wait_for_timeout(200)
    check(problems, page.locator('#selected-word-label').inner_text() == expected,
          'a pick from the list does not show that word')
    check(problems, not page.locator('#list-panel').is_visible(),
          'the list stays open after a pick from it')
    return problems


def phone_extras(page, problems):
    """The word chip, a legend chip, the folded menus and the source form."""
    word_chip = page.locator('#selected-pos-chip')
    if word_chip.is_visible():
        word_chip.tap()
        page.wait_for_timeout(150)
        check(problems, page.locator('#word-explain').is_visible(),
              'the word chip does not expand its explanation')
        word_chip.tap()
    chip = page.locator('#legend .chip').first
    chip.scroll_into_view_if_needed()
    chip.tap()
    page.wait_for_timeout(200)
    explanation = page.locator('#legend-explain')
    check(problems, explanation.is_visible() and explanation.inner_text().strip() != '',
          'a chip tap does not expand its explanation')
    check(problems, page.locator('#legend .chip[aria-pressed="true"]').count() == 1,
          'the expanded chip is not marked pressed')
    page.locator('#legend .chip[aria-pressed="true"]').tap()
    page.wait_for_timeout(200)
    check(problems, not explanation.is_visible(),
          'a second chip tap does not fold the explanation')
    language = page.locator('#ui-language')
    page.locator('#settings-toggle').tap()
    page.wait_for_timeout(150)
    check(problems, language.is_visible(), 'the settings button does not open the menus')
    page.locator('#settings-toggle').tap()
    page.wait_for_timeout(150)
    check(problems, not language.is_visible(), 'the settings button does not close the menus')
    tabs = page.locator('#source-tabs')
    page.locator('#source-summary').tap()
    page.wait_for_timeout(150)
    check(problems, tabs.is_visible(), 'the source row does not open the source form')
    page.locator('#source-summary').tap()
    page.wait_for_timeout(150)
    check(problems, not tabs.is_visible(), 'the source row does not fold the source form')


def run_mobile(browser, args, sample):
    """Every chosen phone profile from a fresh context: the problem count."""
    wanted = {key for key in (args.device or '').split(',') if key}
    profiles = [profile for profile in MOBILE_PROFILES if not wanted or profile[0] in wanted]
    if not profiles:
        print('no such device; keys:', ', '.join(profile[0] for profile in MOBILE_PROFILES))
        return 1
    total = 0
    for key, width, height, dpr in profiles:
        errors = []
        context = browser.new_context(viewport={'width': width, 'height': height},
                                      device_scale_factor=dpr, is_mobile=True, has_touch=True)
        # the phone layout keeps the language menu folded: choose the locale up front
        context.add_init_script(f'localStorage.setItem("ui_language", {json.dumps(args.locale)})')
        page = context.new_page()
        watch_errors(page, errors)
        page.goto(args.url + '/')
        page.wait_for_function(READY, timeout=30000)
        page.set_input_files('#file-input', sample)
        page.wait_for_selector('#words-list li', timeout=120000)
        page.wait_for_timeout(400)
        problems = phone_walk(page, args, key, args.words.split(',')[0].strip())
        phone_extras(page, problems)
        context.close()
        found = problems + [f'console: {error}' for error in errors]
        print(f'{key:11} {len(found)} problem(s)' + (f': {"; ".join(found)}' if found else ''))
        total += len(found)
    print(f'screenshots mobile-<device>-loaded|word|card|list.png in {args.out}')
    return total


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Browser verification of the web translation view.')
    parser.add_argument('--url', default='http://127.0.0.1:8000',
                        help='base URL of a running backend')
    parser.add_argument('--locale', default='ru', help='UI locale to switch to')
    parser.add_argument('--words', default='do,have,look',
                        help='comma-separated word list selections (mobile: the first one)')
    parser.add_argument('--sample', default=None,
                        help='subtitle file (default: first samples/*.srt)')
    parser.add_argument('--out', default=str(REPO_ROOT / 'tmp' / 'screenshots'),
                        help='screenshot directory')
    parser.add_argument('--mobile', action='store_true',
                        help='walk the phone profiles with touch emulation')
    parser.add_argument('--device', default='',
                        help='comma-separated phone profile keys (default: all), e.g. 360x780,390x844')
    args = parser.parse_args()

    sample = args.sample or min(glob.glob(str(REPO_ROOT / 'samples' / '*.srt')) or [None])
    if not sample:
        parser.error('no subtitle sample found under samples/')
    os.makedirs(args.out, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
        status = run_mobile(browser, args, sample) if args.mobile else desktop_run(browser, args, sample)
        browser.close()
    return min(status, 255)


if __name__ == '__main__':
    sys.exit(main())
