import re
from typing import Dict, List, Optional

from kickbase.bot.models import PlayerRecord

from .base import BaseSourceClient


class BundesligaStatsSourceClient(BaseSourceClient):
    source_name = "bundesliga_stats_source"

    def __init__(
        self,
        endpoint_url: str = "https://www.bundesliga.com/en/bundesliga/stats/players/goals/cards",
        timeout_seconds: float = 20.0,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds

    def fetch(self) -> List[PlayerRecord]:
        html = self._load_html()
        return self._parse_stats(html)

    def _load_html(self) -> str:
        return self._load_url_text(self.endpoint_url)

    def _timeout_seconds(self) -> float:
        return self.timeout_seconds

    def _parse_stats(self, html: str) -> List[PlayerRecord]:
        title_pattern = re.compile(r'<h2[^>]*class="title"[^>]*>(?P<category>[^<]+)</h2>', re.S)
        row_pattern = re.compile(
            r'<a[^>]*class="playerRow[^"]*"[^>]*href="/en/bundesliga/player/(?P<slug>[^"#]+)#stats"[^>]*>.*?'
            r'<span[^>]*class="rank">(?P<rank>[^<]*)</span>.*?'
            r'alt="(?P<name>[^"]+)".*?'
            r'<span[^>]*class="clubName d-none">(?P<club>[^<]+)</span>.*?'
            r'<span[^>]*class="value shortText">(?P<value>[^<]+)</span>',
            re.S,
        )

        sections = list(title_pattern.finditer(html))
        players: Dict[str, PlayerRecord] = {}
        for index, title_match in enumerate(sections):
            category = title_match.group("category").strip().casefold()
            start = title_match.end()
            end = sections[index + 1].start() if index + 1 < len(sections) else len(html)
            section = html[start:end]

            signal_name = self._category_to_signal(category)
            if signal_name is None:
                continue

            for match in row_pattern.finditer(section):
                slug = match.group("slug").strip()
                name = match.group("name").strip()
                club = match.group("club").strip()
                rank = match.group("rank").strip()
                value = match.group("value").strip()
                score = self._score_from_rank(rank, value)
                existing = players.get(slug)
                if existing is None:
                    existing = PlayerRecord(
                        player_id=slug,
                        name=name,
                        club=club,
                        reported_at=None,
                        confidence=0.9,
                        signals={signal_name: score},
                    )
                else:
                    signals = dict(existing.signals)
                    signals[signal_name] = max(signals.get(signal_name, 0.0), score)
                    existing = PlayerRecord(
                        player_id=existing.player_id,
                        name=existing.name,
                        club=existing.club,
                        position=existing.position,
                        market_value=existing.market_value,
                        reported_at=existing.reported_at,
                        confidence=max(existing.confidence, 0.9),
                        signals=signals,
                    )
                players[slug] = existing

        return list(players.values())

    @staticmethod
    def _category_to_signal(category: str) -> Optional[str]:
        if category == "goals":
            return "form_signal"
        if category == "assists":
            return "trend_signal"
        if category == "top speed (km/h)":
            return "value_opportunity_signal"
        return None

    @staticmethod
    def _score_from_rank(rank: str, value: str) -> float:
        if value:
            try:
                numeric = float(value.replace(",", "."))
                return max(0.0, min(1.0, numeric / 50.0))
            except ValueError:
                pass
        if rank and rank.isdigit():
            return max(0.0, 1.0 - (int(rank) - 1) / 20.0)
        return 0.0
