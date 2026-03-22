import asyncio
import logging
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient, errors
from telethon.tl.types import (
    InputMessagesFilterPhotos,
    InputMessagesFilterVideo,
    InputMessagesFilterVoice,
    InputMessagesFilterGif,
    InputMessagesFilterDocument,
    InputMessagesFilterMusic,
    InputMessagesFilterUrl,
    InputMessagesFilterRoundVideo,
)

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("wrapped")

# =========================
# CONFIG
# =========================
api_id = 22086571
api_hash = '708287ed93c834dcd8ff7edf21aa1800'
session_name = "telegram_wrapped"

START = datetime(2025, 2, 28, tzinfo=timezone.utc)
END = datetime(2026, 2, 28, tzinfo=timezone.utc)

USE_TAKEOUT = True
SAMPLES_PER_MONTH = 100
TOP_DIALOGS_TO_SAMPLE = 20
API_DELAY = 0.35  # seconds between API calls to avoid FloodWait penalties

MEDIA_FILTERS = [
    ("photos", InputMessagesFilterPhotos()),
    ("videos", InputMessagesFilterVideo()),
    ("voice_notes", InputMessagesFilterVoice()),
    ("round_videos", InputMessagesFilterRoundVideo()),
    ("gifs", InputMessagesFilterGif()),
    ("documents", InputMessagesFilterDocument()),
    ("music", InputMessagesFilterMusic()),
    ("links", InputMessagesFilterUrl()),
]

# =========================
# CLIENT
# =========================
client = TelegramClient(session_name, api_id, api_hash)

# =========================
# TEXT PROCESSING
# =========================
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "to", "of", "in", "on", "for",
    "is", "it", "this", "that", "i", "you", "we", "he", "she", "they", "me",
    "my", "your", "our", "us", "am", "are", "was", "were", "be", "been",
}

URL_RE = re.compile(r"https?://\S+|www\.\S+")
PUNCT_RE = re.compile(r"[^\w\s]")
SPACE_RE = re.compile(r"\s+")
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]",
    flags=re.UNICODE,
)


def clean_text(text: str) -> str:
    text = text.lower()
    text = URL_RE.sub(" ", text)
    text = PUNCT_RE.sub(" ", text)
    text = SPACE_RE.sub(" ", text).strip()
    return text


def extract_emojis(raw_text: str) -> list[str]:
    return EMOJI_RE.findall(raw_text)


def process_text_batch(texts: list[str]) -> dict:
    """Process a batch of message texts. Returns counters instead of mutating globals."""
    words = Counter()
    bigrams = Counter()
    emojis = Counter()

    for text in texts:
        emojis.update(extract_emojis(text))

        cleaned = clean_text(text)
        if not cleaned:
            continue

        tokens = cleaned.split()
        filtered = [t for t in tokens if len(t) > 1 and not t.isdigit()]

        word_tokens = [t for t in filtered if t not in STOPWORDS]
        if word_tokens:
            words.update(word_tokens)

        for i in range(len(filtered) - 1):
            bigrams[f"{filtered[i]} {filtered[i + 1]}"] += 1

    return {"words": words, "bigrams": bigrams, "emojis": emojis}


# =========================
# PHASE 1: GET COUNTS (fast -- 1 API call per dialog, no message iteration)
# =========================
async def get_dialog_count(scan_client, dialog) -> int | None:
    """Get total message count for a dialog without fetching any messages."""
    try:
        result = await scan_client.get_messages(dialog.entity, limit=0)
        await asyncio.sleep(API_DELAY)
        return result.total
    except errors.FloodWaitError as e:
        log.warning(f"  [FloodWait] counting {dialog.name}: sleeping {e.seconds}s")
        await asyncio.sleep(e.seconds)
        result = await scan_client.get_messages(dialog.entity, limit=0)
        await asyncio.sleep(API_DELAY)
        return result.total
    except Exception as e:
        log.error(f"  [Error] counting {dialog.name}: {type(e).__name__}: {e}")
        return None


async def phase1_count_all_dialogs(scan_client, candidates) -> list[dict]:
    """Get message count for every candidate dialog. ~1 API call each."""
    phase_start = time.perf_counter()
    results = []

    log.info(f"Phase 1: Getting message counts for {len(candidates)} dialogs...")

    for i, dialog in enumerate(candidates):
        name = dialog.name or str(dialog.id)
        count = await get_dialog_count(scan_client, dialog)

        if count is not None and count > 0:
            results.append({
                "dialog": dialog,
                "name": name,
                "total": count,
            })

        if (i + 1) % 10 == 0 or i == len(candidates) - 1:
            elapsed = time.perf_counter() - phase_start
            log.info(f"  Counted {i + 1}/{len(candidates)} dialogs ({elapsed:.1f}s)")

    results.sort(key=lambda r: r["total"], reverse=True)

    elapsed = time.perf_counter() - phase_start
    total_msgs = sum(r["total"] for r in results)
    log.info(
        f"Phase 1 done: {len(results)} active dialogs, "
        f"{total_msgs:,} total messages across all chats, "
        f"{elapsed:.1f}s ({len(candidates) / elapsed:.0f} dialogs/s)"
    )
    return results


