#!/usr/bin/env python3
"""Download and convert the offline translation model (one-time preparation).

Fetches facebook/nllb-200-distilled-600M (CC-BY-NC-4.0: noncommercial use
only) from HuggingFace into tmp/nllb-build/, converts it to a CTranslate2
int8 model and stores it with the tokenizer files under
<data-dir>/models/nllb-600m-ct2. Needs the poetry tools group
(`poetry install --with tools`, which brings CPU torch) - the runtime web
stack never loads torch.

Usage: poetry run python tools/prepare_nllb.py [--data-dir data] [--compute-type int8]

A HuggingFace token speeds the download up; it is read from the HF_TOKEN
environment variable or the gitignored .env file next to the repository.
"""
import argparse
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HF_MODEL_ID = 'facebook/nllb-200-distilled-600M'
HF_BASE_URL = f'https://huggingface.co/{HF_MODEL_ID}/resolve/main'
MODEL_DIR_NAME = 'nllb-600m-ct2'
WEIGHTS_FILE = 'pytorch_model.bin'
CONFIG_FILES = ['config.json', 'generation_config.json']
TOKENIZER_FILES = ['tokenizer.json', 'tokenizer_config.json',
                   'special_tokens_map.json', 'sentencepiece.bpe.model']
CONVERTER = 'ct2-transformers-converter'


def load_hf_token():
    """Token from the environment or the gitignored .env next to the repo."""
    token = os.environ.get('HF_TOKEN')
    if token:
        return token
    env_file = REPO_ROOT / '.env'
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        if line.startswith('HF_TOKEN='):
            return line.split('=', 1)[1].strip()
    return None


def download(filename, destination, token):
    """Fetch one repo file, reusing a completed download on reruns."""
    target = destination / filename
    if target.exists() and target.stat().st_size > 0:
        print(f'reusing {target.name} ({target.stat().st_size} bytes)')
        return
    request = urllib.request.Request(f'{HF_BASE_URL}/{filename}')
    if token:
        request.add_header('Authorization', f'Bearer {token}')
    print(f'downloading {filename} ...')
    partial = target.with_suffix(target.suffix + '.part')
    with urllib.request.urlopen(request) as response, open(partial, 'wb') as out:
        while True:
            chunk = response.read(16 * 1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            print(f'  {filename}: {partial.stat().st_size} bytes', end='\r')
    print()
    partial.replace(target)


def main():
    parser = argparse.ArgumentParser(
        description='Prepare the offline NLLB translation model.')
    parser.add_argument('--data-dir', default=str(REPO_ROOT / 'data'))
    parser.add_argument('--compute-type', default='int8',
                        help='CTranslate2 quantization (default int8)')
    args = parser.parse_args()

    build_dir = REPO_ROOT / 'tmp' / 'nllb-build' / HF_MODEL_ID.split('/')[-1]
    build_dir.mkdir(parents=True, exist_ok=True)
    token = load_hf_token()
    for filename in CONFIG_FILES + TOKENIZER_FILES + [WEIGHTS_FILE]:
        download(filename, build_dir, token)

    model_dir = Path(args.data_dir) / 'models' / MODEL_DIR_NAME
    if model_dir.joinpath('model.bin').exists():
        print(f'model already converted: {model_dir}')
        return
    subprocess.run([CONVERTER,
                    '--model', str(build_dir),
                    '--output_dir', str(model_dir),
                    '--quantization', args.compute_type,
                    '--force'], check=True)
    for filename in TOKENIZER_FILES:
        shutil.copy2(build_dir / filename, model_dir / filename)
    print(f'offline translation model ready under {model_dir}')
    print('NLLB-200 weights are CC-BY-NC-4.0: noncommercial use only.')


if __name__ == '__main__':
    main()
