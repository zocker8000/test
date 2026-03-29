import unittest

from clients.bundesliga_roster_source import BundesligaRosterSourceClient
from clients.bundesliga_stats_source import BundesligaStatsSourceClient
from clients.transfermarkt_source import TransfermarktMarketValuesSourceClient


class RealSourceParserTests(unittest.TestCase):
    def test_parses_bundesliga_roster_html(self) -> None:
        html = """
        <h2>FC Bayern München</h2></mat-panel-title>
        <div class="row"><div class="col-12 position">Goalkeepers</div>
        <div class="col-12 col-md-6 col-lg-4 card"><player-card-simple>
        <a href="/en/bundesliga/player/manuel-neuer" jsaction="click:;"><div class="playercard-wrapper">
        <img alt="Manuel Neuer"><span class="playerNumber">1</span>
        </div></a></player-card-simple></div></div>
        """

        players = BundesligaRosterSourceClient()._parse_players(html)

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0].player_id, "manuel-neuer")
        self.assertEqual(players[0].name, "Manuel Neuer")
        self.assertEqual(players[0].club, "FC Bayern München")
        self.assertEqual(players[0].position, "Goalkeepers")

    def test_parses_multiple_roster_sections(self) -> None:
        html = """
        <h2>FC Bayern München</h2></mat-panel-title>
        <div class="row"><div class="col-12 position">Goalkeepers</div>
        <div class="col-12 col-md-6 col-lg-4 card"><player-card-simple>
        <a href="/en/bundesliga/player/manuel-neuer" jsaction="click:;"><div class="playercard-wrapper">
        <img alt="Manuel Neuer"><span class="playerNumber">1</span>
        </div></a></player-card-simple></div></div>
        <h2>Borussia Dortmund</h2></mat-panel-title>
        <div class="row"><div class="col-12 position">Forwards</div>
        <div class="col-12 col-md-6 col-lg-4 card"><player-card-simple>
        <a href="/en/bundesliga/player/serhou-guirassy" jsaction="click:;"><div class="playercard-wrapper">
        <img alt="Serhou Guirassy"><span class="playerNumber">9</span>
        </div></a></player-card-simple></div></div>
        """

        players = BundesligaRosterSourceClient()._parse_players(html)

        self.assertEqual(len(players), 2)
        self.assertEqual([player.club for player in players], ["FC Bayern München", "Borussia Dortmund"])

    def test_parses_transfermarkt_market_values_html(self) -> None:
        html = """
        <tr class="odd">
        <td class="zentriert">1</td><td><table class="inline-table"><tr><td rowspan="2">
        <img alt="Michael Olise" /></td><td class="hauptlink">
        <a title="Michael Olise" href="/michael-olise/profil/spieler/566723">Michael Olise</a></td></tr>
        <tr><td>Right Winger</td></tr></table></td>
        <td class="zentriert"><a title="Bayern Munich" href="/fc-bayern-munchen/startseite/verein/27/saison_id/2025"></a></td>
        <td class="rechts hauptlink">€140.00m</td></tr>
        """

        players = TransfermarktMarketValuesSourceClient()._parse_market_values(html)

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0].player_id, "michael-olise")
        self.assertEqual(players[0].market_value, 140000000)
        self.assertEqual(players[0].club, "Bayern Munich")

    def test_parses_transfermarkt_update_page_row(self) -> None:
        html = """
        <a title="Michael Olise" href="/michael-olise/profil/spieler/566723">Michael Olise</a>
        Right Winger
        <a title="Bayern Munich" href="/fc-bayern-munchen/startseite/verein/27/saison_id/2025"></a>
        €130.00m
        """

        players = TransfermarktMarketValuesSourceClient()._parse_market_values(html)

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0].player_id, "michael-olise")
        self.assertEqual(players[0].market_value, 130000000)

    def test_parses_transfermarkt_compact_market_value_rows(self) -> None:
        html = """
        <a title="Michael Olise" href="/michael-olise/profil/spieler/566723">Michael Olise</a>
        Right Winger
        <img alt="Bayern Munich" />
        €130.00m
        """

        players = TransfermarktMarketValuesSourceClient()._parse_market_values(html)

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0].player_id, "michael-olise")
        self.assertEqual(players[0].club, "Bayern Munich")
        self.assertEqual(players[0].market_value, 130000000)

    def test_transfermarkt_fetch_raises_when_all_pages_fail(self) -> None:
        client = TransfermarktMarketValuesSourceClient(
            page_numbers=[1],
            snapshot_path="/tmp/does-not-exist-transfermarkt.json",
        )

        def fail(page_number: int) -> str:
            raise RuntimeError("network down")

        client._load_html = fail  # type: ignore[method-assign]

        with self.assertRaises(RuntimeError):
            client.fetch()

    def test_transfermarkt_fetch_uses_snapshot_when_live_pages_fail(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir) / "transfermarkt_market_values_snapshot.json"
            snapshot_path.write_text(
                json.dumps(
                    [
                        {
                            "player_id": "michael-olise",
                            "name": "Michael Olise",
                            "club": "Bayern Munich",
                            "position": "Right Winger",
                            "market_value": 130000000,
                            "confidence": 1.0,
                            "signals": {"market_value_signal": 1.0},
                        }
                    ]
                ),
                encoding="utf-8",
            )

            client = TransfermarktMarketValuesSourceClient(
                page_numbers=[1],
                snapshot_path=snapshot_path.as_posix(),
            )

            def fail(page_number: int) -> str:
                raise RuntimeError("network down")

            client._load_html = fail  # type: ignore[method-assign]

            players = client.fetch()

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0].name, "Michael Olise")
        self.assertEqual(players[0].market_value, 130000000)

    def test_parses_bundesliga_stats_html(self) -> None:
        html = """
        <h2 class="title">Goals</h2>
        <a class="playerRow container-fluid linkActive" href="/en/bundesliga/player/harry-kane#stats">
          <span class="rank">1</span>
          <span class="playerImage"><img alt="Harry Kane"></span>
          <span class="playerName"><span class="first">Harry</span><span class="last"> Kane</span></span>
          <span class="clubName d-none">FC Bayern München</span>
          <span class="value shortText">30</span>
        </a>
        """

        players = BundesligaStatsSourceClient()._parse_stats(html)

        self.assertEqual(len(players), 1)
        self.assertEqual(players[0].player_id, "harry-kane")
        self.assertIn("form_signal", players[0].signals)

    def test_aggregates_multiple_stats_categories_for_same_player(self) -> None:
        html = """
        <h2 class="title">Goals</h2>
        <a class="playerRow container-fluid linkActive" href="/en/bundesliga/player/harry-kane#stats">
          <span class="rank">1</span>
          <span class="playerImage"><img alt="Harry Kane"></span>
          <span class="playerName"><span class="first">Harry</span><span class="last"> Kane</span></span>
          <span class="clubName d-none">FC Bayern München</span>
          <span class="value shortText">30</span>
        </a>
        <h2 class="title">Assists</h2>
        <a class="playerRow container-fluid linkActive" href="/en/bundesliga/player/harry-kane#stats">
          <span class="rank">2</span>
          <span class="playerImage"><img alt="Harry Kane"></span>
          <span class="playerName"><span class="first">Harry</span><span class="last"> Kane</span></span>
          <span class="clubName d-none">FC Bayern München</span>
          <span class="value shortText">12</span>
        </a>
        """

        players = BundesligaStatsSourceClient()._parse_stats(html)

        self.assertEqual(len(players), 1)
        self.assertIn("form_signal", players[0].signals)
        self.assertIn("trend_signal", players[0].signals)
        self.assertEqual(players[0].signals["form_signal"], 0.6)
        self.assertEqual(players[0].signals["trend_signal"], 0.24)


if __name__ == "__main__":
    unittest.main()
