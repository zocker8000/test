import json
import tempfile
import unittest
from pathlib import Path

from clients.json_source import JsonFeedSourceClient


class JsonSourceTests(unittest.TestCase):
    def test_fetches_player_records_from_json_feed(self) -> None:
        payload = [
            {
                "player_id": "42",
                "name": "Test Player",
                "club": "Test FC",
                "position": "MF",
                "market_value": 1234567,
                "reported_at": "2026-03-28T10:15:00Z",
                "confidence": 0.88,
                "signals": {"form_signal": 0.5},
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "feed.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            client = JsonFeedSourceClient(endpoint_url=path.as_uri())
            players = client.fetch()

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0].player_id, "42")
        self.assertEqual(players[0].name, "Test Player")
        self.assertEqual(players[0].club, "Test FC")
        self.assertEqual(players[0].market_value, 1234567)
        self.assertEqual(players[0].reported_at, "2026-03-28T10:15:00Z")

    def test_supports_field_aliases_and_wrapped_lists(self) -> None:
        payload = {
            "players": [
                {
                    "id": "77",
                    "title": "Alias Player",
                    "team": "Alias FC",
                    "role": "DF",
                    "value": 987654,
                    "reported_at": "2026-03-28T09:00:00Z",
                    "confidence": 0.75,
                    "signals": {"trend_signal": 0.6},
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "feed.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            client = JsonFeedSourceClient(
                endpoint_url=path.as_uri(),
                player_list_key="players",
                field_map={
                    "player_id": "id",
                    "name": "title",
                    "club": "team",
                    "position": "role",
                    "market_value": "value",
                },
            )
            players = client.fetch()

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0].player_id, "77")
        self.assertEqual(players[0].name, "Alias Player")
        self.assertEqual(players[0].club, "Alias FC")
        self.assertEqual(players[0].position, "DF")
        self.assertEqual(players[0].market_value, 987654)
        self.assertEqual(players[0].reported_at, "2026-03-28T09:00:00Z")


if __name__ == "__main__":
    unittest.main()
