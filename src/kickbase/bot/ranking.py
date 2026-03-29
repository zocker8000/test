from typing import Iterable, List

from .models import PlayerRecord, RankingThresholds, RankingWeights, ScoredPlayer
from .news_relevance import news_recency_signal
from .scoring import ScoreCalculator


class RankingService:
    def __init__(self, weights: RankingWeights, thresholds: RankingThresholds) -> None:
        self.thresholds = thresholds
        self.scorer = ScoreCalculator(weights)

    def filter_eligible_players(self, players: Iterable[PlayerRecord]) -> List[PlayerRecord]:
        eligible = []
        for player in players:
            if player.market_value is None:
                continue
            if player.market_value <= self.thresholds.minimum_market_value:
                continue
            if player.confidence < self.thresholds.minimum_confidence:
                continue
            eligible.append(player)
        return eligible

    def rank(self, players: Iterable[PlayerRecord]) -> List[ScoredPlayer]:
        scored = []
        for player in self.filter_eligible_players(players):
            signals = dict(player.signals)
            if "market_value_signal" not in signals and player.market_value is not None:
                signals["market_value_signal"] = self._market_value_signal(player.market_value)
            if "news_recency_signal" not in signals and player.reported_at:
                signals["news_recency_signal"] = news_recency_signal(player.reported_at)
            score = self.scorer.score(signals)
            scored.append(
                ScoredPlayer(
                    player=player,
                    score=score,
                    normalized_signals=self.scorer.normalized_signals(signals),
                )
            )
        scored.sort(
            key=lambda item: (
                -item.score,
                -(item.player.market_value or 0),
                item.player.name.casefold(),
            )
        )
        return scored

    @staticmethod
    def _market_value_signal(market_value: int) -> float:
        return max(0.0, min(1.0, market_value / 100_000_000))
