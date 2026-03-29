import unittest

from kickbase.bot.ingestion import IngestionService
from kickbase.bot.models import PlayerRecord, RankingThresholds, RankingWeights
from kickbase.bot.ranking import RankingService


class RankingConsistencyTests(unittest.TestCase):
    def test_ranking_is_stable_across_input_order(self) -> None:
        ingestion = IngestionService()
        ranking = RankingService(
            RankingWeights(
                market_value_signal=0.2,
                form_signal=0.2,
                availability_signal=0.25,
                news_signal=0.1,
                news_recency_signal=0.0,
                trend_signal=0.15,
                value_opportunity_signal=0.1,
            ),
            RankingThresholds(minimum_market_value=500000, minimum_confidence=0.4),
        )

        records = [
            PlayerRecord(
                "roster-1",
                "Jamal Musiala",
                club="FC Bayern München",
                position="MF",
                market_value=12000000,
                confidence=0.8,
                signals={"form_signal": 0.6},
            ),
            PlayerRecord(
                "transfermarkt-2",
                "Jamal Musiala",
                club="Bayern Munich",
                position="MF",
                market_value=13000000,
                confidence=0.9,
                signals={"market_value_signal": 1.0},
            ),
            PlayerRecord(
                "stats-3",
                "Serhou Guirassy",
                club="Borussia Dortmund",
                position="FW",
                market_value=11000000,
                confidence=0.9,
                signals={"form_signal": 0.7},
            ),
        ]

        forward = ranking.rank(ingestion.merge_player_records(records))
        reverse = ranking.rank(ingestion.merge_player_records(list(reversed(records))))

        self.assertEqual([item.player.name for item in forward], [item.player.name for item in reverse])
        self.assertEqual([item.score for item in forward], [item.score for item in reverse])
        self.assertEqual(len(forward), 2)


if __name__ == "__main__":
    unittest.main()
