import json
import re
from pathlib import Path
from typing import List, Optional

from kickbase.bot.models import PlayerRecord

from .base import BaseSourceClient


class TransfermarktMarketValuesSourceClient(BaseSourceClient):
    source_name = "transfermarkt_market_values_source"

    def __init__(
        self,
        endpoint_url: str = "https://www.transfermarkt.com/bundesliga/marktwertaenderungen/wettbewerb/L1/saison_id/2025",
        page_numbers: Optional[List[int]] = None,
        snapshot_path: str = "config/snapshots/transfermarkt_market_values_snapshot.json",
        timeout_seconds: float = 20.0,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.page_numbers = page_numbers or [1, 2, 3, 4]
        self.snapshot_path = snapshot_path
        self.timeout_seconds = timeout_seconds

    def fetch(self) -> List[PlayerRecord]:
        players_by_id = {}
        loaded_pages = 0
        last_error: Optional[Exception] = None
        for page_number in self.page_numbers:
            try:
                html = self._load_html(page_number)
                loaded_pages += 1
            except Exception as exc:
                last_error = exc
                continue
            for player in self._parse_market_values(html):
                current = players_by_id.get(player.player_id)
                if current is None or (player.market_value or 0) > (current.market_value or 0):
                    players_by_id[player.player_id] = player
        if loaded_pages == 0 and last_error is not None:
            snapshot_players = self._load_snapshot_players()
            if snapshot_players:
                return snapshot_players
            raise RuntimeError("failed to load transfermarkt market value pages") from last_error

        if players_by_id:
            return list(players_by_id.values())

        snapshot_players = self._load_snapshot_players()
        return snapshot_players if snapshot_players else []

    def _load_html(self, page_number: int) -> str:
        url = self.endpoint_url if page_number == 1 else f"{self.endpoint_url}?page={page_number}"
        return self._load_url_text(url, extra_cache_key=f"page={page_number}")

    def _timeout_seconds(self) -> float:
        return self.timeout_seconds

    def _load_snapshot_players(self) -> List[PlayerRecord]:
        snapshot_file = Path(self.snapshot_path)
        if not snapshot_file.exists():
            return []
        try:
            raw = snapshot_file.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except Exception:
            return []
        if not isinstance(payload, list):
            return []

        players: List[PlayerRecord] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            player_id = item.get("player_id")
            name = item.get("name")
            club = item.get("club")
            market_value = item.get("market_value")
            if not isinstance(player_id, str) or not player_id.strip():
                continue
            if not isinstance(name, str) or not name.strip():
                continue
            if not isinstance(market_value, int):
                continue
            players.append(
                PlayerRecord(
                    player_id=player_id.strip(),
                    name=name.strip(),
                    club=club.strip() if isinstance(club, str) and club.strip() else None,
                    position=item.get("position") if isinstance(item.get("position"), str) else None,
                    market_value=market_value,
                    reported_at=item.get("reported_at") if isinstance(item.get("reported_at"), str) else None,
                    confidence=float(item.get("confidence", 1.0)),
                    signals={
                        key: float(value)
                        for key, value in dict(item.get("signals", {})).items()
                        if isinstance(key, str)
                    }
                    if isinstance(item.get("signals"), dict)
                    else {},
                )
            )
        return players

    def _parse_market_values(self, html: str) -> List[PlayerRecord]:
        players_by_id = {}
        for player in self._parse_table_rows(html) + self._parse_compact_rows(html):
            current = players_by_id.get(player.player_id)
            if current is None or (player.market_value or 0) > (current.market_value or 0):
                players_by_id[player.player_id] = player
        return list(players_by_id.values())

    def _parse_table_rows(self, html: str) -> List[PlayerRecord]:
        cutoff = html.find("Latest market value updates")
        top_section = html[:cutoff] if cutoff != -1 else html
        row_chunks = [
            chunk
            for chunk in re.split(r'(?=<tr class="(?:odd|even)">)', top_section)
            if chunk.startswith('<tr class="')
        ]

        players: List[PlayerRecord] = []
        for row_html in row_chunks:
            player_match = re.search(
                r'<a title="(?P<name>[^"]+)" href="/(?P<slug>[^"/]+)/profil/spieler/(?P<player_id>\d+)">(?P=name)</a>',
                row_html,
                re.S,
            )
            club_match = re.search(r'<a title="(?P<club>[^"]+)" href="[^"]*/startseite/verein/[^"]+">', row_html, re.S)
            market_value_match = re.search(
                r'<td class="rechts hauptlink">(?:<a[^>]*>)?€(?P<market_value>[^<]+)(?:</a>)?',
                row_html,
                re.S,
            )
            position_match = re.search(r'<tr>\s*<td>(?P<position>[^<]+)</td>\s*</tr>', row_html, re.S)

            if not player_match or not club_match or not market_value_match:
                continue

            players.append(
                PlayerRecord(
                    player_id=player_match.group("slug").strip(),
                    name=player_match.group("name").strip(),
                    club=club_match.group("club").strip(),
                    position=position_match.group("position").strip() if position_match else None,
                    market_value=self._parse_market_value(market_value_match.group("market_value")),
                    reported_at=None,
                    confidence=1.0,
                    signals={},
                )
            )
        return players

    def _parse_compact_rows(self, html: str) -> List[PlayerRecord]:
        player_pattern = re.compile(
            r'<a title="(?P<name>[^"]+)" href="/(?P<slug>[^"/]+)/profil/spieler/(?P<player_id>\d+)">(?P=name)</a>',
            re.S,
        )
        players: List[PlayerRecord] = []
        for match in player_pattern.finditer(html):
            segment = html[match.start() : min(len(html), match.start() + 1800)]
            market_value_match = re.search(r'€(?P<market_value>[\d.,]+(?:[mk])?)', segment, re.S)
            club_match = re.search(
                r'(?:<a title="(?P<club_anchor>[^"]+)" href="[^"]*/startseite/verein/[^"]+">|'
                r'<img[^>]*(?:alt|title)="(?P<club_image>[^"]+)"[^>]*>)',
                segment,
                re.S,
            )
            if not market_value_match or not club_match:
                continue

            position = self._extract_position(segment)
            club = club_match.group("club_anchor") or club_match.group("club_image")
            players.append(
                PlayerRecord(
                    player_id=match.group("slug").strip(),
                    name=match.group("name").strip(),
                    club=club.strip() if club else None,
                    position=position,
                    market_value=self._parse_market_value(market_value_match.group("market_value")),
                    reported_at=None,
                    confidence=1.0,
                    signals={},
                )
            )
        return players

    @staticmethod
    def _extract_position(segment: str) -> Optional[str]:
        patterns = [
            r'</a>\s*(?P<position>Goalkeeper|Sweeper|Centre-Back|Left-Back|Right-Back|Defensive Midfield|Central Midfield|Right Midfield|Left Midfield|Attacking Midfield|Left Winger|Right Winger|Second Striker|Centre-Forward|Goalkeepers|Defenders|Midfielders|Strikers)\s*<',
            r'<tr>\s*<td>(?P<position>[^<]+)</td>\s*</tr>',
            r'<span[^>]*class="playerName"[^>]*>.*?</span>\s*(?P<position>[^<]{2,60})\s*<a title="',
        ]
        for pattern in patterns:
            position_match = re.search(pattern, segment, re.S)
            if position_match:
                return position_match.group("position").strip()
        return None

    @staticmethod
    def _parse_market_value(value: str) -> int:
        cleaned = value.strip().lower().replace(",", ".")
        multiplier = 1
        if cleaned.endswith("m"):
            multiplier = 1_000_000
            cleaned = cleaned[:-1]
        elif cleaned.endswith("k"):
            multiplier = 1_000
            cleaned = cleaned[:-1]
        return int(float(cleaned) * multiplier)
