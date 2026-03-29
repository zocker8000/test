from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Optional


class SourceResponseCache:
    def __init__(self, root: str = ".cache/source_responses") -> None:
        self.root = Path(root)

    def build_key(self, source_name: str, url: str, extra: str = "") -> str:
        digest = hashlib.sha256(f"{source_name}|{url}|{extra}".encode("utf-8")).hexdigest()
        return digest

    def read_text(self, cache_key: str, max_age_seconds: Optional[int] = None) -> Optional[str]:
        path = self.root / f"{cache_key}.txt"
        if not path.exists():
            return None
        if max_age_seconds is not None:
            age_seconds = self._age_seconds(path)
            if age_seconds is not None and age_seconds > max_age_seconds:
                return None
        return path.read_text(encoding="utf-8")

    def write_text(self, cache_key: str, content: str) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{cache_key}.txt"
        path.write_text(content, encoding="utf-8")
        return path

    @staticmethod
    def _age_seconds(path: Path) -> Optional[float]:
        try:
            return max(0.0, time.time() - path.stat().st_mtime)
        except OSError:
            return None
