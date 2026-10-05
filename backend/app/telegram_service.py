"""Telegram login sessions.

Sessions are Telethon ``StringSession``s, encrypted with Fernet and kept in
the shared store (memory or Redis) — no SQLite files on disk, and any API
instance can rebuild the client for a request. Connected clients are cached
per process and disconnected when idle.

Privacy: as soon as a Wrapped is generated the Telegram authorization is
revoked (``log_out``) and the encrypted session is deleted. Sessions that are
never used are revoked by the expiry sweeper after ``SESSION_TTL``.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from telethon import TelegramClient, errors
from telethon.sessions import StringSession

from app.store import get_store

log = logging.getLogger("wrapped.service")

SESSION_TTL = int(os.environ.get("SESSION_TTL", "1800"))  # login secret lifetime
RESULT_TTL = int(os.environ.get("RESULT_TTL", str(6 * 3600)))  # finished Wrapped
CLIENT_IDLE_SECONDS = 300  # disconnect cached clients idle this long
CLEANUP_INTERVAL = 30
MAX_VERIFY_ATTEMPTS = 5

_RATE_LIMIT_IP = int(os.environ.get("RATE_LIMIT_SEND_CODE", "10"))
_RATE_LIMIT_PHONE = int(os.environ.get("RATE_LIMIT_SEND_CODE_PHONE", "3"))
_RATE_WINDOW = 600


def _get_api_credentials() -> tuple[int, str]:
    api_id = int(os.environ.get("TELEGRAM_API_ID", "0"))
    api_hash = os.environ.get("TELEGRAM_API_HASH", "")
    if api_id == 0 or not api_hash:
        raise RuntimeError(
            "TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in environment / .env file"
        )
    return api_id, api_hash


# ---------------------------------------------------------------------------
# Encryption of session strings at rest
# ---------------------------------------------------------------------------
_fernet: Fernet | None = None


def _cipher() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.environ.get("SESSION_ENCRYPTION_KEY", "")
        if not key:
            if os.environ.get("REDIS_URL"):
                raise RuntimeError(
                    "SESSION_ENCRYPTION_KEY must be set when REDIS_URL is used "
                    "(generate one with: python -c \"from cryptography.fernet import Fernet; "
                    "print(Fernet.generate_key().decode())\")"
                )
            key = Fernet.generate_key().decode()  # per-process key: single instance only
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def _seal(session_string: str) -> str:
    return _cipher().encrypt(session_string.encode()).decode()


def _unseal(token: str) -> str:
    return _cipher().decrypt(token.encode()).decode()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _validate_phone(phone: str) -> str:
    cleaned = phone.strip().replace(" ", "").replace("-", "")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    if not re.match(r"^\+[1-9]\d{6,14}$", cleaned):
        raise ValueError("Invalid phone number format")
    return cleaned


def _validate_code(code: str) -> str:
    cleaned = code.strip()
    if not re.match(r"^\d{4,6}$", cleaned):
        raise ValueError("Verification code must be 4-6 digits")
    return cleaned


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------
def _k_session(sid: str) -> str:
    return f"session:{sid}"


def _k_progress(sid: str) -> str:
    return f"progress:{sid}"


def _k_result(sid: str) -> str:
    return f"result:{sid}"


def _k_botchat(sid: str) -> str:
    return f"botchat:{sid}"


# ---------------------------------------------------------------------------
# Local client cache
# ---------------------------------------------------------------------------
@dataclass
class _Local:
    client: TelegramClient
    last_used: float = field(default_factory=time.time)
    busy: bool = False


_clients: dict[str, _Local] = {}
_cleanup_task: asyncio.Task | None = None  # type: ignore[type-arg]


def _new_client(session_string: str = "") -> TelegramClient:
    api_id, api_hash = _get_api_credentials()
    return TelegramClient(
        StringSession(session_string),
        api_id,
        api_hash,
        flood_sleep_threshold=0,  # FloodWaits are handled by AdaptiveThrottle
        receive_updates=False,  # we never need live updates: less traffic & memory
    )


async def _save_meta(sid: str, meta: dict[str, Any]) -> None:
    await get_store().set_json(_k_session(sid), meta, SESSION_TTL + 600)


async def get_meta(sid: str) -> dict[str, Any] | None:
    return await get_store().get_json(_k_session(sid))


async def get_client(sid: str) -> TelegramClient:
    """Connected client for a session, rebuilt from the store if needed."""
    local = _clients.get(sid)
    if local is not None:
        local.last_used = time.time()
        if not local.client.is_connected():
            await local.client.connect()
        return local.client
    meta = await get_meta(sid)
    if not meta or not meta.get("secret"):
        raise ValueError("Session not found or expired")
    try:
        session_string = _unseal(meta["secret"])
    except InvalidToken:
        raise ValueError("Session not found or expired")
    client = _new_client(session_string)
    await client.connect()
    _clients[sid] = _Local(client=client)
    return client


def mark_busy(sid: str, busy: bool) -> None:
    local = _clients.get(sid)
    if local is not None:
        local.busy = busy
        local.last_used = time.time()


# ---------------------------------------------------------------------------
# Auth flow
# ---------------------------------------------------------------------------
async def check_send_code_rate(ip: str, phone: str) -> bool:
    store = get_store()
    if await store.hit(f"rate:ip:{ip}", _RATE_WINDOW) > _RATE_LIMIT_IP:
        return False
    try:
        normalized = _validate_phone(phone)
    except ValueError:
        return True  # validation error is reported by create_session
    return await store.hit(f"rate:phone:{normalized}", _RATE_WINDOW) <= _RATE_LIMIT_PHONE


async def create_session(phone: str) -> tuple[str, str]:
    """Send the login code. Returns (session_id, phone_code_hash)."""
    phone = _validate_phone(phone)
    client = _new_client()
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
    except errors.PhoneNumberInvalidError:
        await client.disconnect()
        raise ValueError("Invalid phone number. Please check the number and try again.")
    except errors.FloodWaitError as e:
        await client.disconnect()
        raise ValueError(f"Telegram is rate limiting login codes. Try again in {e.seconds} seconds.")
    except Exception:
        await client.disconnect()
        raise

    sid = str(uuid.uuid4())
    now = time.time()
    await _save_meta(sid, {
        "phone": phone,
        "phone_code_hash": sent.phone_code_hash,
        "authenticated": False,
        "verify_attempts": 0,
        "created_at": now,
        "secret": _seal(client.session.save()),
    })
    await get_store().schedule(sid, now + SESSION_TTL)
    _clients[sid] = _Local(client=client)
    log.info("Session %s created for phone %s***", sid[:8], phone[:4])
    return sid, sent.phone_code_hash


async def verify_session(sid: str, phone: str, code: str, phone_code_hash: str) -> bool:
    meta = await get_meta(sid)
    if meta is None or not meta.get("secret"):
        raise ValueError("Session not found or expired")

    meta["verify_attempts"] = meta.get("verify_attempts", 0) + 1
    await _save_meta(sid, meta)
    if meta["verify_attempts"] > MAX_VERIFY_ATTEMPTS:
        await destroy_session(sid)
        raise ValueError("Too many verification attempts")

    phone = _validate_phone(phone)
    code = _validate_code(code)
    if phone != meta["phone"]:
        raise ValueError("Phone number does not match this session")

    client = await get_client(sid)
    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash or meta["phone_code_hash"])
    except errors.SessionPasswordNeededError:
        raise ValueError(
            "Two-factor authentication is enabled. Please disable it temporarily to use Telegram Wrapped."
        )
    except errors.PhoneCodeInvalidError:
        raise ValueError("Invalid verification code")
    except errors.PhoneCodeExpiredError:
        raise ValueError("Verification code expired. Please request a new one.")

    meta["authenticated"] = True
    meta["secret"] = _seal(client.session.save())
    await _save_meta(sid, meta)
    log.info("Session %s authenticated", sid[:8])
    return True


async def destroy_session(sid: str, revoke: bool = True) -> None:
    """Revoke the Telegram authorization and forget the login secret.
    Progress and results (if any) are kept until RESULT_TTL."""
    store = get_store()
    local = _clients.pop(sid, None)
    client = local.client if local else None
    if client is None and revoke:
        meta = await get_meta(sid)
        if meta and meta.get("secret") and meta.get("authenticated"):
            try:
                client = _new_client(_unseal(meta["secret"]))
                await client.connect()
            except Exception as e:
                log.debug("Could not rebuild client for revoke: %s", e)
                client = None
    if client is not None:
        try:
            if revoke and await client.is_user_authorized():
                await client.log_out()  # removes the session from the user's devices list
                log.info("Session %s revoked", sid[:8])
        except Exception as e:
            log.debug("log_out failed for %s: %s", sid[:8], e)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
    await store.delete(_k_session(sid))
    await store.unschedule(sid)


# ---------------------------------------------------------------------------
# Progress / results / bot mapping
# ---------------------------------------------------------------------------
async def set_progress(sid: str, data: dict[str, Any]) -> None:
    data = {**data, "updated_at": time.time()}
    await get_store().set_json(_k_progress(sid), data, RESULT_TTL)


async def get_progress(sid: str) -> dict[str, Any] | None:
    return await get_store().get_json(_k_progress(sid))


async def set_result(sid: str, result: dict[str, Any]) -> None:
    await get_store().set_json(_k_result(sid), result, RESULT_TTL)


async def get_result(sid: str) -> dict[str, Any] | None:
    return await get_store().get_json(_k_result(sid))


async def set_bot_chat(sid: str, chat_id: int) -> None:
    await get_store().set_json(_k_botchat(sid), chat_id, RESULT_TTL)


async def get_bot_chat(sid: str) -> int | None:
    return await get_store().get_json(_k_botchat(sid))


# ---------------------------------------------------------------------------
# Background maintenance
# ---------------------------------------------------------------------------
async def _cleanup_once() -> None:
    now = time.time()
    # 1. Expired login sessions (claimed atomically across instances)
    store = get_store()
    for sid in await store.claim_due(now):
        local = _clients.get(sid)
        progress = await get_progress(sid)
        running_anywhere = bool(
            progress
            and progress.get("phase") not in ("done", "error")
            and now - progress.get("updated_at", 0) < 180
        )
        if (local is not None and local.busy) or running_anywhere:
            await store.schedule(sid, now + 300)  # pipeline still running (maybe on another instance)
            continue
        log.info("Expiring session %s", sid[:8])
        await destroy_session(sid)
    # 2. Idle connected clients in this process
    for sid, local in list(_clients.items()):
        if not local.busy and now - local.last_used > CLIENT_IDLE_SECONDS:
            _clients.pop(sid, None)
            try:
                await local.client.disconnect()
            except Exception:
                pass


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        try:
            await _cleanup_once()
        except Exception:
            log.exception("Session cleanup failed")


def start_cleanup_task() -> None:
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_loop())


async def shutdown() -> None:
    if _cleanup_task is not None:
        _cleanup_task.cancel()
    for sid, local in list(_clients.items()):
        try:
            await local.client.disconnect()
        except Exception:
            pass
    _clients.clear()
