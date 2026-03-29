from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .models import PlayerRecord
from .normalization import normalize_club_label, normalize_player_name, normalize_player_record

ALLOWED_SOURCE_BUCKETS = (
    "player_pool_sources",
    "market_value_sources",
    "news_sources",
    "stats_sources",
)


@dataclass(frozen=True)
class SourceDefinition:
    name: str
    enabled: bool
    priority: int


@dataclass(frozen=True)
class PlayerMatch:
    match_key: str
    canonical: PlayerRecord
    variants: List[PlayerRecord]


@dataclass(frozen=True)
class IngestionResult:
    players: List[PlayerRecord]
    source_names: List[str]
    failed_sources: List[str]
    source_player_counts: Dict[str, int]
    matches: List[PlayerMatch]


class SourceValidationError(ValueError):
    pass


class IngestionService:
    def validate_source_registry(self, source_registry: Mapping[str, object]) -> Dict[str, List[SourceDefinition]]:
        if not isinstance(source_registry, Mapping):
            raise SourceValidationError("source registry must be a mapping")

        validated: Dict[str, List[SourceDefinition]] = {}
        for bucket_name in ALLOWED_SOURCE_BUCKETS:
            bucket = source_registry.get(bucket_name, [])
            if not isinstance(bucket, list):
                raise SourceValidationError(f"{bucket_name} must be a list")

            validated_bucket: List[SourceDefinition] = []
            for index, entry in enumerate(bucket):
                validated_bucket.append(self._validate_source_entry(bucket_name, index, entry))
            validated[bucket_name] = validated_bucket

        return validated

    def collect_players(self, sources: Sequence[object]) -> IngestionResult:
        collected: List[PlayerRecord] = []
        source_names: List[str] = []
        failed_sources: List[str] = []
        source_player_counts: Dict[str, int] = {}

        for source in sources:
            source_name = getattr(source, "source_name", source.__class__.__name__)
            source_names.append(source_name)
            try:
                fetched = source.fetch() if hasattr(source, "fetch") else []
            except Exception:
                failed_sources.append(source_name)
                source_player_counts[source_name] = 0
                continue
            source_player_counts[source_name] = len(fetched)
            collected.extend(fetched)

        matches = self.find_player_matches(collected)
        return IngestionResult(
            players=self.merge_player_records(collected),
            source_names=source_names,
            failed_sources=failed_sources,
            source_player_counts=source_player_counts,
            matches=matches,
        )

    def find_player_matches(self, records: Iterable[PlayerRecord]) -> List[PlayerMatch]:
        normalized_records = [normalize_player_record(record) for record in records]
        if not normalized_records:
            return []

        grouped_by_name: Dict[str, List[PlayerRecord]] = {}
        for record in normalized_records:
            name_key = normalize_player_name(record.name)
            if not name_key:
                continue
            grouped_by_name.setdefault(name_key, []).append(record)

        matches: List[PlayerMatch] = []
        for name_key in sorted(grouped_by_name):
            name_group = grouped_by_name[name_key]
            club_groups: Dict[str, List[PlayerRecord]] = {}
            clubless: List[PlayerRecord] = []

            for record in name_group:
                club_key = normalize_club_label(record.club)
                if club_key:
                    club_groups.setdefault(club_key, []).append(record)
                else:
                    clubless.append(record)

            if not club_groups:
                matches.append(self._build_match(f"name::{name_key}", name_group))
                continue

            if len(club_groups) == 1:
                club_key, club_records = next(iter(club_groups.items()))
                variants = list(club_records) + clubless
                matches.append(self._build_match(f"nameclub::{name_key}::{club_key}", variants))
                continue

            for club_key in sorted(club_groups):
                matches.append(self._build_match(f"nameclub::{name_key}::{club_key}", club_groups[club_key]))
            if clubless:
                matches.append(self._build_match(f"name::{name_key}", clubless))

        return matches

    def merge_player_records(self, records: Iterable[PlayerRecord]) -> List[PlayerRecord]:
        merged = []
        for match in self.find_player_matches(records):
            merged.append(self._merge_variants(match.variants, match.canonical))
        return sorted(
            merged,
            key=lambda record: (
                record.player_id.casefold() if record.player_id else "",
                normalize_player_name(record.name),
                normalize_club_label(record.club) or "",
            ),
        )

    def _validate_source_entry(self, bucket_name: str, index: int, entry: object) -> SourceDefinition:
        if not isinstance(entry, Mapping):
            raise SourceValidationError(f"{bucket_name}[{index}] must be a mapping")

        name = entry.get("name")
        enabled = entry.get("enabled")
        priority = entry.get("priority")

        if not isinstance(name, str) or not name.strip():
            raise SourceValidationError(f"{bucket_name}[{index}].name must be a non-empty string")
        if not isinstance(enabled, bool):
            raise SourceValidationError(f"{bucket_name}[{index}].enabled must be a boolean")
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise SourceValidationError(f"{bucket_name}[{index}].priority must be an integer")
        if priority < 0:
            raise SourceValidationError(f"{bucket_name}[{index}].priority must be >= 0")

        return SourceDefinition(name=name.strip(), enabled=enabled, priority=priority)

    def _build_match(self, match_key: str, variants: Sequence[PlayerRecord]) -> PlayerMatch:
        ordered_variants = list(variants)
        return PlayerMatch(
            match_key=match_key,
            canonical=self._select_canonical_record(ordered_variants),
            variants=ordered_variants,
        )

    def _select_canonical_record(self, records: Sequence[PlayerRecord]) -> PlayerRecord:
        best = records[0]
        best_quality = self._record_quality(best)
        for record in records[1:]:
            quality = self._record_quality(record)
            if quality > best_quality:
                best = record
                best_quality = quality
        return normalize_player_record(best)

    @staticmethod
    def _record_quality(record: PlayerRecord) -> Tuple[int, int, int, int, int, str]:
        return (
            1 if record.market_value is not None else 0,
            1 if record.confidence > 0 else 0,
            1 if record.club else 0,
            1 if record.position else 0,
            1 if record.reported_at else 0,
            len(record.signals),
            record.player_id,
        )

    def _merge_variants(self, variants: Sequence[PlayerRecord], canonical: PlayerRecord) -> PlayerRecord:
        market_values = [record.market_value for record in variants if record.market_value is not None]
        confidences = [record.confidence for record in variants]
        clubs = [record.club for record in variants if record.club]
        positions = [record.position for record in variants if record.position]
        reported_times = [record.reported_at for record in variants if record.reported_at]
        player_ids = [record.player_id for record in variants if record.player_id]
        merged_signals: Dict[str, float] = {}
        for record in variants:
            for signal_name, signal_value in record.signals.items():
                current = merged_signals.get(signal_name)
                numeric_value = float(signal_value)
                if current is None or numeric_value > current:
                    merged_signals[signal_name] = numeric_value

        return PlayerRecord(
            player_id=self._preferred_value(player_ids, canonical.player_id),
            name=canonical.name,
            club=self._preferred_value(clubs, canonical.club),
            position=self._preferred_value(positions, canonical.position),
            market_value=max(market_values) if market_values else canonical.market_value,
            reported_at=self._preferred_value(reported_times, canonical.reported_at),
            confidence=self._calculate_confidence(variants, canonical, confidences),
            signals=merged_signals,
        )

    @staticmethod
    def _preferred_value(values: Sequence[str], fallback: Optional[str]) -> Optional[str]:
        for value in values:
            if value:
                return value
        return fallback

    @staticmethod
    def _calculate_confidence(
        variants: Sequence[PlayerRecord],
        canonical: PlayerRecord,
        confidences: Sequence[float],
    ) -> float:
        if not variants:
            return 0.0

        strongest_source_confidence = max(confidences) if confidences else canonical.confidence
        club_values = {normalize_club_label(record.club) for record in variants if record.club}
        name_values = {normalize_player_name(record.name) for record in variants if record.name}

        quality = 0.0
        if any(record.market_value is not None for record in variants):
            quality += 0.25
        if any(record.club for record in variants):
            quality += 0.15
        if any(record.position for record in variants):
            quality += 0.10
        if any(record.reported_at for record in variants):
            quality += 0.05
        if any(record.signals for record in variants):
            quality += 0.10
        if len(variants) > 1:
            quality += 0.10
        if len(club_values) <= 1 and club_values:
            quality += 0.10
        if len(name_values) == 1:
            quality += 0.10
        if canonical.market_value is not None:
            quality += 0.05

        blended = max(strongest_source_confidence * 0.7, quality)
        return round(min(1.0, blended), 3)