# =========================
# PHASE 2: MEDIA BREAKDOWN (fast -- 1 API call per filter per dialog)
# =========================
async def get_media_counts(scan_client, dialog) -> dict[str, int]:
    """Get count of each media type. ~8 API calls, no message content fetched."""
    counts = {}
    for filter_name, filter_obj in MEDIA_FILTERS:
        try:
            result = await scan_client.get_messages(
                dialog.entity, limit=0, filter=filter_obj
            )
            counts[filter_name] = result.total
            await asyncio.sleep(API_DELAY)
        except errors.FloodWaitError as e:
            log.warning(f"    [FloodWait] media count: sleeping {e.seconds}s")
            await asyncio.sleep(e.seconds)
            result = await scan_client.get_messages(
                dialog.entity, limit=0, filter=filter_obj
            )
            counts[filter_name] = result.total
            await asyncio.sleep(API_DELAY)
        except Exception:
            counts[filter_name] = 0
    return counts


async def phase2_media_breakdown(scan_client, dialog_stats, top_n=20) -> None:
    """Add media breakdown to the top N dialogs by message count."""
    phase_start = time.perf_counter()
    to_scan = dialog_stats[:top_n]

    log.info(
        f"Phase 2: Getting media breakdown for top {len(to_scan)} dialogs "
        f"(~{len(to_scan) * len(MEDIA_FILTERS)} API calls)..."
    )

    for i, entry in enumerate(to_scan):
        counts = await get_media_counts(scan_client, entry["dialog"])
        entry["media"] = counts

        log.info(
            f"  [{i + 1}/{len(to_scan)}] {entry['name']}: "
            + ", ".join(f"{k}={v:,}" for k, v in counts.items() if v > 0)
        )

    elapsed = time.perf_counter() - phase_start
    log.info(f"Phase 2 done: {elapsed:.1f}s")


# =========================
# PHASE 3: SAMPLE MESSAGES (moderate -- small number of messages per dialog)
# =========================
async def sample_dialog_messages(
    scan_client, dialog, year_start, year_end, per_month=SAMPLES_PER_MONTH
) -> list:
    """Grab evenly-spaced samples across the year. ~12 API calls per dialog."""
    all_samples = []
    current = year_start

    while current < year_end:
        next_month = current + timedelta(days=32)
        next_month = next_month.replace(day=1)
        if next_month > year_end:
            next_month = year_end

        try:
            msgs = await scan_client.get_messages(
                dialog.entity,
                limit=per_month,
                offset_date=next_month,
            )
            await asyncio.sleep(API_DELAY)
            for msg in msgs:
                if msg.date >= year_start:
                    all_samples.append(msg)
        except errors.FloodWaitError as e:
            log.warning(f"    [FloodWait] sampling: sleeping {e.seconds}s")
            await asyncio.sleep(e.seconds)
            msgs = await scan_client.get_messages(
                dialog.entity,
                limit=per_month,
                offset_date=next_month,
            )
            await asyncio.sleep(API_DELAY)
            for msg in msgs:
                if msg.date >= year_start:
                    all_samples.append(msg)
        except Exception as e:
            log.error(f"    [Error] sampling: {type(e).__name__}: {e}")

        current = next_month

    return all_samples


async def phase3_sample_messages(scan_client, dialog_stats, top_n=TOP_DIALOGS_TO_SAMPLE):
    """Sample messages from top dialogs for deep analysis."""
    phase_start = time.perf_counter()
    to_sample = dialog_stats[:top_n]

    log.info(
        f"Phase 3: Sampling ~{SAMPLES_PER_MONTH * 12} msgs/dialog "
        f"from top {len(to_sample)} dialogs..."
    )

    all_sampled = []
    api_calls = 0

    for i, entry in enumerate(to_sample):
        chat_start = time.perf_counter()
        samples = await sample_dialog_messages(
            scan_client, entry["dialog"], START, END
        )
        api_calls += 12

        entry["sampled_count"] = len(samples)
        all_sampled.extend(samples)

        chat_elapsed = time.perf_counter() - chat_start
        log.info(
            f"  [{i + 1}/{len(to_sample)}] {entry['name']}: "
            f"{len(samples):,} sampled in {chat_elapsed:.1f}s"
        )

    elapsed = time.perf_counter() - phase_start
    log.info(
        f"Phase 3 done: {len(all_sampled):,} total samples "
        f"from {len(to_sample)} dialogs, "
        f"~{api_calls} API calls, {elapsed:.1f}s"
    )
    return all_sampled


