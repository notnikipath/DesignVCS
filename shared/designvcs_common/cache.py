from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: datetime


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int = 30) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, CacheEntry[T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._items.get(key)
        if entry is None:
            return None
        if datetime.now(UTC) >= entry.expires_at:
            self._items.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T) -> None:
        self._items[key] = CacheEntry(value=value, expires_at=datetime.now(UTC) + timedelta(seconds=self.ttl_seconds))

    def get_or_set(self, key: str, provider: Callable[[], T]) -> T:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = provider()
        self.set(key, value)
        return value

    def size(self) -> int:
        self._cleanup()
        return len(self._items)

    def _cleanup(self) -> None:
        now = datetime.now(UTC)
        expired = [key for key, item in self._items.items() if now >= item.expires_at]
        for key in expired:
            self._items.pop(key, None)