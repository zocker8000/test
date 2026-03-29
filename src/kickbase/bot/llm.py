from dataclasses import dataclass, field
import json
import math
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import load_llm_settings
from .models import ScoredPlayer


@dataclass(frozen=True)
class LLMConfig:
    enabled: bool = True
    api_key_file: str = ".secrets/openai_api_key.txt"
    api_base_url: str = "https://api.openai.com/v1/responses"
    model: str = "gpt-4o-mini"
    max_players: int = 5
    prompt_token_budget: int = 320
    response_token_budget: int = 160

    @classmethod
    def from_mapping(cls, values: Dict[str, Any]) -> "LLMConfig":
        return cls(
            enabled=bool(values.get("enabled", cls.enabled)),
            api_key_file=str(values.get("api_key_file", cls.api_key_file)),
            api_base_url=str(values.get("api_base_url", cls.api_base_url)),
            model=str(values.get("model", cls.model)),
            max_players=int(values.get("max_players", cls.max_players)),
            prompt_token_budget=int(values.get("prompt_token_budget", cls.prompt_token_budget)),
            response_token_budget=int(values.get("response_token_budget", cls.response_token_budget)),
        )


@dataclass(frozen=True)
class LLMPromptPlan:
    enabled: bool
    api_key_loaded: bool
    api_key_file: str
    model: str
    prompt: str
    prompt_tokens: int
    response_token_budget: int
    player_summaries: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class LLMExchangeResult:
    enabled: bool
    api_key_loaded: bool
    api_key_file: str
    model: str
    request_payload: Dict[str, Any]
    prompt: str
    prompt_tokens: int
    response_token_budget: int
    player_summaries: List[Dict[str, Any]] = field(default_factory=list)
    response_text: str = ""
    response_json: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


def load_llm_config(path: str = "config/llm.yaml") -> LLMConfig:
    settings = load_llm_settings(path)
    llm_settings = settings.get("llm", {})
    if not isinstance(llm_settings, dict):
        llm_settings = {}
    return LLMConfig.from_mapping(llm_settings)


def read_api_key_from_file(path: str) -> Optional[str]:
    api_path = Path(path)
    if not api_path.exists():
        return None
    try:
        value = api_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not value or _looks_like_placeholder_key(value):
        return None
    return value


def estimate_prompt_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def compact_player_summary(player: ScoredPlayer) -> Dict[str, Any]:
    signal_items = [
        f"{name}={value:.2f}"
        for name, value in sorted(player.normalized_signals.items(), key=lambda item: (-item[1], item[0]))[:3]
        if value > 0
    ]
    return {
        "id": player.player.player_id,
        "name": player.player.name,
        "club": player.player.club or "",
        "pos": player.player.position or "",
        "mv": player.player.market_value or 0,
        "score": round(player.score, 3),
        "sig": signal_items,
    }


def select_prompt_players(ranked_players: Sequence[ScoredPlayer], config: LLMConfig) -> List[ScoredPlayer]:
    selected: List[ScoredPlayer] = []
    for player in ranked_players[: max(config.max_players, 0)]:
        candidate = selected + [player]
        candidate_prompt = build_explanation_prompt(candidate)
        if estimate_prompt_tokens(candidate_prompt) > config.prompt_token_budget:
            break
        selected.append(player)
    if not selected and ranked_players:
        selected = [ranked_players[0]]
    return selected


def build_explanation_prompt(ranked_players: Iterable[ScoredPlayer]) -> str:
    summaries = [compact_player_summary(player) for player in ranked_players]
    return _build_prompt_from_summaries(summaries)


def build_llm_plan(
    ranked_players: Sequence[ScoredPlayer],
    *,
    config: LLMConfig,
    api_key: Optional[str] = None,
) -> LLMPromptPlan:
    if not config.enabled:
        return LLMPromptPlan(
            enabled=False,
            api_key_loaded=False,
            api_key_file=config.api_key_file,
            model=config.model,
            prompt="",
            prompt_tokens=0,
            response_token_budget=config.response_token_budget,
            player_summaries=[],
        )

    selected_players = select_prompt_players(ranked_players, config)
    summaries = [compact_player_summary(player) for player in selected_players]
    prompt = _build_prompt_from_summaries(summaries)
    can_send = bool(api_key)

    return LLMPromptPlan(
        enabled=can_send,
        api_key_loaded=can_send,
        api_key_file=config.api_key_file,
        model=config.model,
        prompt=prompt,
        prompt_tokens=estimate_prompt_tokens(prompt),
        response_token_budget=config.response_token_budget,
        player_summaries=summaries,
    )


