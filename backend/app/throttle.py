"""Adaptive request throttle for the Telegram API.

Telegram does not publish its rate limits; it answers with FLOOD_WAIT_X when a
client goes too fast. Instead of guessing a fixed concurrency, this throttle
uses AIMD (additive increase, multiplicative decrease) — the same strategy TCP
uses for congestion control:

* every ``grow_every`` successful calls the concurrency limit grows by one,
  up to ``max_limit``;
* a FloodWait halves the limit and pauses *all* callers for the requested
  time (one shared pause, not N independent ones).

On top of that it enforces a soft *deadline*. Optional work (extra pages,
avatars, thumbnails) is abandoned once the deadline passes or when Telegram
asks for a wait longer than ``max_wait``, so a heavy account degrades to
slightly-less-exact statistics instead of hanging for minutes.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable

from telethon import errors

log = logging.getLogger("wrapped.throttle")


class BudgetExceeded(Exception):
    """Raised for optional requests once the time budget is spent or a flood
    wait would take longer than the caller is willing to wait."""


_FLOOD = (errors.FloodWaitError, errors.FloodPremiumWaitError)

_TRANSIENT = (
    errors.ServerError,
    errors.TimedOutError,
    ConnectionError,
    asyncio.TimeoutError,
)


class AdaptiveThrottle:
    def __init__(
        self,
        initial_limit: int = 4,
        max_limit: int = 16,
        min_limit: int = 1,
        delay: float = 0.0,
        grow_every: int = 20,
        max_wait: float = 30.0,
        deadline: float | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = max(min_limit, min(initial_limit, max_limit))
        self.max_limit = max_limit
        self.min_limit = min_limit
        self.delay = delay
        self.grow_every = grow_every
        self.max_wait = max_wait
        self._clock = clock
        self._deadline = deadline
        self._in_flight = 0
        self._cond = asyncio.Condition()
        self._resume_at = 0.0
        self._streak = 0

        # Metrics
        self.calls = 0
        self.flood_waits = 0
        self.flood_seconds = 0.0

    # ------------------------------------------------------------------
    def set_deadline(self, seconds_from_now: float | None) -> None:
        self._deadline = None if seconds_from_now is None else self._clock() + seconds_from_now

    def deadline_passed(self) -> bool:
        return self._deadline is not None and self._clock() >= self._deadline

    # ------------------------------------------------------------------
    async def _acquire(self) -> None:
        async with self._cond:
            await self._cond.wait_for(lambda: self._in_flight < self.limit)
            self._in_flight += 1

    async def _release(self) -> None:
        async with self._cond:
            self._in_flight -= 1
            self._cond.notify_all()

    async def _on_success(self) -> None:
        self._streak += 1
        if self._streak >= self.grow_every and self.limit < self.max_limit:
            self._streak = 0
            async with self._cond:
                self.limit += 1
                self._cond.notify_all()

    def _on_flood(self, seconds: float) -> None:
        self.flood_waits += 1
        self.flood_seconds += seconds
        self._streak = 0
        new_limit = max(self.min_limit, self.limit // 2)
        if new_limit != self.limit:
            log.info("FloodWait %ss: concurrency %d -> %d", seconds, self.limit, new_limit)
        self.limit = new_limit
        self._resume_at = max(self._resume_at, self._clock() + seconds)

    async def _wait_for_pause(self, essential: bool) -> None:
        remaining = self._resume_at - self._clock()
        if remaining <= 0:
            return
        if not essential and (remaining > self.max_wait or self._would_cross_deadline(remaining)):
            raise BudgetExceeded(f"paused for {remaining:.0f}s")
        await asyncio.sleep(remaining)

    def _would_cross_deadline(self, seconds: float) -> bool:
        return self._deadline is not None and self._clock() + seconds > self._deadline

    # ------------------------------------------------------------------
    async def run(
        self,
        coro_fn: Callable[[], Awaitable[Any]],
        *,
        essential: bool = False,
        retries: int = 4,
    ) -> Any:
        """Run ``coro_fn()`` under the throttle.

        ``coro_fn`` must return a *fresh* awaitable on each call so it can be
        retried. Non-essential calls raise :class:`BudgetExceeded` instead of
        waiting past the deadline or longer than ``max_wait``.
        """
        attempt = 0
        while True:
            if not essential and self.deadline_passed():
                raise BudgetExceeded("deadline passed")
            await self._wait_for_pause(essential)
            await self._acquire()
            try:
                self.calls += 1
                result = await coro_fn()
            except _FLOOD as e:
                seconds = float(getattr(e, "seconds", 1) or 1)
                self._on_flood(seconds)
                attempt += 1
                if attempt > retries:
                    raise
                continue
            except _TRANSIENT as e:
                attempt += 1
                if attempt > retries:
                    raise
                log.debug("Transient error %s, retry %d", type(e).__name__, attempt)
                await asyncio.sleep(min(2 ** attempt * 0.25, 4))
                continue
            finally:
                if self.delay:
                    await asyncio.sleep(self.delay)
                await self._release()
            await self._on_success()
            return result
