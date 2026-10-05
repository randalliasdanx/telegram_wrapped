"""Run the Wrapped pipeline against your own Telegram account and report
speed, API usage and a ground-truth spot check.

    cd backend
    python -m scripts.live_check            # interactive login (phone + code)
    python -m scripts.live_check --verify 3  # also recount the top 3 chats by iterating

Credentials come from backend/.env (TELEGRAM_API_ID / TELEGRAM_API_HASH).
The temporary login is logged out at the end.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.pipeline import run_pipeline  # noqa: E402


async def main(verify: int, keep: bool) -> None:
    client = TelegramClient(StringSession(), int(os.environ["TELEGRAM_API_ID"]), os.environ["TELEGRAM_API_HASH"],
                            flood_sleep_threshold=0, receive_updates=False)
    await client.start()
    try:
        t0 = time.monotonic()

        def progress(p: dict) -> None:
            print(f"  [{time.monotonic() - t0:5.1f}s] {p.get('phase'):<13} {p.get('message', '')}"
                  f"  ({p.get('messages_analyzed', '-')} msgs)")

        result = await run_pipeline(client, progress, utc_offset_minutes=int(-time.timezone / 60))
        acc = result["accuracy"]
        print("\n=== Summary ===")
        print(json.dumps(acc, indent=2))
        print(f"messages sent: {result['grand_total']:,}  chats: {result['total_chats']}  "
              f"peak hour: {result['peak_hour']}:00  streak: {result['longest_streak']}d")

        if verify:
            print(f"\n=== Ground truth for top {verify} chats (iterating every message) ===")
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=365)
            dialogs = {d.name: d for d in await client.get_dialogs()}
            for chat in result["top_chats"][:verify]:
                d = dialogs.get(chat["name"])
                if d is None:
                    continue
                n = 0
                async for m in client.iter_messages(d.entity, offset_date=end, wait_time=1):
                    if m.date < start:
                        break
                    if m.out:
                        n += 1
                flag = "OK " if n == chat["sent"] else "DIFF"
                print(f"  {flag} {chat['name'][:24]:<24} pipeline={chat['sent']:>7,}  actual={n:>7,}")
        if keep:
            Path("live_result.json").write_text(json.dumps(result, indent=2, default=str))
            print("\nSaved live_result.json")
    finally:
        await client.log_out()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", type=int, default=0, help="recount N top chats by full iteration")
    ap.add_argument("--keep", action="store_true", help="save the result JSON")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    asyncio.run(main(args.verify, args.keep))