def build_llm_plan_from_file(
    ranked_players: Sequence[ScoredPlayer],
    *,
    config_path: str = "config/llm.yaml",
) -> LLMPromptPlan:
    config = load_llm_config(config_path)
    api_key = read_api_key_from_file(config.api_key_file) if config.enabled else None
    return build_llm_plan(ranked_players, config=config, api_key=api_key)


def build_openai_request_payload(prompt: str, config: LLMConfig) -> Dict[str, Any]:
    return {
        "model": config.model,
        "max_output_tokens": config.response_token_budget,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    }
                ],
            }
        ],
    }


def call_openai_responses_api(
    *,
    api_key: str,
    request_payload: Dict[str, Any],
    base_url: str,
    timeout_seconds: float = 30.0,
    max_retries: int = 2,
    retry_backoff_seconds: float = 2.0,
) -> Dict[str, Any]:
    request = Request(
        base_url,
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
            break
        except HTTPError as exc:
            last_error = exc
            if exc.code == 429 and attempt < max_retries:
                time.sleep(retry_backoff_seconds * (attempt + 1))
                continue
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc
        except URLError as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(retry_backoff_seconds * (attempt + 1))
                continue
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc
    else:  # pragma: no cover - loop exits via break or raise
        if last_error is not None:
            raise RuntimeError(f"OpenAI request failed: {last_error}") from last_error
        raise RuntimeError("OpenAI request failed")

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI response was not valid JSON") from exc


def extract_response_text(response_json: Mapping[str, Any]) -> str:
    outputs = response_json.get("output", [])
    if not isinstance(outputs, list):
        return ""

    collected: List[str] = []
    for item in outputs:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", "")).strip()
        if item_type == "message":
            content = item.get("content", [])
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                part_type = str(part.get("type", "")).strip()
                text = part.get("text")
                if part_type == "output_text" and isinstance(text, str):
                    collected.append(text)
                elif part_type == "refusal" and isinstance(part.get("refusal"), str):
                    collected.append(part["refusal"])
        elif item_type == "output_text" and isinstance(item.get("text"), str):
            collected.append(item["text"])
    return "\n".join(text.strip() for text in collected if isinstance(text, str) and text.strip())


def _build_prompt_header() -> str:
    return (
        "You are not ranking. Explain these precomputed Bundesliga results only. "
        "Do not reorder players. Keep it short."
    )


def _build_prompt_from_summaries(summaries: List[Dict[str, Any]]) -> str:
    lines = [_build_prompt_header(), "Players:"]
    for index, summary in enumerate(summaries, start=1):
        signals = ",".join(summary["sig"]) if summary["sig"] else "none"
        lines.append(
            f"{index}. {summary['name']}|{summary['club']}|{summary['pos']}|score={summary['score']:.3f}|"
            f"mv={summary['mv']}|sig={signals}"
        )
    lines.append("Reply with one short bullet per player and a brief keep/reject note.")
    return "\n".join(lines)


def _looks_like_placeholder_key(value: str) -> bool:
    normalized = value.strip().casefold()
    return normalized.startswith("replace_with_") or normalized.startswith("your_") or normalized in {
        "changeme",
        "change_me",
        "placeholder",
        "your-api-key-here",
        "api-key-here",
    }


class OptionalLLMClient:
    def __init__(self, config_path: str = "config/llm.yaml") -> None:
        self.config = load_llm_config(config_path)
        self.api_key = read_api_key_from_file(self.config.api_key_file) if self.config.enabled else None

    def is_enabled(self) -> bool:
        return self.config.enabled and bool(self.api_key)

    def build_explanation_request(self, ranked_players: Sequence[ScoredPlayer]) -> LLMPromptPlan:
        return build_llm_plan(ranked_players, config=self.config, api_key=self.api_key)

    def generate_explanation(self, ranked_players: Sequence[ScoredPlayer]) -> Optional[LLMExchangeResult]:
        if not self.is_enabled():
            return None

        plan = self.build_explanation_request(ranked_players)
        request_payload = build_openai_request_payload(plan.prompt, self.config)

        try:
            response_json = call_openai_responses_api(
                api_key=str(self.api_key),
                request_payload=request_payload,
                base_url=self.config.api_base_url,
            )
            response_text = extract_response_text(response_json)
            error = None
        except Exception as exc:
            response_json = {}
            response_text = ""
            error = str(exc)

        return LLMExchangeResult(
            enabled=self.is_enabled(),
            api_key_loaded=self.is_enabled(),
            api_key_file=self.config.api_key_file,
            model=self.config.model,
            request_payload=request_payload,
            prompt=plan.prompt,
            prompt_tokens=plan.prompt_tokens,
            response_token_budget=self.config.response_token_budget,
            player_summaries=plan.player_summaries,
            response_text=response_text,
            response_json=response_json,
            error=error,
        )
