from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.telegram_service import (
    check_send_code_rate,
    create_session,
    verify_session,
)

TRUST_PROXY = os.environ.get("TRUST_PROXY", "0") == "1"


def client_ip(request: Request) -> str:
    if TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


log = logging.getLogger("wrapped.auth")

router = APIRouter()


class SendCodeRequest(BaseModel):
    phone: str


class SendCodeResponse(BaseModel):
    session_id: str
    phone_code_hash: str


class VerifyCodeRequest(BaseModel):
    session_id: str
    phone: str
    code: str
    phone_code_hash: str


class VerifyCodeResponse(BaseModel):
    success: bool


@router.post("/auth/send-code", response_model=SendCodeResponse)
async def send_code(body: SendCodeRequest, request: Request) -> SendCodeResponse:
    ip = client_ip(request)
    log.info("send-code request from %s for phone: %s", ip, body.phone[:4] + "***")

    if not await check_send_code_rate(ip, body.phone):
        raise HTTPException(429, "Too many code requests. Try again in a few minutes.")

    try:
        session_id, phone_code_hash = await create_session(body.phone)
    except ValueError as e:
        log.warning("Validation error: %s", e)
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        log.error("Config error: %s", e)
        raise HTTPException(500, "Telegram API credentials are missing on the server. Set TELEGRAM_API_ID and TELEGRAM_API_HASH in backend/.env and restart.")
    except Exception:
        log.exception("Failed to send code")
        raise HTTPException(502, "Could not reach Telegram. Please try again.")

    return SendCodeResponse(session_id=session_id, phone_code_hash=phone_code_hash)


@router.post("/auth/verify-code", response_model=VerifyCodeResponse)
async def verify_code(body: VerifyCodeRequest) -> VerifyCodeResponse:
    try:
        success = await verify_session(
            body.session_id, body.phone, body.code, body.phone_code_hash
        )
        return VerifyCodeResponse(success=success)
    except ValueError as e:
        log.warning("Verify error: %s", e)
        raise HTTPException(400, str(e))
    except Exception:
        log.exception("Verification failed")
        raise HTTPException(502, "Verification failed. Please try again.")
