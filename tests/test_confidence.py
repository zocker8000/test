import unittest

from kickbase.bot.ingestion import IngestionService
from kickbase.bot.models import PlayerRecord


class ConfidenceTests(unittest.TestCase):
    def test_merged_confidence_reflects_source_agreement_and_completeness(self) -> None:
        service = IngestionService()

        records = [
            PlayerRecord("", "Michael Olise", club="FC Bayern München", confidence=0.4, signals={}),
            PlayerRecord(
                "",
                "Michael Olise",
                club="Bayern Munich",
                position="FW",
                market_value=140000000,
                confidence=0.9,
                signals={"market_value_signal": 1.0},
            ),
        ]

        merged = service.merge_player_records(records)

        self.assertEqual(len(merged), 1)
        self.assertGreaterEqual(merged[0].confidence, 0.8)
        self.assertEqual(merged[0].club, "bayern münchen")


if __name__ == "__main__":
    unittest.main()
