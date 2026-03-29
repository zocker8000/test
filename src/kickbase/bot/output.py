import json
import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .models import ScoredPlayer


def build_ranking_payload(
    ranked_players: Iterable[ScoredPlayer],
    *,
    sources_used: int = 0,
    players_collected: int = 0,
    sources_failed: int = 0,
    players_eligible: int = 0,
    source_player_counts: Optional[Dict[str, int]] = None,
    pipeline_status: str = "unknown",
    pipeline_warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    ranked_list: List[Dict[str, Any]] = []
    for item in ranked_players:
        ranked_list.append(
            {
                "player_id": item.player.player_id,
                "name": item.player.name,
                "club": item.player.club,
                "position": item.player.position,
                "market_value": item.player.market_value,
                "reported_at": item.player.reported_at,
                "score": item.score,
                "signals": item.normalized_signals,
            }
        )

    return {
        "sources_used": sources_used,
        "sources_failed": sources_failed,
        "players_collected": players_collected,
        "players_eligible": players_eligible,
        "players_ranked": len(ranked_list),
        "source_player_counts": source_player_counts or {},
        "pipeline_status": pipeline_status,
        "pipeline_warnings": pipeline_warnings or [],
        "ranked_players": ranked_list,
    }


def build_ranking_rows(ranked_players: Iterable[ScoredPlayer]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in ranked_players:
        rows.append(
            {
                "player_id": item.player.player_id,
                "name": item.player.name,
                "club": item.player.club or "",
                "position": item.player.position or "",
                "market_value": item.player.market_value or "",
                "reported_at": item.player.reported_at or "",
                "score": item.score,
            }
        )
    return rows


def write_json_output(path: str, payload: Dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def write_csv_output(path: str, ranked_players: Iterable[ScoredPlayer]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_ranking_rows(ranked_players)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["player_id", "name", "club", "position", "market_value", "reported_at", "score"],
        )
        writer.writeheader()
        writer.writerows(rows)
    return output_path
