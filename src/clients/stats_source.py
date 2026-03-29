from typing import List

from kickbase.bot.models import PlayerRecord

from .base import BaseSourceClient


class StatsSourceClient(BaseSourceClient):
    source_name = "player_stats_source"

    def fetch(self) -> List[PlayerRecord]:
        return []

