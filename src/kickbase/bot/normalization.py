import re
from dataclasses import replace
import unicodedata
from typing import Optional

from .models import PlayerRecord


def normalize_player_name(name: str) -> str:
    return " ".join(name.strip().split()).casefold()


def normalize_club_label(club: Optional[str]) -> Optional[str]:
    if club is None:
        return None
    normalized = " ".join(club.strip().split())
    if not normalized:
        return None
    folded = _ascii_fold(normalized.casefold())
    collapsed = _collapse_club_label(folded)
    if collapsed.startswith("fc "):
        collapsed = collapsed[3:]
    alias = _CLUB_ALIASES.get(collapsed)
    return alias or collapsed


def normalize_player_record(record: PlayerRecord, club: Optional[str] = None) -> PlayerRecord:
    normalized_name = " ".join(record.name.strip().split())
    normalized_club = normalize_club_label(club if club is not None else record.club)
    return replace(record, name=normalized_name, club=normalized_club)


def _ascii_fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _collapse_club_label(value: str) -> str:
    collapsed = " ".join(value.split())
    collapsed = re.sub(r"\b1\.\s*fc\b", "fc", collapsed)
    collapsed = re.sub(r"\b1\s+fc\b", "fc", collapsed)
    collapsed = collapsed.replace("&", "and")
    collapsed = collapsed.replace(".", "")
    collapsed = collapsed.replace("'", "")
    collapsed = " ".join(collapsed.split())
    return collapsed.strip()


_CLUB_ALIASES = {
    "bayern munich": "bayern münchen",
    "bayern munchen": "bayern münchen",
    "fc bayern munich": "bayern münchen",
    "fc bayern munchen": "bayern münchen",
    "bayer 04 leverkusen": "bayer leverkusen",
    "bayer leverkusen": "bayer leverkusen",
    "eintracht frankfurt": "eintracht frankfurt",
    "borussia dortmund": "borussia dortmund",
    "sc freiburg": "sc freiburg",
    "mainz 05": "mainz 05",
    "fsv mainz 05": "mainz 05",
    "rb leipzig": "rb leipzig",
    "werder bremen": "werder bremen",
    "vfb stuttgart": "vfb stuttgart",
    "borussia monchengladbach": "borussia mönchengladbach",
    "borussia moenchengladbach": "borussia mönchengladbach",
    "borussia mönchengladbach": "borussia mönchengladbach",
    "vfl wolfsburg": "vfl wolfsburg",
    "fc augsburg": "fc augsburg",
    "union berlin": "union berlin",
    "fc union berlin": "union berlin",
    "st pauli": "fc st. pauli",
    "fc st pauli": "fc st. pauli",
    "tsg 1899 hoffenheim": "tsg hoffenheim",
    "hoffenheim": "tsg hoffenheim",
    "fc heidenheim 1846": "1. fc heidenheim 1846",
    "heidenheim 1846": "1. fc heidenheim 1846",
    "fc koln": "1. fc köln",
    "koln": "1. fc köln",
    "fc köln": "1. fc köln",
    "köln": "1. fc köln",
    "hamburger sv": "hamburger sv",
}
