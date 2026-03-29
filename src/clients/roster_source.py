from typing import List

from kickbase.bot.models import PlayerRecord

from .base import BaseSourceClient


class RosterSourceClient(BaseSourceClient):
    source_name = "bundesliga_roster_source"

    def fetch(self) -> List[PlayerRecord]:
        return []

