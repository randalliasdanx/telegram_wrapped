from telethon import TelegramClient
from datetime import datetime, timezone
import time

api_id = 22086571
api_hash = '708287ed93c834dcd8ff7edf21aa1800'
client = TelegramClient('anon', api_id, api_hash)

start = datetime(2025, 2, 28, tzinfo=timezone.utc)
end = datetime(2026, 2, 28, tzinfo=timezone.utc)

total_messages = 0

async def main():
    global total_messages

    dialogs = await client.get_dialogs()
    start_time = time.perf_counter()
    for d in dialogs:
        async for msg in client.iter_messages(d.entity):
            print(d)
            print(msg)
            total_messages += 1
            break
        break

    print(total_messages)
    print(time.perf_counter() - start_time)

with client:
    client.loop.run_until_complete(main())