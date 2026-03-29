import unittest
from datetime import datetime, timezone

from kickbase.bot.news_relevance import news_recency_signal, parse_reported_at


class NewsRelevanceTests(unittest.TestCase):
    def test_parses_iso_timestamp_with_z_suffix(self) -> None:
        parsed = parse_reported_at("2026-03-28T10:15:00Z")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.isoformat(), "2026-03-28T10:15:00+00:00")

    def test_computes_recency_score(self) -> None:
        now = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
        score = news_recency_signal("2026-03-27T12:00:00Z", now=now, half_life_hours=72.0)
        self.assertAlmostEqual(score, 0.666667)

    def test_returns_zero_for_invalid_timestamp(self) -> None:
        self.assertEqual(news_recency_signal("not-a-date"), 0.0)


if __name__ == "__main__":
    unittest.main()
