from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path


__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]

_src_package = Path(__file__).resolve().parent.parent / "src" / "clients"
if _src_package.exists():
    __path__.append(str(_src_package))

from .bundesliga_roster_source import BundesligaRosterSourceClient
from .bundesliga_stats_source import BundesligaStatsSourceClient
from .json_source import JsonFeedSourceClient, SourceFetchError
from .transfermarkt_source import TransfermarktMarketValuesSourceClient

__all__ = [
    "BundesligaRosterSourceClient",
    "BundesligaStatsSourceClient",
    "JsonFeedSourceClient",
    "SourceFetchError",
    "TransfermarktMarketValuesSourceClient",
]
