import unittest

from kickbase.bot.ingestion import IngestionService, SourceValidationError
from kickbase.bot.models import PlayerRecord


class IngestionTests(unittest.TestCase):
    def test_collect_players_skips_failed_sources(self) -> None:
        service = IngestionService()

        class FailingSource:
            source_name = "failing_source"

            def fetch(self):
                raise RuntimeError("boom")

        class WorkingSource:
            source_name = "working_source"

            def fetch(self):
                return [PlayerRecord("1", "Working Player", market_value=600000, confidence=1.0, signals={})]

        result = service.collect_players([FailingSource(), WorkingSource()])

        self.assertEqual(result.source_names, ["failing_source", "working_source"])
        self.assertEqual(result.failed_sources, ["failing_source"])
        self.assertEqual([player.player_id for player in result.players], ["1"])

    def test_validates_source_registry_shape(self) -> None:
        service = IngestionService()

        validated = service.validate_source_registry(
            {
                "player_pool_sources": [{"name": "bundesliga_roster_source", "enabled": True, "priority": 1}],
                "market_value_sources": [{"name": "kickbase_market_value_source", "enabled": True, "priority": 1}],
                "news_sources": [{"name": "football_news_source", "enabled": True, "priority": 1}],
                "stats_sources": [{"name": "player_stats_source", "enabled": True, "priority": 1}],
            }
        )

        self.assertEqual(validated["player_pool_sources"][0].name, "bundesliga_roster_source")

    def test_rejects_invalid_source_registry_entry(self) -> None:
        service = IngestionService()

        with self.assertRaises(SourceValidationError):
            service.validate_source_registry(
                {
                    "player_pool_sources": [{"name": "", "enabled": True, "priority": 1}],
                    "market_value_sources": [],
                    "news_sources": [],
                    "stats_sources": [],
                }
            )

    def test_matches_players_by_normalized_name_and_club(self) -> None:
        service = IngestionService()

        records = [
            PlayerRecord("roster-1", "  Jamal   Musiala ", club="FC Bayern München", position="MF", signals={}),
            PlayerRecord(
                "transfermarkt-99",
                "jamal musiala",
                club="Bayern Munich",
                position="MF",
                market_value=12000000,
                confidence=0.9,
                signals={"form_signal": 0.8},
            ),
            PlayerRecord("stats-3", "Different Player", club="Bayern München", signals={}),
        ]

        matches = service.find_player_matches(records)
        merged = service.merge_player_records(records)

        self.assertEqual(len(matches), 2)
        match_map = {match.match_key: match for match in matches}
        self.assertIn("nameclub::jamal musiala::bayern münchen", match_map)
        self.assertIn("nameclub::different player::bayern münchen", match_map)
        self.assertEqual(match_map["nameclub::jamal musiala::bayern münchen"].canonical.name, "jamal musiala")
        self.assertEqual(match_map["nameclub::different player::bayern münchen"].canonical.name, "Different Player")
        self.assertEqual([player.name for player in merged], ["jamal musiala", "Different Player"])

    def test_merges_clubless_record_when_name_is_unambiguous(self) -> None:
        service = IngestionService()

        records = [
            PlayerRecord("", "Jamal Musiala", club="Bayern München", position="MF", signals={}),
            PlayerRecord(
                "",
                " Jamal   Musiala ",
                club=None,
                position="MF",
                market_value=11000000,
                confidence=0.8,
                signals={"trend_signal": 0.7},
            ),
        ]

        matches = service.find_player_matches(records)
        merged = service.merge_player_records(records)

        self.assertEqual(len(matches), 1)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].club, "bayern münchen")
        self.assertEqual(merged[0].market_value, 11000000)
        self.assertGreaterEqual(merged[0].confidence, 0.8)

    def test_does_not_merge_same_name_across_different_clubs_without_identifier(self) -> None:
        service = IngestionService()

        records = [
            PlayerRecord("", "Max Mustermann", club="Club A", signals={}),
            PlayerRecord("", "Max Mustermann", club="Club B", signals={}),
        ]

        matches = service.find_player_matches(records)
        merged = service.merge_player_records(records)

        self.assertEqual(len(matches), 2)
        self.assertEqual(len(merged), 2)
        self.assertEqual({player.club for player in merged}, {"club a", "club b"})


if __name__ == "__main__":
    unittest.main()
