import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from clients import (
    BundesligaRosterSourceClient,
    BundesligaStatsSourceClient,
    JsonFeedSourceClient,
    TransfermarktMarketValuesSourceClient,
)

from .config import load_ranking_thresholds, load_ranking_weights
from .ingestion import IngestionService
from .llm import OptionalLLMClient
from .models import PlayerRecord
from .readiness import assess_pipeline_readiness
from .output import build_ranking_payload, write_csv_output, write_json_output
from .ranking import RankingService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bundesliga player ranking bot scaffold")
    parser.add_argument("--config", default="config/ranking_weights.yaml", help="Path to ranking config")
    parser.add_argument("--dry-run", action="store_true", help="Run the scaffold without external ingestion")
    parser.add_argument("--source-url", help="Optional JSON feed URL for a test fetch")
    parser.add_argument("--source-list-key", help="Optional key containing the player list in a JSON object")
    parser.add_argument(
        "--field-map",
        action="append",
        default=[],
        metavar="TARGET=SOURCE",
        help="Map a canonical player field to a JSON field name; may be repeated",
    )
    parser.add_argument("--feeds", default="config/feeds.yaml", help="Path to source feed configuration")
    parser.add_argument("--live", action="store_true", help="Run configured live sources and print ranking results")
    parser.add_argument("--output", default="out/ranking.json", help="Write ranking results to a JSON file")
    return parser


