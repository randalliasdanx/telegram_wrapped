"""Shared state store.

``MemoryStore`` (default) keeps everything in-process — fine for a single
instance. Set ``REDIS_URL`` to use ``RedisStore`` so any number of API
instances/workers share sessions, progress, results and rate limits; then a
request can land on any instance (no sticky sessions needed).
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Protocol


class Store(Protocol):
    async def get_json(self, key: str) -> Any | None: ...
    async def set_json(self, key: str, value: Any, ttl: int) -> None: ...
    async def delete(self, *keys: str) -> None: ...
    async def hit(self, key: str, window: int) -> int: ...
    async def schedule(self, member: str, at: float) -> None: ...
    async def unschedule(self, member: str) -> None: ...
    async def claim_due(self, now: float, limit: int = 50) -> list[str]: ...


class MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}
        self._schedule: dict[str, float] = {}

    def _alive(self, key: str) -> str | None:
        item = self._data.get(key)
        if item is None:
            return None
        expires, raw = item
        if expires < time.time():
            self._data.pop(key, None)
            return None
        return raw

    async def get_json(self, key: str) -> Any | None:
        raw = self._alive(key)
        return None if raw is None else json.loads(raw)

    async def set_json(self, key: str, value: Any, ttl: int) -> None:
        self._data[key] = (time.time() + ttl, json.dumps(value))
        if len(self._data) % 256 == 0:
            self._sweep()

    async def delete(self, *keys: str) -> None:
        for k in keys:
            self._data.pop(k, None)

    async def hit(self, key: str, window: int) -> int:
        raw = self._alive(key)
        count = (int(raw) if raw else 0) + 1
        expires = self._data[key][0] if raw else time.time() + window
        self._data[key] = (expires, str(count))
        return count

    async def schedule(self, member: str, at: float) -> None:
        self._schedule[member] = at

    async def unschedule(self, member: str) -> None:
        self._schedule.pop(member, None)

    async def claim_due(self, now: float, limit: int = 50) -> list[str]:
        due = [m for m, at in self._schedule.items() if at <= now][:limit]
        for m in due:
            self._schedule.pop(m, None)
        return due

    def _sweep(self) -> None:
        now = time.time()
        for k in [k for k, (exp, _) in self._data.items() if exp < now]:
            self._data.pop(k, None)


class RedisStore:
    SCHEDULE_KEY = "tgw:expiry"

    def __init__(self, url: str, prefix: str = "tgw:") -> None:
        import redis.asyncio as redis

        self._r = redis.from_url(url, decode_responses=True)
        self._p = prefix

    async def get_json(self, key: str) -> Any | None:
        raw = await self._r.get(self._p + key)
        return None if raw is None else json.loads(raw)

    async def set_json(self, key: str, value: Any, ttl: int) -> None:
        await self._r.set(self._p + key, json.dumps(value), ex=ttl)

    async def delete(self, *keys: str) -> None:
        if keys:
            await self._r.delete(*(self._p + k for k in keys))

    async def hit(self, key: str, window: int) -> int:
        k = self._p + key
        count = int(await self._r.incr(k))
        if count == 1:
            await self._r.expire(k, window)
        return count

    async def schedule(self, member: str, at: float) -> None:
        await self._r.zadd(self.SCHEDULE_KEY, {member: at})

    async def unschedule(self, member: str) -> None:
        await self._r.zrem(self.SCHEDULE_KEY, member)

    async def claim_due(self, now: float, limit: int = 50) -> list[str]:
        due = await self._r.zrangebyscore(self.SCHEDULE_KEY, 0, now, start=0, num=limit)
        claimed = []
        for m in due:
            # ZREM is atomic: exactly one instance wins each member
            if await self._r.zrem(self.SCHEDULE_KEY, m):
                claimed.append(m)
        return claimed


_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        url = os.environ.get("REDIS_URL", "")
        _store = RedisStore(url) if url else MemoryStore()
    return _store


def set_store(store: Store | None) -> None:
    """Override the store (tests)."""
    global _store
    _store = store
