from telethon import TelegramClient 
from datetime import datetime, timezone
import time

api_id = 22086571
api_hash = '708287ed93c834dcd8ff7edf21aa1800'
client = TelegramClient('anon', api_id, api_hash)

start = datetime(2025, 2, 28, tzinfo=timezone.utc)
end = datetime(2026, 2, 28, tzinfo=timezone.utc)

async def main():
    dialogs = await client.get_dialogs()
    for dialog in dialogs[1]:
        start = time.perf_counter()
        dialog_ent = dialog.entity
        count = 0
        async for message in client.iter_messages(dialog_ent):
            count += 1
            if count == 1:
                break
        elapsed = time.perf_counter() - start 
        print(f"{elapsed} ms")

with client:
    client.loop.run_until_complete(main())