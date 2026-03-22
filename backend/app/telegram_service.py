from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from telethon import TelegramClient, errors

log = logging.getLogger("wrapped.service")


def _get_api_credentials() -> tuple[int, str]:
    api_id = int(os.environ.get("TELEGRAM_API_ID", "0"))
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")
    if api_id == 0 or not api_hash:
        raise RuntimeError(
            "TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment / .env file"
        )
    return api_id, api_hash

SESSION_TTL = 14400  # 4 hours — enough for pipeline + user returning from bot notification
CLEANUP_INTERVAL = 60  # seconds


@dataclass
class UserSession:
    session_id: str
    client: TelegramClient
    tmp_dir: str
    phone: str = ""
    phone_code_hash: str = ""
    authenticated: bool = False
    created_at: float = field(default_factory=time.time)
    progress: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    pipeline_task: asyncio.Task | None = None  # type: ignore[type-arg]
    verify_attempts: int = 0
    bot_chat_id: int | None = None  # set when user starts the bot via deep link


_sessions: dict[str, UserSession] = {}
_cleanup_task: asyncio.Task | None = None  # type: ignore[type-arg]


def _validate_phone(phone: str) -> str:
    import re

    cleaned = phone.strip().replace(" ", "").replace("-", "")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    if not re.match(r"^\+[1-9]\d{6,14}$", cleaned):
        raise ValueError("Invalid phone number format")
    return cleaned


def _validate_code(code: str) -> str:
    import re

    cleaned = code.strip()
    if not re.match(r"^\d{4,6}$", cleaned):
        raise ValueError("Verification code must be 4-6 digits")
    return cleaned


async def create_session(phone: str) -> UserSession:
    phone = _validate_phone(phone)
    api_id, api_hash = _get_api_credentials()

    session_id = str(uuid.uuid4())
    tmp_dir = tempfile.mkdtemp(prefix="tg_wrapped_")
    session_path = os.path.join(tmp_dir, "session")

    client = TelegramClient(session_path, api_id, api_hash, flood_sleep_threshold=0)
    await client.connect()

    try:
        sent = await client.send_code_request(phone)
    except errors.PhoneNumberInvalidError:
        await client.disconnect()
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ValueError(
            "Invalid phone number. Please check the number and try again."
        )

    session = UserSession(
        session_id=session_id,
        client=client,
        tmp_dir=tmp_dir,
        phone=phone,
        phone_code_hash=sent.phone_code_hash,
    )
    _sessions[session_id] = session
    log.info("Session %s created for phone %s***", session_id[:8], phone[:6])
    return session


async def verify_session(
    session_id: str, phone: str, code: str, phone_code_hash: str
) -> bool:
    session = get_session(session_id)
    if session is None:
        raise ValueError("Session not found or expired")

    session.verify_attempts += 1
    if session.verify_attempts > 5:
        await destroy_session(session_id)
        raise ValueError("Too many verification attempts")

    phone = _validate_phone(phone)
    code = _validate_code(code)

    try:
        await session.client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        session.authenticated = True
        log.info("Session %s authenticated", session_id[:8])
        return True
    except errors.SessionPasswordNeededError:
        raise ValueError("Two-factor authentication is enabled. Please disable it temporarily to use Telegram Wrapped.")
    except errors.PhoneCodeInvalidError:
        raise ValueError("Invalid verification code")
    except errors.PhoneCodeExpiredError:
        raise ValueError("Verification code expired. Please request a new one.")


def get_session(session_id: str) -> UserSession | None:
    return _sessions.get(session_id)


async def destroy_session(session_id: str) -> None:
    session = _sessions.pop(session_id, None)
    if session is None:
        return

    if session.pipeline_task and not session.pipeline_task.done():
        session.pipeline_task.cancel()

    try:
        await session.client.disconnect()
    except Exception:
        pass

    try:
        shutil.rmtree(session.tmp_dir, ignore_errors=True)
    except Exception:
        pass

    log.info("Session %s destroyed", session_id[:8])


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        now = time.time()
        expired = []
        for sid, s in _sessions.items():
            if now - s.created_at <= SESSION_TTL:
                continue
            if s.pipeline_task and not s.pipeline_task.done():
                log.debug("Skipping purge of %s — pipeline still running", sid[:8])
                continue
            if s.result is not None and s.bot_chat_id is not None:
                # Keep results alive until the user retrieves them (up to 2x TTL)
                if now - s.created_at <= SESSION_TTL * 2:
                    log.debug("Skipping purge of %s — result pending bot retrieval", sid[:8])
                    continue
            expired.append(sid)
        for sid in expired:
            log.info("Auto-purging expired session %s", sid[:8])
            await destroy_session(sid)


def start_cleanup_task() -> None:
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_loop())


_rate_store: dict[str, list[float]] = {}
_RATE_LIMIT = int(os.environ.get("RATE_LIMIT_SEND_CODE", "10"))
_RATE_WINDOW = 600  # 10-minute window


def get_send_code_rate(ip: str) -> bool:
    """Simple in-memory rate limiter for send-code. Returns True if allowed."""
    now = time.time()
    key = f"rate:{ip}"
    timestamps = [t for t in _rate_store.get(key, []) if now - t < _RATE_WINDOW]
    if len(timestamps) >= _RATE_LIMIT:
        return False
    timestamps.append(now)
    _rate_store[key] = timestamps
    return True
