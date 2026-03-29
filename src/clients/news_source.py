from typing import List

from kickbase.bot.models import PlayerRecord

from .base import BaseSourceClient


class NewsSourceClient(BaseSourceClient):
    source_name = "football_news_source"

    def fetch(self) -> List[PlayerRecord]:
        return []

