"""Telegram Bot worker for Telegram Wrapped.

Responsibilities:
- Handle /start <session_id> (deep-link flow) — store chat_id → session_id mapping
- Notify users via bot message when their Wrapped is ready

Usage:
  Set BOT_TOKEN in .env
  Set APP_URL to your deployed frontend URL (e.g. https://telegramwrapped.com)
  The bot starts automatically on FastAPI startup if BOT_TOKEN is set.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

log = logging.getLogger("wrapped.bot")

# session_id -> chat_id mapping (in-memory for v1)
_session_to_chat: dict[str, int] = {}

_app: Any = None  # telegram.ext.Application instance


async def _start_command(update: Any, context: Any) -> None:
    """Handle /start [session_id] — the deep-link entry point.

    When a user clicks the Start-Bot CTA on the waiting page, they arrive
    at t.me/BotUsername?start=SESSION_ID. Telegram passes SESSION_ID as
    the first argument to /start.
    """
    from app.telegram_service import get_session

    chat_id = update.effective_chat.id
    args = context.args or []

    if args:
        session_id = args[0].strip()
        _session_to_chat[session_id] = chat_id
        # Also store on the session object so the pipeline completion handler can use it
        session = get_session(session_id)
        if session is not None:
            session.bot_chat_id = chat_id
            log.info("Bot: registered chat_id=%d for session %s***", chat_id, session_id[:8])
            await update.message.reply_text(
                "You're all set! 🎉\n\n"
                "We'll send you a message right here when your Telegram Wrapped is ready. "
                "You can close the browser tab now.",
            )
        else:
            log.warning("Bot: /start with unknown session %s***", session_id[:8])
            await update.message.reply_text(
                "This link has expired or is invalid. Please restart from the website.",
            )
    else:
        await update.message.reply_text(
            "👋 Welcome to Telegram Wrapped!\n\n"
            "Head to our website to get started and we'll ping you here when your results are ready.",
        )


async def notify_user(session_id: str, result_url: str) -> bool:
    """Send result notification to a user who pre-started the bot.

    Returns True if the message was sent successfully.
    """
    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        return False

    chat_id = _session_to_chat.get(session_id)
    if chat_id is None:
        log.info("Bot: no chat_id registered for session %s*** — skipping notification", session_id[:8])
        return False

    try:
        from telegram import Bot

        async with Bot(token=bot_token) as bot:
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "Your Telegram Wrapped is ready! 🎉\n\n"
                    f"See your results here: {result_url}"
                ),
            )
        log.info("Bot: notified chat_id=%d for session %s***", chat_id, session_id[:8])
        return True
    except Exception as e:
        log.warning("Bot: failed to notify session %s***: %s", session_id[:8], e)
        return False


async def start_bot() -> None:
    """Start the bot in polling mode. No-ops if BOT_TOKEN is not set."""
    global _app

    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        log.info("BOT_TOKEN not configured — bot will not start")
        return

    try:
        from telegram.ext import Application, CommandHandler

        _app = Application.builder().token(bot_token).build()
        _app.add_handler(CommandHandler("start", _start_command))
        await _app.initialize()
        await _app.start()
        await _app.updater.start_polling()
        log.info("Telegram bot started (polling)")
    except Exception as e:
        log.error("Failed to start Telegram bot: %s", e)
        _app = None


async def stop_bot() -> None:
    """Gracefully shut down the bot polling loop."""
    global _app
    if _app is None:
        return
    try:
        await _app.updater.stop()
        await _app.stop()
        await _app.shutdown()
        log.info("Telegram bot stopped")
    except Exception as e:
        log.warning("Error stopping bot: %s", e)
    finally:
        _app = None
