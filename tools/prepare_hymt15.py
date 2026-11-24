#!/usr/bin/env python3
"""Download the local fallback translation model (one-time preparation).

Fetches the tencent/HY-MT1.5-1.8B Q4_K_M GGUF (~1.1 GB) from HuggingFace
into <data-dir>/models/hymt15-1.8b-q4km/. This is the offline backup engine
for the web stack: when the remote OLLAMA_* server is unreachable, the app
serves a llama.cpp subprocess on this model. Runtime license note: Tencent
HY Community License (open weights with restrictions) - the repository
ships no weights, every user downloads their own copy.

Usage: poetry run python tools/prepare_hymt15.py [--data-dir data]
"""
import argparse
import os
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HF_MODEL_ID = 'tencent/HY-MT1.5-1.8B-GGUF'
HF_BASE_URL = f'https://huggingface.co/{HF_MODEL_ID}/resolve/main'
MODEL_DIR_NAME = 'hymt15-1.8b-q4km'
MODEL_FILE = 'HY-MT1.5-1.8B-Q4_K_M.gguf'
DOWNLOAD_CHUNK_BYTES = 16 * 1024 * 1024


def load_hf_token():
    """Token from the environment or the gitignored .env next to the repo."""
    token = os.environ.get('HF_TOKEN')
    if token:
        return token
    env_file = REPO_ROOT / '.env'
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith('HF_TOKEN='):
            return line.split('=', 1)[1].strip()
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Download the HY-MT1.5-1.8B fallback model GGUF.')
    parser.add_argument('--data-dir', default=str(REPO_ROOT / 'data'))
    args = parser.parse_args()
    target_dir = Path(args.data_dir) / 'models' / MODEL_DIR_NAME
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / MODEL_FILE
    if target.exists() and target.stat().st_size > 0:
        print(f'{MODEL_FILE}: already prepared ({target.stat().st_size} bytes)')
        return
    url = f'{HF_BASE_URL}/{MODEL_FILE}'
    request = urllib.request.Request(url)
    token = load_hf_token()
    if token:
        request.add_header('Authorization', f'Bearer {token}')
    partial = target.with_suffix(target.suffix + '.part')
    print(f'downloading {url} ...')
    with urllib.request.urlopen(request) as response, open(partial, 'wb') as out:
        while True:
            chunk = response.read(DOWNLOAD_CHUNK_BYTES)
            if not chunk:
                break
            out.write(chunk)
            print(f'  {partial.stat().st_size} bytes', end='\r')
    print()
    partial.replace(target)
    print(f'fallback model ready: {target}')


if __name__ == '__main__':
    main()
