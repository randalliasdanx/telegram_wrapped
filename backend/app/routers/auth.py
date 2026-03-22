from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.telegram_service import (
    create_session,
    get_send_code_rate,
    verify_session,
)

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
    client_ip = request.client.host if request.client else "unknown"
    log.info("send-code request from %s for phone: %s", client_ip, body.phone[:6] + "***")

    if not get_send_code_rate(client_ip):
        raise HTTPException(429, "Too many code requests. Try again in a few minutes.")

    try:
        session = await create_session(body.phone)
    except ValueError as e:
        log.warning("Validation error: %s", e)
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        log.error("Config error: %s", e)
        raise HTTPException(500, str(e))
    except Exception as e:
        log.exception("Failed to send code")
        raise HTTPException(500, f"Failed to send code: {type(e).__name__}: {e}")

    return SendCodeResponse(
        session_id=session.session_id,
        phone_code_hash=session.phone_code_hash,
    )


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
    except Exception as e:
        log.exception("Verification failed")
        raise HTTPException(500, f"Verification failed: {type(e).__name__}: {e}")
