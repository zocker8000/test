from abc import ABC, abstractmethod
import time
from typing import List

from kickbase.bot.models import PlayerRecord

from .cache import SourceResponseCache


class BaseSourceClient(ABC):
    source_name: str = "base"
    cache_root: str = ".cache/source_responses"
    cache_ttl_seconds: int = 3600
    request_retries: int = 2
    retry_backoff_seconds: float = 1.0

    @abstractmethod
    def fetch(self) -> List[PlayerRecord]:
        raise NotImplementedError

    def is_enabled(self) -> bool:
        return True

    def cache_key(self) -> str:
        return self.source_name

    def _load_url_text(self, url: str, extra_cache_key: str = "") -> str:
        from urllib.request import Request, urlopen

        cache = SourceResponseCache(self.cache_root)
        cache_key = cache.build_key(self.source_name, url, extra_cache_key)
        cached = cache.read_text(cache_key, max_age_seconds=self.cache_ttl_seconds)
        if cached is not None:
            return cached

        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        last_error = None
        for attempt in range(self.request_retries + 1):
            try:
                with urlopen(request, timeout=self._timeout_seconds()) as response:
                    text = response.read().decode("utf-8", "ignore")
                cache.write_text(cache_key, text)
                return text
            except Exception as exc:
                last_error = exc
                stale_cached = cache.read_text(cache_key, max_age_seconds=None)
                if stale_cached is not None:
                    return stale_cached
                if attempt < self.request_retries:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                break
        raise last_error  # type: ignore[misc]

    def _timeout_seconds(self) -> float:
        return 20.0
