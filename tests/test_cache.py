import tempfile
import unittest

from clients.cache import SourceResponseCache


class CacheTests(unittest.TestCase):
    def test_cache_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = SourceResponseCache(root=tmpdir)
            key = cache.build_key("demo", "https://example.com/feed.json", "players")

            self.assertIsNone(cache.read_text(key))
            cache.write_text(key, "hello")
            self.assertEqual(cache.read_text(key), "hello")


if __name__ == "__main__":
    unittest.main()
