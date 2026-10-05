from __future__ import annotations

import asyncio
import json
import logging
import os
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.bot import notify_user
from app.jobs import scheduler
from app.pipeline import run_pipeline
from app.schemas import WrappedData
from app.telegram_service import (
    destroy_session,
    get_client,
    get_meta,
    get_progress,
    get_result,
    mark_busy,
    set_progress,
    set_result,
)

log = logging.getLogger("wrapped.router")

router = APIRouter()

ACTIVE_PHASES = {"queued", "init", "counting", "fetching", "conversations", "computing"}
STALE_AFTER = 180  # seconds without a progress update => the worker died
HEARTBEAT_EVERY = 20


class StartRequest(BaseModel):
    session_id: str
    utc_offset_minutes: int = 0  # browser's getTimezoneOffset() negated: +480 for SGT (UTC+8)


def _is_live(progress: dict | None) -> bool:
    return bool(
        progress
        and progress.get("phase") in ACTIVE_PHASES
        and time.time() - progress.get("updated_at", 0) < STALE_AFTER
    )


@router.post("/wrapped/start", status_code=202)
async def start_pipeline(body: StartRequest) -> dict[str, str]:
    sid = body.session_id
    if not -14 * 60 <= body.utc_offset_minutes <= 14 * 60:
        raise HTTPException(400, "Invalid UTC offset")
    if await get_result(sid) is not None:
        return {"status": "done"}
    meta = await get_meta(sid)
    if meta is None:
        raise HTTPException(404, "Session not found or expired")
    if not meta.get("authenticated"):
        raise HTTPException(400, "Session not authenticated")
    if scheduler.is_active(sid) or _is_live(await get_progress(sid)):
        raise HTTPException(409, "Pipeline already running")

    async def progress(data: dict) -> None:
        await set_progress(sid, data)

    async def work() -> None:
        last = {"t": time.time(), "data": {"phase": "init", "message": "Starting…"}}

        async def track(data: dict) -> None:
            last["t"], last["data"] = time.time(), data
            await progress(data)

        async def heartbeat() -> None:
            while True:
                await asyncio.sleep(HEARTBEAT_EVERY)
                if time.time() - last["t"] >= HEARTBEAT_EVERY:
                    await progress(last["data"])

        hb = asyncio.create_task(heartbeat())
        mark_busy(sid, True)
        try:
            client = await get_client(sid)
            result = await run_pipeline(client, track, utc_offset_minutes=body.utc_offset_minutes)
            WrappedData(**result)  # validate before publishing
            await set_result(sid, result)
            await progress({"phase": "done", "message": "Your Wrapped is ready!"})
            log.info("Pipeline done for %s in %ss", sid[:8], result.get("accuracy", {}).get("duration_seconds"))
            # Privacy: revoke the Telegram authorization as soon as we're done
            mark_busy(sid, False)
            await destroy_session(sid)
            frontend_url = os.environ.get("FRONTEND_URL", "")
            if frontend_url:
                await notify_user(sid, f"{frontend_url}?session={sid}")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("Pipeline failed for session %s", sid[:8])
            message = str(e) if isinstance(e, ValueError) else "Something went wrong while reading your chats. Please try again."
            await progress({"phase": "error", "message": message})
        finally:
            hb.cancel()
            mark_busy(sid, False)

    await progress({"phase": "queued", "message": "Getting ready…"})
    scheduler.submit(sid, work, progress)
    return {"status": "started"}


@router.get("/wrapped/status/{session_id}")
async def get_status(session_id: str) -> dict:
    progress = await get_progress(session_id)
    if progress is None:
        if await get_result(session_id) is not None:
            return {"phase": "done", "message": "Your Wrapped is ready!"}
        raise HTTPException(404, "Session not found or expired")
    if progress.get("phase") in ACTIVE_PHASES and not _is_live(progress):
        return {"phase": "error", "message": "Processing was interrupted. Please try again."}
    return progress


@router.get("/wrapped/progress/{session_id}")
async def stream_progress(session_id: str) -> StreamingResponse:
    if await get_progress(session_id) is None and await get_meta(session_id) is None:
        raise HTTPException(404, "Session not found or expired")

    async def event_generator():
        last_sent = None
        idle = 0.0
        while True:
            current = await get_progress(session_id)
            if current is not None and current.get("phase") in ACTIVE_PHASES and not _is_live(current):
                current = {"phase": "error", "message": "Processing was interrupted. Please try again."}
            comparable = {k: v for k, v in (current or {}).items() if k != "updated_at"}
            if current is not None and comparable != last_sent:
                yield f"data: {json.dumps(comparable)}\n\n"
                last_sent = comparable
                idle = 0.0
                if current.get("phase") in ("done", "error"):
                    break
            elif idle >= 15:
                yield ": keep-alive\n\n"  # keeps proxies from closing the stream
                idle = 0.0
            await asyncio.sleep(0.5)
            idle += 0.5

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/wrapped/result/{session_id}", response_model=WrappedData)
async def fetch_result(session_id: str) -> WrappedData:
    result = await get_result(session_id)
    if result is None:
        if _is_live(await get_progress(session_id)):
            raise HTTPException(409, "Still processing")
        raise HTTPException(404, "Result not found or expired")
    return WrappedData(**result)


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", **scheduler.stats()}