# =========================
# PHASE 4: COMPUTE STATS FROM SAMPLES (pure CPU, no API calls)
# =========================
def phase4_compute_stats(dialog_stats, sampled_messages) -> dict:
    """Compute all analytics from counts + samples. Zero API calls."""
    phase_start = time.perf_counter()

    log.info(f"Phase 4: Computing stats from {len(sampled_messages):,} sampled messages...")

    # --- From Phase 1 counts (exact) ---
    grand_total = sum(d["total"] for d in dialog_stats)

    top_chats = [
        {"name": d["name"], "total": d["total"], "pct": d["total"] / grand_total * 100}
        for d in dialog_stats[:10]
    ]

    # --- From Phase 3 samples (statistical) ---
    hour_activity = Counter()
    day_activity = Counter()
    from_ids = Counter()
    raw_texts = []

    for msg in sampled_messages:
        hour_activity[msg.date.hour] += 1
        day_activity[msg.date.date()] += 1

        if hasattr(msg, "from_id") and msg.from_id:
            sender_id = getattr(msg.from_id, "user_id", None) or getattr(msg.from_id, "channel_id", None)
            if sender_id:
                from_ids[sender_id] += 1

        if msg.message:
            raw_texts.append(msg.message)

    # Peak hour
    peak_hour = max(hour_activity, key=hour_activity.get) if hour_activity else None

    # Busiest day
    busiest_day = max(day_activity, key=day_activity.get) if day_activity else None

    # Streak (longest consecutive days with messages in sample)
    if day_activity:
        sorted_days = sorted(day_activity.keys())
        longest_streak = 1
        current_streak = 1
        for i in range(1, len(sorted_days)):
            if (sorted_days[i] - sorted_days[i - 1]).days == 1:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1
    else:
        longest_streak = 0

    # Text analysis
    text_start = time.perf_counter()
    text_results = process_text_batch(raw_texts)
    text_elapsed = time.perf_counter() - text_start

    # Media totals (from Phase 2)
    media_totals = Counter()
    for d in dialog_stats:
        if "media" in d:
            for k, v in d["media"].items():
                media_totals[k] += v

    elapsed = time.perf_counter() - phase_start
    log.info(
        f"Phase 4 done: {elapsed:.2f}s "
        f"(text processing: {text_elapsed:.2f}s for {len(raw_texts):,} texts)"
    )

    return {
        "grand_total": grand_total,
        "top_chats": top_chats,
        "hour_activity": hour_activity,
        "peak_hour": peak_hour,
        "busiest_day": busiest_day,
        "day_activity": day_activity,
        "longest_streak": longest_streak,
        "media_totals": media_totals,
        "words": text_results["words"],
        "bigrams": text_results["bigrams"],
        "emojis": text_results["emojis"],
        "sample_size": len(sampled_messages),
        "text_count": len(raw_texts),
    }


# =========================
# DIALOG FILTERING
# =========================
def select_candidate_dialogs(dialogs):
    selected = []
    skipped_no_message = 0
    skipped_old = 0

    for d in dialogs:
        if not d.message:
            skipped_no_message += 1
            continue
        if d.message.date < START:
            skipped_old += 1
            continue
        selected.append(d)

    log.info(
        f"Dialog filter: {len(selected)} selected, "
        f"{skipped_old} skipped (last msg before {START.date()}), "
        f"{skipped_no_message} skipped (no messages)"
    )
    return selected


