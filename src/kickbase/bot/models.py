from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional


@dataclass(frozen=True)
class RankingWeights:
    market_value_signal: float = 0.20
    form_signal: float = 0.20
    availability_signal: float = 0.25
    news_signal: float = 0.10
    news_recency_signal: float = 0.00
    trend_signal: float = 0.15
    value_opportunity_signal: float = 0.10

    @classmethod
    def from_mapping(cls, values: Mapping[str, float]) -> "RankingWeights":
        return cls(
            market_value_signal=float(values.get("market_value_signal", cls.market_value_signal)),
            form_signal=float(values.get("form_signal", cls.form_signal)),
            availability_signal=float(values.get("availability_signal", cls.availability_signal)),
            news_signal=float(values.get("news_signal", cls.news_signal)),
            news_recency_signal=float(values.get("news_recency_signal", cls.news_recency_signal)),
            trend_signal=float(values.get("trend_signal", cls.trend_signal)),
            value_opportunity_signal=float(values.get("value_opportunity_signal", cls.value_opportunity_signal)),
        )


@dataclass(frozen=True)
class RankingThresholds:
    minimum_market_value: int = 500000
    minimum_confidence: float = 0.40

    @classmethod
    def from_mapping(cls, values: Mapping[str, float]) -> "RankingThresholds":
        return cls(
            minimum_market_value=int(values.get("minimum_market_value", cls.minimum_market_value)),
            minimum_confidence=float(values.get("minimum_confidence", cls.minimum_confidence)),
        )


@dataclass(frozen=True)
class PlayerRecord:
    player_id: str
    name: str
    club: Optional[str] = None
    position: Optional[str] = None
    market_value: Optional[int] = None
    reported_at: Optional[str] = None
    confidence: float = 0.0
    signals: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoredPlayer:
    player: PlayerRecord
    score: float
    normalized_signals: Dict[str, float] = field(default_factory=dict)
