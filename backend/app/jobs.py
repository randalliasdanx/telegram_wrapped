"""Per-instance pipeline scheduler.

Each running pipeline holds one Telegram connection and some CPU, so an
instance runs at most ``MAX_CONCURRENT_PIPELINES`` at once; the rest wait in a
FIFO queue and see their position in the progress stream. Scale out by adding
instances (with ``REDIS_URL`` set, any instance can serve any session).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Awaitable, Callable

log = logging.getLogger("wrapped.jobs")

MAX_CONCURRENT_PIPELINES = int(os.environ.get("MAX_CONCURRENT_PIPELINES", "8"))

ProgressFn = Callable[[dict[str, Any]], Awaitable[None]]


class JobScheduler:
    def __init__(self, max_concurrent: int = MAX_CONCURRENT_PIPELINES) -> None:
        self._sem = asyncio.Semaphore(max_concurrent)
        self._waiting: list[str] = []
        self._progress: dict[str, ProgressFn] = {}
        self._tasks: dict[str, asyncio.Task] = {}  # type: ignore[type-arg]
        self.running = 0

    def is_active(self, sid: str) -> bool:
        task = self._tasks.get(sid)
        return task is not None and not task.done()

    def stats(self) -> dict[str, int]:
        return {"running": self.running, "queued": len(self._waiting)}

    async def _announce_queue(self) -> None:
        for pos, sid in enumerate(self._waiting, start=1):
            fn = self._progress.get(sid)
            if fn is not None:
                await fn({
                    "phase": "queued",
                    "queue_position": pos,
                    "message": f"You're #{pos} in line — lots of people unwrapping right now!",
                })

    def submit(self, sid: str, work: Callable[[], Awaitable[None]], progress: ProgressFn) -> None:
        async def runner() -> None:
            self._waiting.append(sid)
            self._progress[sid] = progress
            try:
                if self._sem.locked():
                    await self._announce_queue()
                async with self._sem:
                    self._waiting.remove(sid)
                    await self._announce_queue()
                    self.running += 1
                    try:
                        await work()
                    finally:
                        self.running -= 1
            finally:
                if sid in self._waiting:
                    self._waiting.remove(sid)
                self._progress.pop(sid, None)
                self._tasks.pop(sid, None)

        self._tasks[sid] = asyncio.create_task(runner())

    async def shutdown(self) -> None:
        for task in list(self._tasks.values()):
            task.cancel()


scheduler = JobScheduler()
