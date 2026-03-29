from pathlib import Path
from typing import Any, Dict

from .models import RankingThresholds, RankingWeights


def _load_yaml_like(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        return _fallback_load(path)

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def _fallback_load(path: Path) -> Dict[str, Any]:
    current_section = None
    current_list = None
    root: Dict[str, Any] = {}
    current_item = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0 and stripped.endswith(":"):
            current_section = stripped[:-1]
            root[current_section] = {}
            current_list = None
            current_item = None
            continue

        if indent == 2 and stripped.startswith("- "):
            key_values = stripped[2:]
            if current_section not in root or not isinstance(root[current_section], list):
                root[current_section] = []
            current_list = root[current_section]
            current_item = {}
            current_list.append(current_item)
            if ":" in key_values:
                key, value = key_values.split(":", 1)
                current_item[key.strip()] = _parse_scalar(value.strip())
            continue

        if indent == 4 and current_item is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current_item[key.strip()] = _parse_scalar(value.strip())
            continue

        if indent == 2 and ":" in stripped and isinstance(root.get(current_section), dict):
            key, value = stripped.split(":", 1)
            root[current_section][key.strip()] = _parse_scalar(value.strip())
            continue

        if indent == 4 and current_section and isinstance(root.get(current_section), dict):
            section = root[current_section]
            if isinstance(section, dict) and ":" in stripped:
                key, value = stripped.split(":", 1)
                section[key.strip()] = _parse_scalar(value.strip())
            continue

    return root


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value == "":
        return ""
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def load_ranking_settings(path: str = "config/ranking_weights.yaml") -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {
            "weights": {},
            "thresholds": {},
        }
    return _load_yaml_like(config_path)


def load_ranking_weights(path: str = "config/ranking_weights.yaml") -> RankingWeights:
    settings = load_ranking_settings(path)
    return RankingWeights.from_mapping(settings.get("weights", {}))


def load_ranking_thresholds(path: str = "config/ranking_weights.yaml") -> RankingThresholds:
    settings = load_ranking_settings(path)
    return RankingThresholds.from_mapping(settings.get("thresholds", {}))


def load_feed_settings(path: str = "config/feeds.yaml") -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {"sources": []}
    return _load_yaml_like(config_path)


def load_llm_settings(path: str = "config/llm.yaml") -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {"llm": {}}
    return _load_yaml_like(config_path)
