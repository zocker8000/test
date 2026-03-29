import re
from typing import List, Optional

from kickbase.bot.models import PlayerRecord

from .base import BaseSourceClient


class BundesligaRosterSourceClient(BaseSourceClient):
    source_name = "bundesliga_roster_source"

    def __init__(self, endpoint_url: str = "https://www.bundesliga.com/en/bundesliga/player", timeout_seconds: float = 20.0) -> None:
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds

    def fetch(self) -> List[PlayerRecord]:
        html = self._load_html()
        return self._parse_players(html)

    def _load_html(self) -> str:
        return self._load_url_text(self.endpoint_url)

    def _timeout_seconds(self) -> float:
        return self.timeout_seconds

    def _parse_players(self, html: str) -> List[PlayerRecord]:
        club_pattern = re.compile(r'<h2[^>]*>(?P<club>[^<]+)</h2></mat-panel-title>', re.S)
        position_pattern = re.compile(r'<div class="col-12 position">(?P<position>[^<]+)</div>', re.S)
        player_pattern = re.compile(
            r'href="/en/bundesliga/player/(?P<slug>[^"#]+)"[^>]*jsaction="click:;"><div[^>]*class="playercard-wrapper">.*?alt="(?P<name>[^"]+)"',
            re.S,
        )

        club_matches = list(club_pattern.finditer(html))
        players: List[PlayerRecord] = []
        for index, club_match in enumerate(club_matches):
            club = club_match.group("club").strip()
            start = club_match.end()
            end = club_matches[index + 1].start() if index + 1 < len(club_matches) else len(html)
            club_chunk = html[start:end]

            current_position: Optional[str] = None
            token_pattern = re.compile(
                r'<div class="col-12 position">(?P<position>[^<]+)</div>|href="/en/bundesliga/player/(?P<slug>[^"#]+)"[^>]*jsaction="click:;"><div[^>]*class="playercard-wrapper">.*?alt="(?P<name>[^"]+)"',
                re.S,
            )
            for token in token_pattern.finditer(club_chunk):
                position = token.group("position")
                if position:
                    current_position = position.strip()
                    continue

                slug = token.group("slug")
                name = token.group("name")
                if not slug or not name:
                    continue
                players.append(
                    PlayerRecord(
                        player_id=slug.strip(),
                        name=name.strip(),
                        club=club,
                        position=current_position,
                        reported_at=None,
                        confidence=1.0,
                    )
                )

        return players
