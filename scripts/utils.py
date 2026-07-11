"""
utils.py
--------
Shared, dependency-light utilities used across every engine:

* structured logging
* on-disk JSON caching with TTL
* retry-with-backoff decorator
* small formatting helpers (numbers, dates, XML escaping)
"""

from __future__ import annotations

import functools
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
                               datefmt="%H:%M:%S")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


log = get_logger("neoquantumforge")


# --------------------------------------------------------------------------
# Caching
# --------------------------------------------------------------------------

class JSONCache:
    """A tiny file-backed cache with a time-to-live, used to avoid hammering
    the GitHub API and to keep the build resilient when the API is briefly
    unavailable (the last good response is reused)."""

    def __init__(self, cache_dir: Path, ttl_seconds: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

    def _path(self, key: str) -> Path:
        safe_key = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str, allow_stale: bool = False) -> Optional[Any]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

        age = time.time() - payload.get("_cached_at", 0)
        if age > self.ttl_seconds and not allow_stale:
            return None
        return payload.get("data")

    def set(self, key: str, data: Any) -> None:
        path = self._path(key)
        payload = {"_cached_at": time.time(), "data": data}
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


# --------------------------------------------------------------------------
# Retry decorator
# --------------------------------------------------------------------------

def retry(times: int = 3, delay_seconds: float = 1.5, backoff: float = 2.0,
          exceptions: tuple = (Exception,)) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry a function call with exponential backoff."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay_seconds
            last_exc: Optional[BaseException] = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001
                    last_exc = exc
                    log.warning(
                        "%s failed (attempt %d/%d): %s",
                        func.__name__, attempt, times, exc
                    )
                    if attempt < times:
                        time.sleep(current_delay)
                        current_delay *= backoff
            assert last_exc is not None
            raise last_exc
        return wrapper
    return decorator


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------

def format_count(n: int) -> str:
    """1234 -> '1.2k', 999 -> '999'."""
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k"
    return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "\u2026"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
