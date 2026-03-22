from __future__ import annotations

import asyncio
import json
import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.bot import notify_user
from app.pipeline import run_pipeline
from app.schemas import WrappedData
from app.telegram_service import get_session

log = logging.getLogger("wrapped.router")

router = APIRouter()


class StartRequest(BaseModel):
    session_id: str
    utc_offset_minutes: int = 0  # browser's getTimezoneOffset() negated: +480 for SGT (UTC+8)


@router.post("/wrapped/start", status_code=202)
async def start_pipeline(body: StartRequest) -> dict[str, str]:
    session = get_session(body.session_id)
    if session is None:
        raise HTTPException(404, "Session not found or expired")
    if not session.authenticated:
        raise HTTPException(400, "Session not authenticated")
    if session.pipeline_task and not session.pipeline_task.done():
        raise HTTPException(409, "Pipeline already running")

    session.progress = {"phase": "init", "message": "Starting..."}
    session.result = None

    def progress_callback(data: dict) -> None:
        session.progress = data

    async def _run() -> None:
        try:
            result = await run_pipeline(session.client, progress_callback, utc_offset_minutes=body.utc_offset_minutes)
            session.result = result
            session.progress = {"phase": "done", "message": "Your Wrapped is ready!"}
            # Notify via bot if user pre-started the bot via deep link
            frontend_url = os.environ.get("FRONTEND_URL", "")
            if frontend_url and session.bot_chat_id:
                result_url = f"{frontend_url}?session={body.session_id}"
                await notify_user(body.session_id, result_url)
        except Exception as e:
            log.exception("Pipeline failed for session %s", body.session_id[:8])
            session.progress = {"phase": "error", "message": str(e)}

    session.pipeline_task = asyncio.create_task(_run())
    return {"status": "started"}


@router.get("/wrapped/progress/{session_id}")
async def stream_progress(session_id: str) -> StreamingResponse:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found or expired")

    async def event_generator():
        last_sent = None
        while True:
            current = session.progress
            if current != last_sent:
                yield f"data: {json.dumps(current)}\n\n"
                last_sent = dict(current) if current else None
                if current and current.get("phase") in ("done", "error"):
                    break
            await asyncio.sleep(0.5)

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
async def get_result(session_id: str) -> WrappedData:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found or expired")
    if session.result is None:
        raise HTTPException(202, "Still processing")
    return WrappedData(**session.result)
