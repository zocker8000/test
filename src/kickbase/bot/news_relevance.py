from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def parse_reported_at(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def news_recency_signal(
    reported_at: Optional[str],
    now: Optional[datetime] = None,
    half_life_hours: float = 72.0,
) -> float:
    published_at = parse_reported_at(reported_at)
    if published_at is None:
        return 0.0

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    age_hours = (current_time - published_at).total_seconds() / 3600.0
    if age_hours <= 0:
        return 1.0
    if half_life_hours <= 0:
        return 0.0

    score = max(0.0, 1.0 - (age_hours / half_life_hours))
    return round(score, 6)

