import unittest
from unittest.mock import patch

from kickbase.bot.models import PlayerRecord, RankingThresholds, RankingWeights
from kickbase.bot.ranking import RankingService


class RankingNewsRecencyTests(unittest.TestCase):
    @patch("kickbase.bot.ranking.news_recency_signal", return_value=0.42)
    def test_rank_injects_news_recency_signal_when_reported_at_is_present(self, mock_news_recency_signal) -> None:
        service = RankingService(
            RankingWeights(
                market_value_signal=0.0,
                form_signal=0.0,
                availability_signal=0.0,
                news_signal=0.0,
                news_recency_signal=1.0,
                trend_signal=0.0,
                value_opportunity_signal=0.0,
            ),
            RankingThresholds(minimum_market_value=500000, minimum_confidence=0.0),
        )

        player = PlayerRecord(
            "1",
            "Recent Player",
            market_value=600000,
            confidence=1.0,
            reported_at="2026-03-27T12:00:00Z",
            signals={},
        )

        ranked = service.rank([player])

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].normalized_signals["news_recency_signal"], 0.42)
        self.assertEqual(ranked[0].score, 0.42)
        mock_news_recency_signal.assert_called_once_with("2026-03-27T12:00:00Z")

    def test_rank_keeps_news_recency_disabled_by_default(self) -> None:
        service = RankingService(
            RankingWeights(
                market_value_signal=0.0,
                form_signal=0.0,
                availability_signal=0.0,
                news_signal=0.0,
                news_recency_signal=0.0,
                trend_signal=0.0,
                value_opportunity_signal=0.0,
            ),
            RankingThresholds(minimum_market_value=500000, minimum_confidence=0.0),
        )

        player = PlayerRecord(
            "1",
            "Recent Player",
            market_value=600000,
            confidence=1.0,
            reported_at="2026-03-27T12:00:00Z",
            signals={},
        )

        ranked = service.rank([player])

        self.assertEqual(len(ranked), 1)
        self.assertIn("news_recency_signal", ranked[0].normalized_signals)
        self.assertEqual(ranked[0].score, 0.0)
        self.assertGreater(ranked[0].normalized_signals["news_recency_signal"], 0.0)


if __name__ == "__main__":
    unittest.main()