def _parse_field_map(entries: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise ValueError(f"invalid field map entry: {entry}")
        target, source = entry.split("=", 1)
        target = target.strip()
        source = source.strip()
        if not target or not source:
            raise ValueError(f"invalid field map entry: {entry}")
        mapping[target] = source
    return mapping


def _build_source_client(source_config: Dict[str, object]):
    source_type = str(source_config.get("type", "")).strip()
    url = str(source_config.get("url", "")).strip()
    if not source_type or not url:
        raise ValueError("source entries need both type and url")

    if source_type == "bundesliga_roster":
        return BundesligaRosterSourceClient(endpoint_url=url)
    if source_type == "transfermarkt_market_values":
        return TransfermarktMarketValuesSourceClient(endpoint_url=url)
    if source_type == "bundesliga_stats":
        return BundesligaStatsSourceClient(endpoint_url=url)
    if source_type == "json_feed":
        return JsonFeedSourceClient(
            endpoint_url=url,
            player_list_key=source_config.get("player_list_key") or None,
            field_map=source_config.get("field_map") or None,
        )

    raise ValueError(f"unsupported source type: {source_type}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    weights = load_ranking_weights(args.config)
    thresholds = load_ranking_thresholds(args.config)
    ranking_service = RankingService(weights, thresholds)
    ingestion_service = IngestionService()
    llm_client = OptionalLLMClient()

    if args.dry_run:
        demo_players = [
            PlayerRecord(
                player_id="demo-1",
                name="Demo Player",
                club="Demo FC",
                position="MF",
                market_value=600000,
                confidence=1.0,
                signals={"market_value_signal": 1.0},
            )
        ]
        ranked = ranking_service.rank(demo_players)
        display_limit = min(len(ranked), 100)
        displayed_ranked = ranked[:display_limit]
        payload = build_ranking_payload(
            displayed_ranked,
            sources_used=0,
            players_collected=len(demo_players),
            sources_failed=0,
            players_eligible=len(ranked),
            source_player_counts={"demo": len(demo_players)},
            pipeline_status="ready",
            pipeline_warnings=[],
        )
        write_json_output(args.output, payload)
        csv_output = Path(args.output).with_suffix(".csv")
        write_csv_output(str(csv_output), displayed_ranked)
        if llm_client.is_enabled():
            llm_result = llm_client.generate_explanation(displayed_ranked)
            if llm_result is not None:
                llm_output = Path(args.output).with_name("llm_response.json")
                write_json_output(str(llm_output), asdict(llm_result))
                print(f"llm_enabled={llm_result.enabled}")
                print(f"llm_prompt_tokens={llm_result.prompt_tokens}")
                print(f"llm_output={llm_output.as_posix()}")
                if llm_result.error:
                    print(f"warning=llm_request_failed:{llm_result.error}")
        print(f"ranked_players={len(ranked)}")
        print(f"displayed_players={len(displayed_ranked)}")
        if displayed_ranked:
            print(f"top_player={displayed_ranked[0].player.name}")
        print(f"output={args.output}")
        print(f"csv_output={csv_output.as_posix()}")
        return 0

    if args.source_url:
        source_client = JsonFeedSourceClient(
            endpoint_url=args.source_url,
            player_list_key=args.source_list_key,
            field_map=_parse_field_map(args.field_map),
        )
        result = ingestion_service.collect_players([source_client])
        payload = {
            "source": source_client.source_name,
            "players_fetched": len(result.players),
            "pipeline_status": "source_only",
            "pipeline_warnings": result.failed_sources,
            "players": [
                {
                    "player_id": player.player_id,
                    "name": player.name,
                    "club": player.club,
                    "position": player.position,
                    "market_value": player.market_value,
                    "reported_at": player.reported_at,
                    "confidence": player.confidence,
                    "signals": player.signals,
                }
                for player in result.players
            ],
        }
        write_json_output(args.output, payload)
        csv_output = Path(args.output).with_suffix(".csv")
        write_csv_output(str(csv_output), result.players)
        if llm_client.is_enabled():
            llm_result = llm_client.generate_explanation(result.players)
            if llm_result is not None:
                llm_output = Path(args.output).with_name("llm_response.json")
                write_json_output(str(llm_output), asdict(llm_result))
                print(f"llm_enabled={llm_result.enabled}")
                print(f"llm_prompt_tokens={llm_result.prompt_tokens}")
                print(f"llm_output={llm_output.as_posix()}")
                if llm_result.error:
                    print(f"warning=llm_request_failed:{llm_result.error}")
        print(f"source={source_client.source_name}")
        print(f"players_fetched={len(result.players)}")
        print(f"output={args.output}")
        print(f"csv_output={csv_output.as_posix()}")
        for player in result.players[:5]:
            print(f"player={player.name}|club={player.club or ''}|market_value={player.market_value or ''}")
        return 0

    if args.live:
        from .config import load_feed_settings

        feed_settings = load_feed_settings(args.feeds)
        source_entries = feed_settings.get("sources", [])
        source_clients = []
        for entry in source_entries:
            if isinstance(entry, dict) and entry.get("enabled", True):
                source_clients.append(_build_source_client(entry))

        result = ingestion_service.collect_players(source_clients)
        ranked = ranking_service.rank(result.players)
        display_limit = min(len(ranked), 100)
        displayed_ranked = ranked[:display_limit]
        readiness = assess_pipeline_readiness(
            source_player_counts=result.source_player_counts,
            players_collected=len(result.players),
            players_eligible=len(ranked),
            sources_used=len(source_clients),
            sources_failed=len(result.failed_sources),
        )
        payload = build_ranking_payload(
            displayed_ranked,
            sources_used=len(source_clients),
            players_collected=len(result.players),
            sources_failed=len(result.failed_sources),
            players_eligible=len(ranked),
            source_player_counts=result.source_player_counts,
            pipeline_status=readiness.status,
            pipeline_warnings=readiness.warnings,
        )
        write_json_output(args.output, payload)
        csv_output = Path(args.output).with_suffix(".csv")
        write_csv_output(str(csv_output), displayed_ranked)
        if llm_client.is_enabled():
            llm_result = llm_client.generate_explanation(displayed_ranked)
            if llm_result is not None:
                llm_output = Path(args.output).with_name("llm_response.json")
                write_json_output(str(llm_output), asdict(llm_result))
                print(f"llm_enabled={llm_result.enabled}")
                print(f"llm_prompt_tokens={llm_result.prompt_tokens}")
                print(f"llm_output={llm_output.as_posix()}")
                if llm_result.error:
                    print(f"warning=llm_request_failed:{llm_result.error}")

        print(f"sources_used={len(source_clients)}")
        print(f"sources_failed={len(result.failed_sources)}")
        print(f"players_collected={len(result.players)}")
        print(f"players_eligible={len(ranked)}")
        print(f"displayed_players={len(displayed_ranked)}")
        print(f"pipeline_status={readiness.status}")
        print(f"source_player_counts={result.source_player_counts}")
        print(f"output={args.output}")
        print(f"csv_output={csv_output.as_posix()}")
        for warning in readiness.warnings:
            print(f"warning={warning}")
        for index, item in enumerate(displayed_ranked, start=1):
            print(
                f"{index}. {item.player.name} | club={item.player.club or ''} | "
                f"market_value={item.player.market_value or ''} | score={item.score}"
            )
        return 0

    print("scaffold_ready=true")
    print(f"config={Path(args.config).as_posix()}")
    return 0
