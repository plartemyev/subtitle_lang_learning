"""Filesystem locations shared by every frontend."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Data directory (dictionary, models, caches) living outside the
    repository by default; override with ``SUBTITLE_LEARNING_DATA_DIR``."""
    return Path(os.environ.get('SUBTITLE_LEARNING_DATA_DIR', REPO_ROOT / 'data'))
