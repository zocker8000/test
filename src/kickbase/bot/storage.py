import json
from pathlib import Path
from typing import Any, Optional


class JsonStorage:
    def __init__(self, root: str = ".cache") -> None:
        self.root = Path(root)

    def read(self, key: str) -> Optional[Any]:
        path = self.root / f"{key}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write(self, key: str, payload: Any) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{key}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

