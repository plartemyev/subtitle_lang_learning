"""Remote model translation against an OpenAI-compatible server.

The primary engine: an Ollama/llama.cpp server on the LAN serves a big
multilingual model (Qwen3.6-35B-A3B in the reference deployment). The
prompt protocol is the collapsed one-liner the benchmark validated -
``Translate subtitle into <language>: <subtitle text>`` - with thinking
mode explicitly disabled: Qwen3.6-class models think *by default*, which
costs hundreds of invisible reasoning tokens and seconds of latency
(reasoning lands in a separate ``reasoning_content`` field the provider
ignores). Connection, HTTP and empty-output failures raise so the
fallback chain moves on to the local engine.
"""
import json
import logging
import os
import urllib.error
import urllib.request

from core.translation.models import PhraseTranslation

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {'en': 'English', 'de': 'German', 'ru': 'Russian',
                  'th': 'Thai'}


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

    def translate(self, text, source_code, target_locale, words):
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
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f'{self.label}: {error}') from error
        content = _strip_reasoning(
            str(result['choices'][0]['message'].get('content') or '').strip())
        if not content:
            raise RuntimeError(f'{self.label}: empty completion '
                               f'(thinking mode not disabled?)')
        return PhraseTranslation(source_text=text, target_text=content,
                                 words=[])
