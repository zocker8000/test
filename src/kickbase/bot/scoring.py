from typing import Dict, Mapping

from .models import RankingWeights


class ScoreCalculator:
    def __init__(self, weights: RankingWeights) -> None:
        self.weights = weights

    def score(self, signals: Mapping[str, float]) -> float:
        weighted_sum = 0.0
        for name, weight in self.weights_as_dict().items():
            weighted_sum += self._clamp(signals.get(name, 0.0)) * weight
        return round(weighted_sum, 6)

    def normalized_signals(self, signals: Mapping[str, float]) -> Dict[str, float]:
        return {name: self._clamp(value) for name, value in signals.items()}

    def weights_as_dict(self) -> Dict[str, float]:
        return {
            "market_value_signal": self.weights.market_value_signal,
            "form_signal": self.weights.form_signal,
            "availability_signal": self.weights.availability_signal,
            "news_signal": self.weights.news_signal,
            "news_recency_signal": self.weights.news_recency_signal,
            "trend_signal": self.weights.trend_signal,
            "value_opportunity_signal": self.weights.value_opportunity_signal,
        }

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))
