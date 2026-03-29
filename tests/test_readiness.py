import unittest

from kickbase.bot.readiness import assess_pipeline_readiness


class ReadinessTests(unittest.TestCase):
    def test_reports_ready_when_players_and_sources_are_healthy(self) -> None:
        report = assess_pipeline_readiness(
            source_player_counts={"roster": 50, "market": 50},
            players_collected=100,
            players_eligible=80,
            sources_used=2,
            sources_failed=0,
        )

        self.assertEqual(report.status, "ready")
        self.assertEqual(report.warnings, [])

    def test_reports_degraded_when_a_source_fails(self) -> None:
        report = assess_pipeline_readiness(
            source_player_counts={"roster": 50, "market": 0},
            players_collected=50,
            players_eligible=40,
            sources_used=2,
            sources_failed=1,
        )

        self.assertEqual(report.status, "degraded")
        self.assertIn("one_or_more_sources_failed", report.warnings)

    def test_reports_blocked_when_no_players_are_collected(self) -> None:
        report = assess_pipeline_readiness(
            source_player_counts={},
            players_collected=0,
            players_eligible=0,
            sources_used=0,
            sources_failed=0,
        )

        self.assertEqual(report.status, "blocked")
        self.assertIn("no_sources_configured", report.warnings)
        self.assertIn("no_players_collected", report.warnings)


if __name__ == "__main__":
    unittest.main()
