import json
import tempfile
import unittest
from pathlib import Path

from kickbase.bot.models import PlayerRecord, RankingThresholds, RankingWeights
from kickbase.bot.output import build_ranking_payload, write_csv_output, write_json_output
from kickbase.bot.ranking import RankingService


class OutputTests(unittest.TestCase):
    def test_writes_ranking_payload(self) -> None:
        service = RankingService(
            RankingWeights(
                market_value_signal=0.2,
                form_signal=0.2,
                availability_signal=0.25,
                news_signal=0.1,
                news_recency_signal=0.0,
                trend_signal=0.15,
                value_opportunity_signal=0.1,
            ),
            RankingThresholds(minimum_market_value=500000, minimum_confidence=0.0),
        )

        ranked = service.rank(
            [
                PlayerRecord(
                    "1",
                    "Output Player",
                    market_value=700000,
                    confidence=1.0,
                    signals={"market_value_signal": 1.0},
                )
            ]
        )
        payload = build_ranking_payload(ranked, sources_used=3, players_collected=1, sources_failed=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_json_output(str(Path(tmpdir) / "ranking.json"), payload)
            loaded = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(loaded["sources_used"], 3)
        self.assertEqual(loaded["sources_failed"], 1)
        self.assertEqual(loaded["players_collected"], 1)
        self.assertEqual(loaded["players_eligible"], 0)
        self.assertEqual(loaded["pipeline_status"], "unknown")
        self.assertEqual(loaded["players_ranked"], 1)
        self.assertEqual(loaded["ranked_players"][0]["name"], "Output Player")

    def test_writes_ranking_csv(self) -> None:
        service = RankingService(
            RankingWeights(),
            RankingThresholds(minimum_market_value=500000, minimum_confidence=0.0),
        )

        ranked = service.rank(
            [
                PlayerRecord(
                    "1",
                    "CSV Player",
                    club="CSV FC",
                    position="MF",
                    market_value=700000,
                    reported_at="2026-03-28T12:00:00Z",
                    confidence=1.0,
                    signals={"market_value_signal": 1.0},
                )
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_csv_output(str(Path(tmpdir) / "ranking.csv"), ranked)
            content = path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(content[0], "player_id,name,club,position,market_value,reported_at,score")
        self.assertIn("CSV Player", content[1])


if __name__ == "__main__":
    unittest.main()
