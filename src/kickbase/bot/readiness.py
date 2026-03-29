from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class PipelineReadiness:
    status: str
    warnings: List[str] = field(default_factory=list)
    source_player_counts: Dict[str, int] = field(default_factory=dict)
    players_collected: int = 0
    players_eligible: int = 0
    sources_used: int = 0
    sources_failed: int = 0


def assess_pipeline_readiness(
    *,
    source_player_counts: Dict[str, int],
    players_collected: int,
    players_eligible: int,
    sources_used: int,
    sources_failed: int,
) -> PipelineReadiness:
    warnings: List[str] = []

    if sources_used <= 0:
        warnings.append("no_sources_configured")
    if players_collected <= 0:
        warnings.append("no_players_collected")
    if players_eligible <= 0:
        warnings.append("no_players_above_threshold")
    if sources_failed > 0:
        warnings.append("one_or_more_sources_failed")
    if any(count <= 0 for count in source_player_counts.values()):
        warnings.append("one_or_more_sources_returned_no_players")

    if players_collected <= 0 or players_eligible <= 0:
        status = "blocked"
    elif sources_failed > 0 or any(count <= 0 for count in source_player_counts.values()):
        status = "degraded"
    else:
        status = "ready"

    return PipelineReadiness(
        status=status,
        warnings=warnings,
        source_player_counts=source_player_counts,
        players_collected=players_collected,
        players_eligible=players_eligible,
        sources_used=sources_used,
        sources_failed=sources_failed,
    )
