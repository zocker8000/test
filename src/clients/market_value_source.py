from typing import List

from kickbase.bot.models import PlayerRecord

from .base import BaseSourceClient


class MarketValueSourceClient(BaseSourceClient):
    source_name = "kickbase_market_value_source"

    def fetch(self) -> List[PlayerRecord]:
        return []

