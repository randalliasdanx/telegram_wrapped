"""Wrapped pipeline orchestration.

1. Try to open a Takeout (bulk export) session — relaxed rate limits — but
   never block on it: if Telegram asks for an approval delay we continue with
   the standard API immediately.
2. Collect data with :class:`app.fetcher.Fetcher` under an
   :class:`app.throttle.AdaptiveThrottle` with a soft deadline.
3. Compute statistics (pure CPU) off the event loop.
4. Download a handful of images (top chat avatars, sticker thumbnails).
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from concurrent.futures import Executor, ProcessPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine

from telethon import TelegramClient, errors

from app.fetcher import Collected, Fetcher, download_avatar, select_candidate_dialogs
from app.stats import compute_stats
from app.throttle import AdaptiveThrottle, BudgetExceeded

# Re-exported for backwards compatibility (tests and scripts import these here)
from app.text_analysis import (  # noqa: F401
    STOPWORDS,
    _clean_text,
    _clean_text_preserve_case,
    _extract_emojis,
    _get_peak_personality,
    _llr_score,
    _load_background_bigrams,
    _process_text_batch,
)

log = logging.getLogger("wrapped.pipeline")

ProgressCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]] | Callable[[dict[str, Any]], None]


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


# Standard API: Telegram's normal per-account limits
STANDARD = {
    "initial_limit": _env_int("TG_CONCURRENCY", 4),
    "max_limit": _env_int("TG_MAX_CONCURRENCY", 10),
    "page_budget": _env_int("TG_PAGE_BUDGET", 600),  # x100 messages
    "deadline": _env_int("TG_FETCH_DEADLINE", 75),  # seconds for optional work
}
# Takeout: bulk-export session with relaxed limits
TAKEOUT = {
    "initial_limit": _env_int("TG_TAKEOUT_CONCURRENCY", 8),
    "max_limit": _env_int("TG_TAKEOUT_MAX_CONCURRENCY", 24),
    "page_budget": _env_int("TG_TAKEOUT_PAGE_BUDGET", 2000),
    "deadline": _env_int("TG_TAKEOUT_FETCH_DEADLINE", 120),
}
# Seconds we are willing to wait if Telegram delays the takeout session.
# 0 = never wait (fall back to the standard API right away).
TAKEOUT_MAX_WAIT = _env_int("TAKEOUT_MAX_WAIT", 0)
USE_TAKEOUT = os.environ.get("USE_TAKEOUT", "1") != "0"
TOP_AVATARS = 5
TOP_STICKER_IMAGES = 10

# CPU-bound statistics run in a process pool when STATS_WORKERS > 0 (better
# for many concurrent users), otherwise in a thread.
_stats_executor: Executor | None = None


def _get_executor() -> Executor | None:
    global _stats_executor
    workers = _env_int("STATS_WORKERS", 0)
    if workers > 0 and _stats_executor is None:
        _stats_executor = ProcessPoolExecutor(max_workers=workers)
    return _stats_executor


# Backwards-compatible name
_select_candidate_dialogs = select_candidate_dialogs


async def _emit(callback: ProgressCallback | None, data: dict[str, Any]) -> None:
    if callback is None:
        return
    result = callback(data)
    if asyncio.iscoroutine(result):
        await result


def _sniff_mime(data: bytes) -> str:
    if data[:4] == b"RIFF":
        return "image/webp"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return "image/webp"


async def _sticker_image(client: TelegramClient, throttle: AdaptiveThrottle, doc: Any) -> str | None:
    try:
        thumb = 0 if getattr(doc, "thumbs", None) else None
        data = await asyncio.wait_for(
            throttle.run(lambda: client.download_media(doc, file=bytes, thumb=thumb)), 8.0,
        )
    except (BudgetExceeded, asyncio.TimeoutError):
        return None
    except Exception as e:
        log.debug("Sticker thumbnail failed: %s", e)
        return None
    if not data:
        return None
    return f"data:{_sniff_mime(data)};base64,{base64.b64encode(data).decode()}"


async def _attach_images(
    client: TelegramClient, throttle: AdaptiveThrottle, collected: Collected, stats: dict[str, Any],
) -> None:
    """Avatars for the top chats and thumbnails for the top stickers, in parallel."""
    throttle.set_deadline(15)
    by_name = {d.name: d for d in collected.dialogs}

    async def avatar(chat: dict[str, Any]) -> None:
        d = by_name.get(chat["name"])
        if d is not None:
            chat["avatar"] = await download_avatar(client, throttle, d.entity)

    async def sticker(entry: dict[str, Any]) -> None:
        doc = collected.sticker_docs.get(entry["sticker_id"])
        entry["image"] = await _sticker_image(client, throttle, doc) if doc is not None else None

    await asyncio.gather(
        *(avatar(c) for c in stats["top_chats"][:TOP_AVATARS]),
        *(sticker(s) for s in stats["top_stickers"][:TOP_STICKER_IMAGES]),
    )
    for s in stats["top_stickers"]:
        s.pop("sticker_id", None)
        s.setdefault("image", None)


async def _run_phases(
    scan_client: TelegramClient,
    raw_client: TelegramClient,
    callback: ProgressCallback | None,
    start: datetime,
    end: datetime,
    settings: dict[str, int],
    takeout: bool,
    utc_offset_minutes: int = 0,
) -> dict[str, Any]:
    t0 = time.monotonic()
    throttle = AdaptiveThrottle(
        initial_limit=settings["initial_limit"],
        max_limit=settings["max_limit"],
    )

    async def progress(data: dict[str, Any]) -> None:
        data.setdefault("elapsed", round(time.monotonic() - t0, 1))
        await _emit(callback, data)

    dialogs = await throttle.run(lambda: scan_client.get_dialogs(limit=None), essential=True)
    candidates = select_candidate_dialogs(dialogs, start)
    await progress({"phase": "init", "message": f"Found {len(candidates)} chats active this year"})

    # Counting is essential (exact totals); everything after has a soft deadline.
    fetcher = Fetcher(
        scan_client, throttle, start, end, progress,
        page_budget=settings["page_budget"], raw_client=raw_client,
    )
    throttle.set_deadline(settings["deadline"])
    collected = await fetcher.collect(candidates)
    log.info(
        "Collected %d dialogs, %d records, %d API calls, %d flood waits (%.0fs) in %.1fs",
        len(collected.dialogs), fetcher.analyzed, throttle.calls,
        throttle.flood_waits, throttle.flood_seconds, time.monotonic() - t0,
    )

    await progress({"phase": "computing", "message": "Crunching the numbers…", "messages_analyzed": fetcher.analyzed})
    # Strip Telethon objects so the payload is small and picklable
    lean = replace(
        collected,
        dialogs=[replace(d, entity=None, peer=None) for d in collected.dialogs],
        sticker_docs={},
    )
    loop = asyncio.get_running_loop()
    stats = await loop.run_in_executor(
        _get_executor(),
        compute_stats, lean, start, end, utc_offset_minutes, time.monotonic() - t0, takeout,
    )

    await progress({"phase": "computing", "message": "Adding the finishing touches…", "messages_analyzed": fetcher.analyzed})
    await _attach_images(scan_client, throttle, collected, stats)
    stats["accuracy"]["duration_seconds"] = round(time.monotonic() - t0, 1)
    stats["accuracy"]["api_calls"] = throttle.calls
    return stats


async def _try_with_takeout(
    client: TelegramClient,
    callback: ProgressCallback | None,
    start: datetime,
    end: datetime,
    utc_offset_minutes: int = 0,
) -> dict[str, Any] | None:
    """Run inside a Takeout session. Returns None if takeout is unavailable."""
    for attempt in range(2):
        try:
            async with client.takeout(
                users=True, chats=True, megagroups=True, files=True,
                max_file_size=10 * 1024 * 1024,
            ) as takeout:
                log.info("Takeout session acquired")
                await _emit(callback, {"phase": "init", "message": "Export session active — turbo mode!"})
                return await _run_phases(
                    takeout, client, callback, start, end, TAKEOUT, takeout=True,
                    utc_offset_minutes=utc_offset_minutes,
                )
        except errors.TakeoutInitDelayError as e:
            if attempt == 0 and 0 < e.seconds <= TAKEOUT_MAX_WAIT:
                await _emit(callback, {
                    "phase": "init",
                    "message": f"Telegram asked us to wait {e.seconds}s for the export session…",
                })
                await asyncio.sleep(e.seconds)
                continue
            log.info("Takeout delayed by %ss — using standard API", e.seconds)
            return None
        except (errors.FloodWaitError, errors.TakeoutInvalidError, errors.RPCError) as e:
            log.info("Takeout unavailable (%s) — using standard API", type(e).__name__)
            return None
    return None


async def run_pipeline(
    client: TelegramClient,
    callback: ProgressCallback | None = None,
    utc_offset_minutes: int = 0,
) -> dict[str, Any]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365)

    await _emit(callback, {"phase": "init", "message": "Connecting to Telegram…"})

    if USE_TAKEOUT:
        result = await _try_with_takeout(client, callback, start, end, utc_offset_minutes)
        if result is not None:
            return result

    return await _run_phases(
        client, client, callback, start, end, STANDARD, takeout=False,
        utc_offset_minutes=utc_offset_minutes,
    )
