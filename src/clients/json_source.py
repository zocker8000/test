import json
from typing import Any, Dict, Iterable, List, Mapping, Optional

from kickbase.bot.models import PlayerRecord

from .base import BaseSourceClient


class SourceFetchError(RuntimeError):
    pass


class JsonFeedSourceClient(BaseSourceClient):
    source_name = "generic_json_feed_source"

    DEFAULT_FIELD_MAP = {
        "player_id": "player_id",
        "name": "name",
        "club": "club",
        "position": "position",
        "market_value": "market_value",
        "reported_at": "reported_at",
        "confidence": "confidence",
        "signals": "signals",
    }

    def __init__(
        self,
        endpoint_url: str,
        player_list_key: Optional[str] = None,
        field_map: Optional[Mapping[str, str]] = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.player_list_key = player_list_key
        self.field_map = dict(self.DEFAULT_FIELD_MAP)
        if field_map:
            for target_field, source_field in field_map.items():
                if target_field in self.DEFAULT_FIELD_MAP and source_field:
                    self.field_map[target_field] = source_field
        self.timeout_seconds = timeout_seconds

    def fetch(self) -> List[PlayerRecord]:
        payload = self._load_payload()
        items = self._extract_items(payload)
        return [self._to_player_record(item) for item in items]

    def _load_payload(self) -> Any:
        try:
            raw = self._load_url_text(self.endpoint_url, extra_cache_key=self.player_list_key or "")
        except Exception as exc:  # pragma: no cover - network errors vary
            raise SourceFetchError(f"failed to load JSON feed from {self.endpoint_url}") from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SourceFetchError("JSON feed payload is not valid JSON") from exc

    def _extract_items(self, payload: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(payload, list):
            return payload

        if isinstance(payload, dict):
            if self.player_list_key:
                items = payload.get(self.player_list_key)
                if isinstance(items, list):
                    return items
                raise SourceFetchError(
                    f"JSON feed did not contain a list at key '{self.player_list_key}'"
                )

            for fallback_key in ("players", "data", "items"):
                items = payload.get(fallback_key)
                if isinstance(items, list):
                    return items

        raise SourceFetchError("JSON feed must be a list or contain a list under a known key")

    def _to_player_record(self, item: Mapping[str, Any]) -> PlayerRecord:
        player_id = self._require_string(item, self.field_map["player_id"])
        name = self._require_string(item, self.field_map["name"])
        club = self._optional_string(self._get(item, "club"))
        position = self._optional_string(self._get(item, "position"))
        market_value = self._optional_int(self._get(item, "market_value"))
        reported_at = self._optional_string(self._get(item, "reported_at"))
        confidence = self._optional_float(self._get(item, "confidence"), default=0.0)
        signals = self._get(item, "signals")
        signals = signals if isinstance(signals, dict) else {}

        return PlayerRecord(
            player_id=player_id,
            name=name,
            club=club,
            position=position,
            market_value=market_value,
            reported_at=reported_at,
            confidence=confidence,
            signals={key: float(value) for key, value in signals.items()},
        )

    def _get(self, item: Mapping[str, Any], target_field: str) -> Any:
        source_field = self.field_map[target_field]
        return item.get(source_field)

    @staticmethod
    def _require_string(item: Mapping[str, Any], key: str) -> str:
        value = item.get(key)
        if not isinstance(value, str) or not value.strip():
            raise SourceFetchError(f"missing or invalid '{key}' field in JSON feed item")
        return value.strip()

    @staticmethod
    def _optional_string(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)

    @staticmethod
    def _optional_int(value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            raise SourceFetchError("boolean values are not valid market values")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise SourceFetchError("invalid integer field in JSON feed") from exc

    @staticmethod
    def _optional_float(value: Any, default: float = 0.0) -> float:
        if value is None or value == "":
            return default
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise SourceFetchError("invalid float field in JSON feed") from exc

    def _timeout_seconds(self) -> float:
        return self.timeout_seconds
