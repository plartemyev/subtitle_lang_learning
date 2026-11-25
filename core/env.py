"""Gitignored .env loading for frontends launched outside compose.

Docker compose reads the repository .env itself; the desktop frontend and the
bare web backend run on the host, so they load the same file once at startup.
Secrets never enter the repository (see README).
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DOTENV_PATH = Path(__file__).resolve().parent.parent / '.env'


def load_dotenv(path=DOTENV_PATH):
    """Set KEY=VALUE lines as environment defaults; real environment
    variables always win. A missing file is a normal outcome."""
    try:
        content = Path(path).read_text(encoding='utf-8')
    except OSError:
        return
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)
    logger.info('loaded %s', path)
