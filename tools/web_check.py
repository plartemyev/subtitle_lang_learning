#!/usr/bin/env python3
"""Browser verification of the web frontend via playwright-controlled chromium.

Loads the SPA against a running backend, uploads a subtitle sample, selects
words, hovers a contraction token and reports the translation view state plus
any console/page errors - the frontend degrades silently on API failures
(catch -> empty payloads), so error counting is the point, not just looks.

Usage (backend must be up):
    poetry run python -m uvicorn web.app:app --port 8123   # or docker compose
    python3 tools/web_check.py --url http://127.0.0.1:8123

Needs the system playwright package (python3 -c 'import playwright') and
/usr/bin/chromium; screenshots land in tmp/screenshots/.
"""
import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402


def hover_contraction_token(page):
    """Hover the first token whose label carries an apostrophe, if any."""
    tokens = page.locator('#phrase-view .tok')
    for index in range(tokens.count()):
        label = tokens.nth(index).locator('.lbl').text_content()
        if label and "'" in label:
            tokens.nth(index).hover()
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Browser verification of the web translation view.')
    parser.add_argument('--url', default='http://127.0.0.1:8000',
                        help='base URL of a running backend')
    parser.add_argument('--locale', default='ru', help='UI locale to switch to')
    parser.add_argument('--words', default='do,have,look',
                        help='comma-separated word list selections')
    parser.add_argument('--sample', default=None,
                        help='subtitle file (default: first samples/*.srt)')
    parser.add_argument('--out', default=str(REPO_ROOT / 'tmp' / 'screenshots'),
                        help='screenshot directory')
    args = parser.parse_args()

    import glob
    sample = args.sample or (sorted(glob.glob(str(REPO_ROOT / 'samples' / '*.srt')) or [None])[0])
    if not sample:
        parser.error('no subtitle sample found under samples/')
    os.makedirs(args.out, exist_ok=True)

    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        page.on('console', lambda message: errors.append(message.text)
                if message.type == 'error' else None)
        page.on('pageerror', lambda error: errors.append(str(error)))
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
        page.screenshot(path=f'{args.out}/web-ui-{args.locale}-check.png')
        print('console errors:', errors if errors else 'none')
        browser.close()
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
