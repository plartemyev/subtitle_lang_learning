"""Remote model translation against an OpenAI-compatible server.

The primary engine: an Ollama/llama.cpp server on the LAN serves a big
multilingual model (Qwen3.6-35B-A3B in the reference deployment). The
prompt protocol is the collapsed one-liner the benchmark validated -
``Translate subtitle into <language>: <subtitle text>`` - with thinking
mode explicitly disabled: Qwen3.6-class models think *by default*, which
costs hundreds of invisible reasoning tokens and seconds of latency
(reasoning lands in a separate ``reasoning_content`` field the provider
ignores).

Fallback-switch policy (checked before every remote call):
1. a cached dead state skips the remote entirely;
2. otherwise a connect probe runs with a 0.5 s timeout;
3. then a slot-availability probe (llama.cpp /health answers 503 when all
   slots are busy; servers without /health are treated as available);
4. no slot caches the remote dead for SLOT_DEAD_SECONDS (slots free up
   quickly), a failed connect caches it dead for CONNECT_DEAD_SECONDS;
5. a successful call clears the cached state. Failures raise so the
   fallback chain moves on to the local engine.
"""
import json
import logging
import os
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from core.translation.models import PhraseTranslation

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {'en': 'English', 'de': 'German', 'ru': 'Russian',
                  'th': 'Thai'}
CONNECT_PROBE_TIMEOUT = 0.5
SLOT_PROBE_TIMEOUT = 0.5
CONNECT_DEAD_SECONDS = 600
SLOT_DEAD_SECONDS = 10


def _strip_reasoning(text):
    for open_tag, close_tag in (('<think>', '</think>'),
                                ('<thinking>', '</thinking>')):
        while open_tag in text and close_tag in text:
            head, rest = text.split(open_tag, 1)
            _block, text = rest.split(close_tag, 1)
            text = head + text
    return text.strip()


class OllamaProvider:
    """Model translation over an OpenAI-compatible chat endpoint."""

    def __init__(self, base_url, model, api_key='', timeout=120.0):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.label = 'remote-ollama'
        self._dead_until = 0.0
        self._dead_reason = 'fresh'
        self._state_lock = threading.Lock()

    @classmethod
    def from_env(cls):
        """Provider configured from OLLAMA_* variables, or None when the
        remote engine is not configured. The API token stays in the
        gitignored secrets (.env), never in the repository."""
        base_url = os.environ.get('OLLAMA_BASE_URL')
        model = os.environ.get('OLLAMA_MODEL')
        if not base_url or not model:
            return None
        return cls(base_url, model,
                   api_key=os.environ.get('OLLAMA_API_KEY', ''))

    def _mark_dead(self, seconds, reason):
        with self._state_lock:
            self._dead_until = time.monotonic() + seconds
        self._dead_reason = reason
        logger.info('%s: remote cached dead for %ss (%s)', self.label,
                    seconds, reason)

    def _clear_dead(self):
        with self._state_lock:
            self._dead_until = 0.0
        self._dead_reason = 'fresh'

    def _cached_dead(self):
        with self._state_lock:
            remaining = self._dead_until - time.monotonic()
        return remaining if remaining > 0 else 0.0

    def _probe(self):
        """Connect probe (0.5 s) then slot probe; raises with the dead cache
        populated when either fails."""
        parts = urllib.parse.urlsplit(self.base_url)
        port = parts.port or (443 if parts.scheme == 'https' else 80)
        try:
            socket.create_connection((parts.hostname, port),
                                     timeout=CONNECT_PROBE_TIMEOUT).close()
        except OSError as error:
            self._mark_dead(CONNECT_DEAD_SECONDS, f'no connect: {error}')
            raise RuntimeError(f'{self.label}: no connect ({error}); remote '
                               f'cached dead for {CONNECT_DEAD_SECONDS}s')
        try:
            request = urllib.request.Request(f'{self.base_url}/health')
            if self.api_key:
                request.add_header('Authorization', f'Bearer {self.api_key}')
            with urllib.request.urlopen(request,
                                        timeout=SLOT_PROBE_TIMEOUT) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
            error.close()  # an HTTPError is an open response body
        except (urllib.error.URLError, OSError) as error:
            self._mark_dead(SLOT_DEAD_SECONDS, f'health probe failed: {error}')
            raise RuntimeError(f'{self.label}: health probe failed ({error}); '
                               f'remote cached dead for {SLOT_DEAD_SECONDS}s')
        if status == 503:
            self._mark_dead(SLOT_DEAD_SECONDS, 'no free slot')
            raise RuntimeError(f'{self.label}: no free slot; remote cached '
                               f'dead for {SLOT_DEAD_SECONDS}s')
        # 200 and unknown servers (404 on /health) are treated as available

    def translate(self, text, source_code, target_locale, words):
        cached_dead = self._cached_dead()
        if cached_dead:
            raise RuntimeError(f'{self.label}: remote cached dead for another '
                               f'{cached_dead:.0f}s ({self._dead_reason})')
        self._probe()
        payload = {
            'model': self.model,
            'messages': [{'role': 'user', 'content':
                          f'Translate subtitle into '
                          f'{LANGUAGE_NAMES[target_locale]}: {text}'}],
            'max_tokens': 512,
            'temperature': 0.0,
            'chat_template_kwargs': {'enable_thinking': False},
        }
        request = urllib.request.Request(
            f'{self.base_url}/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json',
                     'Authorization': f'Bearer {self.api_key}'})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as error:
            error.close()  # an HTTPError is an open response body
            if error.code == 503:
                self._mark_dead(SLOT_DEAD_SECONDS, 'no free slot')
                raise RuntimeError(f'{self.label}: no free slot; remote '
                                   f'cached dead for {SLOT_DEAD_SECONDS}s')
            raise RuntimeError(f'{self.label}: HTTP {error.code}') from error
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as error:
            self._mark_dead(CONNECT_DEAD_SECONDS, f'request failed: {error}')
            raise RuntimeError(f'{self.label}: {error}; remote cached dead '
                               f'for {CONNECT_DEAD_SECONDS}s')
        content = _strip_reasoning(
            str(result['choices'][0]['message'].get('content') or '').strip())
        if not content:
            raise RuntimeError(f'{self.label}: empty completion '
                               f'(thinking mode not disabled?)')
        self._clear_dead()
        return PhraseTranslation(source_text=text, target_text=content,
                                 words=[])
