import unittest

from kickbase.bot.models import PlayerRecord, RankingThresholds, RankingWeights
from kickbase.bot.ranking import RankingService


class FilteringTests(unittest.TestCase):
    def test_filters_market_value_below_or_equal_threshold_and_low_confidence(self) -> None:
        service = RankingService(
            RankingWeights(),
            RankingThresholds(minimum_market_value=500000, minimum_confidence=0.4),
        )

        players = [
            PlayerRecord("1", "Below Market", market_value=499999, confidence=1.0, signals={}),
            PlayerRecord("2", "At Market", market_value=500000, confidence=1.0, signals={}),
            PlayerRecord("3", "Low Confidence", market_value=600000, confidence=0.39, signals={}),
            PlayerRecord("4", "Eligible", market_value=600000, confidence=0.5, signals={}),
        ]

        eligible = service.filter_eligible_players(players)

        self.assertEqual([player.player_id for player in eligible], ["4"])


if __name__ == "__main__":
    unittest.main()