# =========================
# DISPLAY RESULTS
# =========================
def display_results(stats, dialog_stats, total_elapsed, phase_timings):
    print("\n" + "=" * 60)
    print("              TELEGRAM WRAPPED STATS")
    print("=" * 60)

    # --- Total messages (exact from counts) ---
    print(f"\nTotal messages: {stats['grand_total']:,}  (exact count)")
    daily_avg = stats["grand_total"] / 365
    print(f"Daily average:  ~{daily_avg:,.0f} messages")

    # --- Top chats (exact from counts) ---
    print(f"\nTop 10 chats:")
    for rank, chat in enumerate(stats["top_chats"], 1):
        bar = "█" * int(chat["pct"] / stats["top_chats"][0]["pct"] * 25)
        print(f"  {rank:>2}. {chat['name']}: {chat['total']:,} ({chat['pct']:.1f}%) {bar}")

    # --- Media breakdown (exact from filter counts) ---
    if stats["media_totals"]:
        print(f"\nMedia breakdown (top {TOP_DIALOGS_TO_SAMPLE} chats):")
        for media_type, count in stats["media_totals"].most_common():
            if count > 0:
                print(f"  {media_type}: {count:,}")

    # --- Hourly distribution (from samples) ---
    if stats["hour_activity"]:
        print(f"\nPeak hour: {stats['peak_hour']:02d}:00")
        print(f"  (based on {stats['sample_size']:,} sampled messages)")
        print("  Hourly distribution:")
        max_h = max(stats["hour_activity"].values())
        for h in range(24):
            c = stats["hour_activity"].get(h, 0)
            bar = "█" * int(c / max_h * 30) if max_h else ""
            print(f"  {h:02d}:00 {bar} {c:,}")

    # --- Streak ---
    if stats["longest_streak"] > 0:
        print(f"\nLongest streak: {stats['longest_streak']} consecutive days")
        print(f"  (from {len(stats['day_activity'])} unique days in sample)")

    # --- Busiest day ---
    if stats["busiest_day"]:
        day = stats["busiest_day"]
        print(f"\nBusiest day (in sample): {day} ({stats['day_activity'][day]:,} msgs)")

    # --- Top words ---
    if stats["words"]:
        print(f"\nTop 20 words (from {stats['text_count']:,} texts):")
        for word, count in stats["words"].most_common(20):
            print(f"  {word}: {count:,}")

    # --- Top bigrams ---
    if stats["bigrams"]:
        print(f"\nTop 20 bigrams:")
        for phrase, count in stats["bigrams"].most_common(20):
            print(f"  {phrase}: {count:,}")

    # --- Top emoji ---
    if stats["emojis"]:
        print(f"\nTop 20 emojis:")
        for em, count in stats["emojis"].most_common(20):
            print(f"  {em}: {count:,}")

    # --- Performance summary ---
    print(f"\n{'=' * 60}")
    print("  PERFORMANCE")
    print(f"{'=' * 60}")
    for phase_name, duration in phase_timings:
        print(f"  {phase_name:<30} {duration:>8.1f}s")
    print(f"  {'─' * 40}")
    print(f"  {'Total':<30} {total_elapsed:>8.1f}s")
    print(f"\n  API strategy: counts + filters + sampling")
    print(f"  Sample size:  {stats['sample_size']:,} msgs "
          f"(from {stats['grand_total']:,} total)")
    if stats["grand_total"] > 0:
        pct = stats["sample_size"] / stats["grand_total"] * 100
        print(f"  Coverage:     {pct:.1f}% of messages sampled")
    print(f"{'=' * 60}")


# =========================
# MAIN
# =========================
async def main():
    run_start = time.perf_counter()
    await client.start()
    log.info("Client connected")

    dialog_start = time.perf_counter()
    dialogs = await client.get_dialogs()
    log.info(f"Fetched {len(dialogs)} dialogs in {time.perf_counter() - dialog_start:.1f}s")

    candidates = select_candidate_dialogs(dialogs)
    phase_timings = []

    async def run_pipeline(scan_client):
        # Phase 1: Exact counts (fast)
        t = time.perf_counter()
        dialog_stats = await phase1_count_all_dialogs(scan_client, candidates)
        phase_timings.append(("Phase 1: Counts", time.perf_counter() - t))

        # Phase 2: Media breakdown for top dialogs (fast)
        t = time.perf_counter()
        await phase2_media_breakdown(scan_client, dialog_stats)
        phase_timings.append(("Phase 2: Media filters", time.perf_counter() - t))

        # Phase 3: Sample messages for text/time analysis (moderate)
        t = time.perf_counter()
        sampled = await phase3_sample_messages(scan_client, dialog_stats)
        phase_timings.append(("Phase 3: Sampling", time.perf_counter() - t))

        # Phase 4: Compute everything from the data we have (instant, pure CPU)
        t = time.perf_counter()
        stats = phase4_compute_stats(dialog_stats, sampled)
        phase_timings.append(("Phase 4: Compute", time.perf_counter() - t))

        return dialog_stats, stats

    if USE_TAKEOUT:
        try:
            async with client.takeout(
                users=True,
                chats=True,
                megagroups=True,
                channels=True,
                files=False,
            ) as takeout:
                log.info("Takeout session started")
                dialog_stats, stats = await run_pipeline(takeout)
        except errors.TakeoutInitDelayError as e:
            log.warning(
                f"Takeout not ready (wait {e.seconds}s). Falling back to normal client."
            )
            dialog_stats, stats = await run_pipeline(client)
    else:
        dialog_stats, stats = await run_pipeline(client)

    total_elapsed = time.perf_counter() - run_start
    display_results(stats, dialog_stats, total_elapsed, phase_timings)

    await client.disconnect()
    log.info("Client disconnected")


if __name__ == "__main__":
    asyncio.run(main())
