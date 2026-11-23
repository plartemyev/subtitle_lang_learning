"""Counter-based LRU behaviour of the sqlite phrase translation cache."""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.translation.cache import TranslationCache, cache_key

# test databases live in the project tmp dir (the system temp is never used)
TMP_DIR = PROJECT_ROOT / 'tmp' / 'tests'


class CacheKeyTests(unittest.TestCase):
    def test_same_call_maps_to_same_key(self):
        self.assertEqual(cache_key('eng', 'ru', 'To be or not to be'),
                         cache_key('eng', 'ru', 'To be or not to be'))

    def test_direction_and_text_change_the_key(self):
        key = cache_key('eng', 'ru', 'phrase')
        self.assertNotEqual(key, cache_key('ru', 'eng', 'phrase'))
        self.assertNotEqual(key, cache_key('eng', 'de', 'phrase'))
        self.assertNotEqual(key, cache_key('eng', 'ru', 'phrases'))


class TranslationCacheTests(unittest.TestCase):
    def setUp(self):
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = TMP_DIR / f'cache-{self.id()}.sqlite'
        self.db_path.unlink(missing_ok=True)
        self.cache = TranslationCache(self.db_path, max_bytes=1000)
        self.addCleanup(self.cache._db.close)

    def test_get_returns_put_payload(self):
        key = cache_key('eng', 'ru', 'To be, or not to be.')
        self.cache.put(key, {'translation': 'Быть или не быть'})
        self.assertEqual(self.cache.get(key), {'translation': 'Быть или не быть'})

    def test_miss_returns_none(self):
        self.assertIsNone(self.cache.get(cache_key('eng', 'ru', 'never stored')))

    def test_eviction_drops_the_least_recently_used_entry(self):
        # three payloads of ~311 bytes each fit the 1000-byte budget
        keys = [cache_key('eng', 'de', f'phrase {index}') for index in range(3)]
        for key in keys:
            self.cache.put(key, {'text': 'x' * 300})
        # refreshing the first entry makes the second the least recently used
        self.cache.get(keys[0])
        self.cache.put(cache_key('eng', 'de', 'one more'), {'text': 'x' * 300})
        self.assertIsNone(self.cache.get(keys[1]), 'least recently used must be evicted')
        for index in (0, 2):
            self.assertIsNotNone(self.cache.get(keys[index]))

    def test_oversized_payload_is_not_stored(self):
        key = cache_key('eng', 'de', 'huge')
        self.cache.put(key, {'text': 'x' * 2000})
        self.assertIsNone(self.cache.get(key))


if __name__ == '__main__':
    unittest.main()
