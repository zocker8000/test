import unittest

from kickbase.bot.models import PlayerRecord, RankingThresholds, RankingWeights
from kickbase.bot.ranking import RankingService


class ScoringTests(unittest.TestCase):
    def test_ranking_uses_deterministic_weighted_score(self) -> None:
        service = RankingService(
            RankingWeights(
                market_value_signal=0.2,
                form_signal=0.2,
                availability_signal=0.25,
                news_signal=0.1,
                trend_signal=0.15,
                value_opportunity_signal=0.1,
            ),
            RankingThresholds(minimum_market_value=500000, minimum_confidence=0.0),
        )

        players = [
            PlayerRecord(
                "1",
                "Player A",
                market_value=700000,
                confidence=1.0,
                signals={"market_value_signal": 1.0, "form_signal": 0.5},
            ),
            PlayerRecord(
                "2",
                "Player B",
                market_value=800000,
                confidence=1.0,
                signals={"market_value_signal": 1.0, "form_signal": 0.25},
            ),
        ]

        ranked = service.rank(players)

        self.assertEqual([item.player.player_id for item in ranked], ["1", "2"])
        self.assertAlmostEqual(ranked[0].score, 0.3)


if __name__ == "__main__":
    unittest.main()
