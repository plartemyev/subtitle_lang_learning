"""SQLite-backed LRU cache for phrase translation calls (~2 GiB budget).

Counter-based LRU per the project design: a process-wide monotonically
increasing counter is written into a row on every access, and eviction always
drops the rows with the lowest counters (ties: oldest access time). The cache
lives in the data directory and survives restarts; payloads are the serialized
phrase translation responses.
"""
import hashlib
import json
import os
import sqlite3
import threading
import time
from itertools import count

DEFAULT_MAX_BYTES = 2 * 1024 ** 3
EVICTION_BATCH = 64
CACHE_VERSION = 'v2'  # bump to invalidate stored payloads after format changes

_SCHEMA = """
CREATE TABLE IF NOT EXISTS translations (
    key TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    nbytes INTEGER NOT NULL,
    access_counter INTEGER NOT NULL,
    created_at REAL NOT NULL,
    accessed_at REAL NOT NULL
);
"""


def cache_key(source_code, target_locale, text):
    """Stable cache key for one translation call."""
    material = f'{CACHE_VERSION}|{source_code}|{target_locale}|{text}'
    return hashlib.sha256(material.encode('utf-8')).hexdigest()


class TranslationCache:
    """Thread-safe sqlite LRU store keyed by :func:`cache_key`."""

    def __init__(self, path, max_bytes=None):
        self._path = str(path)
        self._max_bytes = max_bytes if max_bytes is not None else int(
            os.environ.get('SUBTITLE_LEARNING_CACHE_MAX_BYTES', DEFAULT_MAX_BYTES))
        self._lock = threading.Lock()  # uvicorn serves requests on a threadpool
        self._counter = count(1)
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        self._db = sqlite3.connect(self._path, check_same_thread=False)
        self._db.execute(_SCHEMA)
        self._db.commit()

    def get(self, key):
        """Payload of a cached call, refreshing its LRU counter; None on miss."""
        with self._lock:
            row = self._db.execute('SELECT payload FROM translations WHERE key = ?',
                                   (key,)).fetchone()
            if row is None:
                return None
            self._db.execute(
                'UPDATE translations SET access_counter = ?, accessed_at = ? WHERE key = ?',
                (next(self._counter), time.time(), key))
            self._db.commit()
            return json.loads(row[0])

    def put(self, key, payload):
        """Store one call result, evicting least recently used rows over budget.

        Payloads larger than the whole budget are not stored: phrase
        responses are kilobytes, so this only guards a misconfigured budget.
        """
        blob = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
        nbytes = len(blob.encode('utf-8'))
        if nbytes > self._max_bytes:
            return
        now = time.time()
        with self._lock:
            self._db.execute('INSERT OR REPLACE INTO translations VALUES (?, ?, ?, ?, ?, ?)',
                             (key, blob, nbytes, next(self._counter), now, now))
            self._evict_locked()
            self._db.commit()

    def _evict_locked(self):
        """Drop lowest-counter rows until the payload budget fits.

        Rows are scanned least-recently-used first and only the prefix that
        restores the budget is deleted, never the whole scan batch.
        """
        total = self._db.execute('SELECT COALESCE(SUM(nbytes), 0) FROM translations').fetchone()[0]
        while total > self._max_bytes:
            victims = self._db.execute(
                'SELECT key, nbytes FROM translations '
                'ORDER BY access_counter ASC, accessed_at ASC LIMIT ?',
                (EVICTION_BATCH,)).fetchall()
            if not victims:
                return
            deleted = []
            for victim in victims:
                deleted.append((victim[0],))
                total -= victim[1]
                if total <= self._max_bytes:
                    break
            self._db.executemany('DELETE FROM translations WHERE key = ?', deleted)
