from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.bot import start_bot, stop_bot
from app.routers import auth, wrapped
from app.jobs import scheduler
from app.telegram_service import shutdown as shutdown_sessions, start_cleanup_task

log = logging.getLogger("wrapped.main")
log.info("TELEGRAM_API_ID loaded: %s", "yes" if os.environ.get("TELEGRAM_API_ID") else "NO")

app = FastAPI(title="Telegram Wrapped API")

APP_ENV = os.environ.get("APP_ENV", "development")
CORS_ORIGIN = os.environ.get("CORS_ORIGIN", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN] if APP_ENV == "production" else ["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:  # type: ignore[type-arg]
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if APP_ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.on_event("startup")
async def on_startup() -> None:
    start_cleanup_task()
    await start_bot()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await scheduler.shutdown()
    await shutdown_sessions()
    await stop_bot()


app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(wrapped.router, prefix="/api", tags=["wrapped"])
