"""Local HY-MT1.5-1.8B fallback served by a llama-server subprocess.

The offline backup engine when the remote server is unreachable: Tencent's
HY-MT1.5-1.8B translation model (Q4_K_M GGUF, ~1.1 GB, prepared once by
tools/prepare_hymt15.py) runs under llama.cpp on the CPU. The server
process is spawned lazily on the first fallback translation and kept warm;
prompt and sampling follow the model card verbatim (the collapsed protocol
does not apply here - this model only understands its own instruction
format). Failures raise so the caller can answer 503.
"""
import atexit
import json
import logging
import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from core.translation.models import PhraseTranslation

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {'en': 'English', 'de': 'German', 'ru': 'Russian',
                  'th': 'Thai'}
MODEL_DIR_NAME = 'hymt15-1.8b-q4km'
MODEL_FILE = 'HY-MT1.5-1.8B-Q4_K_M.gguf'
USER_TEMPLATE = ('Translate the following segment into {target}, without '
                 'additional explanation.\n\n{text}')
SAMPLING = {'temperature': 0.7, 'top_p': 0.6, 'top_k': 20,
            'repeat_penalty': 1.05}


class LocalLlamaProvider:
    """Fallback translation via a llama-server subprocess hosting HY-MT1.5."""

    def __init__(self, model_path, server_bin, port, timeout=180.0):
        self.model_path = str(model_path)
        self.server_bin = server_bin
        self.port = port
        self.timeout = timeout
        self.label = 'local-hymt15-1.8b'
        self._process = None
        self._lock = threading.Lock()
        atexit.register(self.stop)

    @classmethod
    def from_env(cls, data_dir):
        """Provider from LLAMA_LOCAL_* variables, or None when the model
        file or the llama-server binary is not available."""
        model_path = Path(os.environ.get(
            'LLAMA_LOCAL_MODEL',
            Path(data_dir) / 'models' / MODEL_DIR_NAME / MODEL_FILE))
        server_bin = os.environ.get('LLAMA_SERVER_BIN', 'llama-server')
        resolved = shutil.which(server_bin) or (
            server_bin if Path(server_bin).exists() else None)
        if not model_path.exists() or not resolved:
            return None
        port = int(os.environ.get('LLAMA_LOCAL_PORT', '8802'))
        return cls(model_path, resolved, port)

    def _base_url(self):
        return f'http://127.0.0.1:{self.port}'

    def _ensure_server(self):
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return
            command = [self.server_bin, '-m', self.model_path,
                       '--port', str(self.port), '-t', '8', '-c', '2048',
                       '-ngl', '0', '--jinja', '--no-warmup']
            logger.info('starting local llama-server on port %d', self.port)
            self._process = subprocess.Popen(
                command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + self.timeout
            while time.monotonic() < deadline:
                if self._process.poll() is not None:
                    raise RuntimeError(
                        f'{self.label}: llama-server exited during startup')
                try:
                    with urllib.request.urlopen(f'{self._base_url()}/health',
                                                timeout=2) as response:
                        if response.status == 200:
                            return
                except (urllib.error.URLError, OSError):
                    pass
                time.sleep(1)
            self.stop()
            raise RuntimeError(f'{self.label}: llama-server did not become '
                               f'healthy within {self.timeout:.0f}s')

    def translate(self, text, source_code, target_locale, words):
        self._ensure_server()
        payload = {
            'messages': [{'role': 'user', 'content': USER_TEMPLATE.format(
                target=LANGUAGE_NAMES[target_locale], text=text)}],
            'max_tokens': 256,
            'cache_prompt': True,
            **SAMPLING,
        }
        request = urllib.request.Request(
            f'{self._base_url()}/v1/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as error:
            self.stop()  # a wedged server must not poison later fallbacks
            raise RuntimeError(f'{self.label}: {error}') from error
        content = str(result['choices'][0]['message'].get('content')
                      or '').strip()
        if not content:
            raise RuntimeError(f'{self.label}: empty completion')
        return PhraseTranslation(source_text=text, target_text=content,
                                 words=[])

    def stop(self):
        process, self._process = self._process, None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
