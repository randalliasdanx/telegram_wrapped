from __future__ import annotations

import asyncio
import base64
import logging
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Coroutine
import math

import random

from telethon import TelegramClient, errors
from telethon.tl.functions.messages import GetSearchCountersRequest, SearchRequest
from telethon.tl.types import (
    Channel,
    Chat,
    InputMessagesFilterDocument,
    InputMessagesFilterEmpty,
    InputMessagesFilterGif,
    InputMessagesFilterMusic,
    InputMessagesFilterPhotos,
    InputMessagesFilterRoundVideo,
    InputMessagesFilterUrl,
    InputMessagesFilterVideo,
    InputMessagesFilterVoice,
    User,
)

log = logging.getLogger("wrapped.pipeline")

API_DELAY = 0.5
CONCURRENT_LIMIT = 3
TOP_DIALOGS_TO_SAMPLE = None  # Sample ALL dialogs for maximum accuracy
MIN_YEARLY_TO_SAMPLE = 50    # Skip Phase 3 for dialogs with < 50 messages in the year
PHASE1B_MIN_TOTAL = 500      # Only refine yearly count for dialogs with > 500 lifetime msgs

# Takeout mode: Telegram's bulk-export API with relaxed rate limits
API_DELAY_TAKEOUT = 0.05
CONCURRENT_LIMIT_TAKEOUT = 10
SAMPLING_PARALLELISM = 5
SAMPLING_PARALLELISM_TAKEOUT = 20
TAKEOUT_MAX_WAIT = 480  # max seconds to wait for takeout approval


def _samples_per_month(dialog_total: int) -> int:
    """Adaptive sampling: allocate more samples to busier chats.
    Capped at dialog_total/12 to avoid wasteful empty-page API calls on small chats."""
    if dialog_total > 50_000:
        base = 1000
    elif dialog_total > 10_000:
        base = 500
    else:
        base = 200
    # Never request more per month than the chat's average monthly volume
    cap = max(10, dialog_total // 12)
    return min(base, cap)


class _Throttle:
    """Concurrency controller with shared flood-wait coordination."""

    def __init__(self, limit: int = CONCURRENT_LIMIT, delay: float = API_DELAY):
        self._sem = asyncio.Semaphore(limit)
        self._delay = delay
        self._flood_event = asyncio.Event()
        self._flood_event.set()

    async def run(self, coro_fn):  # type: ignore[type-arg]
        """Accept a zero-arg callable that returns a fresh coroutine each call.
        This allows safe retry after FloodWaitError (coroutines are one-shot)."""
        async with self._sem:
            await self._flood_event.wait()
            try:
                result = await coro_fn()
                await asyncio.sleep(self._delay)
                return result
            except errors.FloodWaitError as e:
                if self._flood_event.is_set():
                    self._flood_event.clear()
                    log.warning("FloodWait: %ds (shared pause)", e.seconds)
                    await asyncio.sleep(e.seconds)
                    self._flood_event.set()
                else:
                    await self._flood_event.wait()
                result = await coro_fn()
                await asyncio.sleep(self._delay)
                return result

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

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "to", "of", "in", "on", "for",
    "is", "it", "this", "that", "i", "you", "we", "he", "she", "they", "me",
    "my", "your", "our", "us", "am", "are", "was", "were", "be", "been",
    "do", "does", "did", "have", "has", "had", "will", "would", "could", "should",
    "can", "may", "might", "shall", "not", "no", "so", "at", "by", "with",
    "from", "up", "out", "about", "into", "than", "then", "just", "like",
    "also", "very", "really", "too", "here", "there", "when", "what", "how",
    "who", "which", "where", "why", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "only", "own", "same", "than",
    "its", "his", "her", "their", "him", "them", "these", "those",
    "im", "dont", "cant", "wont", "didnt", "doesnt", "isnt", "wasnt",
    "ok", "okay", "ya", "yah", "yeah", "yep", "nah", "nope",
    "lol", "haha", "hahaha", "hahahaha", "hehe", "lmao", "omg", "idk",
    "got", "get", "go", "going", "went", "come", "came", "say", "said",
    "know", "think", "see", "want", "need", "make", "take", "give",
    "tell", "ask", "try", "let", "keep", "put", "still", "even",
    "one", "two", "de", "la", "el", "en", "que", "es", "un", "lo",
    "ah", "oh", "eh", "um", "uh", "hmm", "mm",
}

URL_RE = re.compile(r"https?://\S+|www\.\S+")
PUNCT_RE = re.compile(r"[^\w\s'-]")
SPACE_RE = re.compile(r"\s+")
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]",
    flags=re.UNICODE,
)

ProgressCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]] | Callable[[dict[str, Any]], None]


def _clean_text(text: str) -> str:
    lower = text.lower()
    lower = URL_RE.sub(" ", lower)
    lower = PUNCT_RE.sub(" ", lower)
    lower = SPACE_RE.sub(" ", lower).strip()
    return lower


def _clean_text_preserve_case(text: str) -> str:
    """Clean but preserve original casing for display purposes."""
    cleaned = URL_RE.sub(" ", text)
    cleaned = PUNCT_RE.sub(" ", cleaned)
    cleaned = SPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def _extract_emojis(raw_text: str) -> list[str]:
    return EMOJI_RE.findall(raw_text)


_BG_BIGRAMS_PATH = Path(__file__).resolve().parent / "ml" / "models" / "background_bigrams.json"
_bg_cache: dict[str, int] | None = None
_bg_total_cache: float = 0.0


def _load_background_bigrams() -> tuple[dict[str, int], float]:
    global _bg_cache, _bg_total_cache
    if _bg_cache is None:
        try:
            import json as _json
            with open(_BG_BIGRAMS_PATH) as f:
                _bg_cache = _json.load(f)
            _bg_total_cache = float(sum(_bg_cache.values())) or 1.0
        except FileNotFoundError:
            _bg_cache = {}
            _bg_total_cache = 1.0
    return _bg_cache, _bg_total_cache


def _llr_score(k_ab: float, k_a: float, k_b: float, N: float) -> float:
    """Log-likelihood ratio for bigram (a, b).
    More robust than PMI for informal text (ACL research-backed)."""
    def _H(k: float, n: float) -> float:
        if k <= 0 or k >= n or n <= 0:
            return 0.0
        p = k / n
        return k * math.log(p) + (n - k) * math.log(1 - p)

    return 2.0 * (_H(k_ab, k_a) + _H(k_b - k_ab, N - k_a) - _H(k_b, N))


def _process_text_batch(texts: list[tuple[str, float]]) -> dict[str, defaultdict]:
    # Non-stopword counts (for final word display)
    display_words: defaultdict[str, float] = defaultdict(float)
    # ALL unigram counts including stopwords (for LLR probability calculation)
    all_unigrams: defaultdict[str, float] = defaultdict(float)
    ngram_counts: defaultdict[str, float] = defaultdict(float)
    emojis: defaultdict[str, float] = defaultdict(float)
    # Track original casing: normalized -> most-common original form
    case_map: dict[str, str] = {}
    case_counts: defaultdict[str, float] = defaultdict(float)

    for text, weight in texts:
        for emo in _extract_emojis(text):
            emojis[emo] += weight

        cleaned = _clean_text(text)
        original = _clean_text_preserve_case(text)
        if not cleaned:
            continue

        tokens = cleaned.split()
        orig_tokens = original.split()
        filtered = [t for t in tokens if len(t) > 1 and not t.isdigit()]
        orig_filtered = [
            o for t, o in zip(tokens, orig_tokens)
            if len(t) > 1 and not t.isdigit()
        ] if len(tokens) == len(orig_tokens) else filtered

        for t in filtered:
            all_unigrams[t] += weight
            if t not in STOPWORDS:
                display_words[t] += weight

        for n in range(2, 6):
            for i in range(len(filtered) - n + 1):
                gram = " ".join(filtered[i: i + n])
                ngram_counts[gram] += weight
                orig_gram = " ".join(orig_filtered[i: i + n]) if i + n <= len(orig_filtered) else gram
                if gram not in case_map or weight > case_counts.get(gram, 0):
                    case_map[gram] = orig_gram
                    case_counts[gram] = weight

    total_unigrams = sum(all_unigrams.values()) or 1.0
    total_weighted = sum(ngram_counts.values()) or 1.0
    base_min_freq = max(4.0, total_weighted * 0.0003)

    candidates: dict[str, float] = {}
    for gram, count in ngram_counts.items():
        gram_words = gram.split()
        n_words = len(gram_words)
        # Longer phrases appear less often by nature — scale min_freq down
        # so 4-5 word phrases only need ~40% of the base threshold to qualify.
        length_scale = max(0.4, 1.0 - 0.15 * (n_words - 2))
        if count < base_min_freq * length_scale:
            continue
        non_stop = sum(1 for w in gram_words if w not in STOPWORDS)
        if non_stop < max(1, len(gram_words) // 2):
            continue
        candidates[gram] = count

    # Score using LLR * TF-IDF distinctiveness against background English corpus.
    # Phrases common in general English get dampened; personally distinctive ones get boosted.
    # Longer phrases get a length bonus to counteract LLR dilution.
    bg_bigrams, bg_total = _load_background_bigrams()

    scored: list[tuple[str, float, float]] = []
    for gram, count in candidates.items():
        gram_words = gram.split()
        n_words = len(gram_words)

        # LLR component: use minimum pairwise LLR (weakest link)
        # instead of geometric mean — a phrase is only as strong as its
        # weakest word-pair bond.
        pairwise_llrs = []
        for j in range(n_words - 1):
            bigram = f"{gram_words[j]} {gram_words[j+1]}"
            k_ab = ngram_counts.get(bigram, 0) if n_words > 2 else count
            k_a = all_unigrams.get(gram_words[j], 1.0)
            k_b = all_unigrams.get(gram_words[j+1], 1.0)
            pairwise_llrs.append(_llr_score(k_ab, k_a, k_b, total_unigrams))

        llr = min(pairwise_llrs) if pairwise_llrs else 0.0
        if llr <= 0:
            continue

        # TF-IDF distinctiveness: compare user frequency against background.
        # Background corpus only has bigrams, so longer phrases automatically
        # get high distinctiveness (they won't appear in the background).
        user_freq = count / total_weighted
        bg_freq = bg_bigrams.get(gram, 0) / bg_total
        distinctiveness = math.log2(1.0 + user_freq / max(bg_freq, 1e-8))

        # Length bonus: prefer longer phrases (they're more informative and
        # personal). A 4-word phrase with decent cohesion should beat a
        # 2-word phrase with similar LLR.
        length_bonus = 1.0 + 0.3 * (n_words - 2)

        score = llr * distinctiveness * length_bonus * math.log2(1 + count)
        scored.append((gram, score, count))

    # Sort by score descending, then deduplicate.
    # Key change: prefer LONGER phrases over shorter sub-phrases.
    # Sort by length DESC first (longer phrases get first chance), then score DESC.
    scored.sort(key=lambda x: (-len(x[0].split()), -x[1]))
    accepted: list[tuple[str, float, float]] = []
    accepted_strs: list[str] = []
    for gram, score, count in scored:
        # Skip if this phrase is contained within an already-accepted longer phrase
        is_sub = any(gram in a for a in accepted_strs)
        if is_sub:
            continue
        # If accepting this phrase, remove any already-accepted shorter sub-phrases
        accepted = [(g, s, c) for g, s, c in accepted if g not in gram]
        accepted_strs = [g for g, _, _ in accepted]
        accepted.append((gram, score, count))
        accepted_strs.append(gram)
        if len(accepted) >= 15:
            break

    # Re-sort by score for final display order
    accepted.sort(key=lambda x: -x[1])

    # Use original casing for display
    phrases: defaultdict[str, float] = defaultdict(float)
    for gram, _score, count in accepted:
        display_form = case_map.get(gram, gram)
        phrases[display_form] = count

    return {"words": display_words, "phrases": phrases, "emojis": emojis}
        

def _get_peak_personality(peak_hour: int) -> str:
    if peak_hour in (22, 23, 0, 1, 2, 3):
        return "Night Owl"
    if peak_hour in (4, 5, 6, 7, 8):
        return "Early Bird"
    if peak_hour in (9, 10, 11):
        return "Morning Messenger"
    if peak_hour in (12, 13, 14):
        return "Lunch Texter"
    if peak_hour in (15, 16, 17):
        return "Afternoon Chatter"
    return "Evening Communicator"


async def _emit(callback: ProgressCallback | None, data: dict[str, Any]) -> None:
    if callback is None:
        return
    result = callback(data)
    if asyncio.iscoroutine(result):
        await result


# ---------------------------------------------------------------------------
# Phase 1
# ---------------------------------------------------------------------------
async def phase1_count_all_dialogs(
    scan_client: TelegramClient,
    candidates: list[Any],
    callback: ProgressCallback | None = None,
    my_id: int | None = None,
    throttle: _Throttle | None = None,
) -> list[dict[str, Any]]:
    total = len(candidates)
    completed = 0
    results: list[dict[str, Any]] = []
    lock = asyncio.Lock()
    thr = throttle or _Throttle()

    async def _count_one(dialog: Any) -> None:
        nonlocal completed
        name = getattr(dialog, "name", None) or str(dialog.id)
        try:
            result = await thr.run(
                lambda: scan_client.get_messages(dialog.entity, limit=0)
            )
            count = result.total if result is not None else 0
        except Exception as e:
            log.error("Error counting %s: %s: %s", name, type(e).__name__, e)
            count = 0

        async with lock:
            if count > 0:
                results.append({"dialog": dialog, "name": name, "total": count})
            completed += 1
            if completed % 20 == 0 or completed == total:
                await _emit(callback, {
                    "phase": "counting",
                    "progress": completed,
                    "total": total,
                    "message": f"Counting messages... {completed}/{total} chats",
                })

    await asyncio.gather(*(_count_one(d) for d in candidates))
    results.sort(key=lambda r: r["total"], reverse=True)
    return results


async def _refine_yearly_counts(
    scan_client: TelegramClient,
    dialog_stats: list[dict[str, Any]],
    year_start: datetime,
    throttle: _Throttle | None = None,
    callback: ProgressCallback | None = None,
) -> None:
    """Use messages.search with min_date to get accurate yearly counts.
    Updates entries in-place with a 'yearly_total' key."""
    thr = throttle or _Throttle()
    min_date_ts = int(year_start.timestamp())
    completed = 0
    lock = asyncio.Lock()
    total = len(dialog_stats)

    async def _refine_one(entry: dict[str, Any]) -> None:
        nonlocal completed
        try:
            input_peer = await scan_client.get_input_entity(entry["dialog"].entity)
            result = await thr.run(
                lambda: scan_client(SearchRequest(
                    peer=input_peer,
                    q="",
                    filter=InputMessagesFilterEmpty(),
                    min_date=min_date_ts,
                    max_date=0,
                    offset_id=0,
                    add_offset=0,
                    limit=1,
                    max_id=0,
                    min_id=0,
                    hash=0,
                    from_id=None,
                    top_msg_id=None,
                ))
            )
            yearly = getattr(result, "count", None)
            if yearly is not None and yearly > 0:
                entry["yearly_total"] = yearly
        except Exception as e:
            log.warning("Yearly count failed for %s: %s", entry.get("name"), e)

        async with lock:
            completed += 1
            if completed % 20 == 0 or completed == total:
                await _emit(callback, {
                    "phase": "counting",
                    "progress": completed,
                    "total": total,
                    "message": f"Getting yearly counts... {completed}/{total}",
                })

    await asyncio.gather(*(_refine_one(e) for e in dialog_stats))

    got = sum(1 for e in dialog_stats if "yearly_total" in e)
    log.info("Yearly refinement: %d/%d dialogs got yearly counts", got, total)

    # Re-sort by yearly count where available
    dialog_stats.sort(
        key=lambda d: d.get("yearly_total", d["total"]), reverse=True,
    )


# ---------------------------------------------------------------------------
# Phase 2
# ---------------------------------------------------------------------------
async def _get_media_counts_batch(
    scan_client: TelegramClient,
    dialog: Any,
    throttle: _Throttle | None = None,
) -> dict[str, int]:
    """Get all media type counts in a SINGLE API call using GetSearchCountersRequest."""
    thr = throttle or _Throttle()
    try:
        input_peer = await scan_client.get_input_entity(dialog.entity)
        filters = [f for _, f in MEDIA_FILTERS]
        result = await thr.run(
            lambda: scan_client(GetSearchCountersRequest(peer=input_peer, filters=filters))
        )
        return {
            name: counter.count
            for (name, _), counter in zip(MEDIA_FILTERS, result)
        }
    except Exception as e:
        log.warning("Batch media count failed for %s: %s", getattr(dialog, "name", "?"), e)
        return {name: 0 for name, _ in MEDIA_FILTERS}


async def phase2_media_breakdown(
    scan_client: TelegramClient,
    dialog_stats: list[dict[str, Any]],
    callback: ProgressCallback | None = None,
    my_id: int | None = None,
    throttle: _Throttle | None = None,
) -> None:
    """Count media types across ALL dialogs using batch API (1 call per dialog)."""
    to_scan = dialog_stats
    completed = 0
    lock = asyncio.Lock()

    async def _scan_one(entry: dict[str, Any]) -> None:
        nonlocal completed
        counts = await _get_media_counts_batch(scan_client, entry["dialog"], throttle=throttle)
        async with lock:
            entry["media"] = counts
            completed += 1
            if completed % 20 == 0 or completed == len(to_scan):
                await _emit(callback, {
                    "phase": "media",
                    "progress": completed,
                    "total": len(to_scan),
                    "message": f"Analyzing media... {completed}/{len(to_scan)} chats",
                })

    await asyncio.gather(*(_scan_one(e) for e in to_scan))


# ---------------------------------------------------------------------------
# Phase 3
# ---------------------------------------------------------------------------
async def _sample_dialog_messages(
    scan_client: TelegramClient,
    dialog: Any,
    year_start: datetime,
    year_end: datetime,
    yearly_total: int = 1000,
    throttle: _Throttle | None = None,
    is_top_dialog: bool = False,
) -> list[Any]:
    """Sample messages using temporal-window passes with random dates within each window.

    Key improvement: instead of sampling at window boundaries, we pick a random date
    *within* each window so samples are uniformly distributed across the year.
    This gives much better time-of-day coverage for peak hour accuracy.
    """
    thr = throttle or _Throttle()
    all_samples: list[Any] = []

    # Adaptive pass count: more passes = better temporal coverage
    # Top dialogs get double the passes for better accuracy on phrases/peak hour
    if yearly_total < 150:
        num_passes = 1
    elif yearly_total < 800:
        num_passes = 2
    elif yearly_total < 4000:
        num_passes = 4
    elif yearly_total < 15000:
        num_passes = 6
    else:
        num_passes = 8

    if is_top_dialog:
        num_passes = min(num_passes * 2, 12)

    # Per-pass message limit: top dialogs get more samples
    per_pass = min(150 if is_top_dialog else 100, max(25, yearly_total // max(num_passes * 3, 1)))
    year_seconds = (year_end - year_start).total_seconds()
    window_seconds = year_seconds / num_passes

    for i in range(num_passes):
        # Sample at a RANDOM point within this window (not at the boundary)
        # This ensures messages are drawn from all times of day throughout the year
        window_start_offset = year_seconds * i / num_passes
        random_within_window = random.random() * window_seconds
        sample_date = year_start + timedelta(seconds=window_start_offset + random_within_window)
        if sample_date > year_end:
            sample_date = year_end

        # Small add_offset for additional randomness within message stream at that date
        rand_offset = random.randint(0, max(per_pass // 4, 0))

        _entity = dialog.entity
        _limit = per_pass
        _offset_date = sample_date
        _add_offset = rand_offset
        try:
            msgs = await thr.run(
                lambda e=_entity, lim=_limit, od=_offset_date, ao=_add_offset: (
                    scan_client.get_messages(e, limit=lim, offset_date=od, add_offset=ao)
                )
            )
            if msgs:
                for msg in msgs:
                    if year_start <= msg.date <= year_end:
                        all_samples.append(msg)
        except Exception as e:
            log.error("Error sampling: %s: %s", type(e).__name__, e)

    return all_samples


async def _fetch_user_stickers(
    scan_client: TelegramClient,
    dialog: Any,
    year_start: datetime,
    year_end: datetime,
    my_id: int | None,
    throttle: _Throttle | None = None,
    limit: int = 200,
) -> list[Any]:
    """Dedicated sticker fetch using InputMessagesFilterDocument, filtered client-side.

    Stickers are Telegram Documents; there is no InputMessagesFilterSticker.
    We fetch document messages and keep only those where msg.sticker is set.
    Doing this for top dialogs is far more accurate than relying on general
    message samples (stickers appear infrequently and are easily missed).
    """
    thr = throttle or _Throttle()
    try:
        input_peer = await scan_client.get_input_entity(dialog.entity)
        min_date_ts = int(year_start.timestamp())
        max_date_ts = int(year_end.timestamp())
        result = await thr.run(
            lambda: scan_client(SearchRequest(
                peer=input_peer,
                q="",
                filter=InputMessagesFilterDocument(),
                min_date=min_date_ts,
                max_date=max_date_ts,
                offset_id=0,
                add_offset=0,
                limit=limit,
                max_id=0,
                min_id=0,
                hash=0,
                from_id=None,
                top_msg_id=None,
            ))
        )
        msgs = getattr(result, "messages", []) or []
        # Keep only sticker messages sent by the user
        sticker_msgs = [m for m in msgs if getattr(m, "sticker", None) is not None]
        if my_id is not None:
            sticker_msgs = [
                m for m in sticker_msgs
                if hasattr(m, "from_id") and m.from_id
                and getattr(m.from_id, "user_id", None) == my_id
            ]
        return sticker_msgs
    except Exception as e:
        log.warning("Sticker search failed for %s: %s", getattr(dialog, "name", "?"), e)
        return []


# ---------------------------------------------------------------------------
# Phase 4
# ---------------------------------------------------------------------------
def phase4_compute_stats(
    dialog_stats: list[dict[str, Any]],
    sampled_messages: list[Any],
    start: datetime,
    end: datetime,
    my_id: int | None = None,
    all_samples_unfiltered: list[Any] | None = None,
    utc_offset_minutes: int = 0,
    dedicated_sticker_msgs: list[Any] | None = None,
) -> dict[str, Any]:
    # Use yearly_total (from Phase 1b) when available, else lifetime total
    def _best_count(d: dict[str, Any]) -> int:
        return d.get("yearly_total", d["total"])

    grand_total = sum(_best_count(d) for d in dialog_stats)
    days_in_range = max((end - start).days, 1)
    daily_average = round(grand_total / days_in_range)

    log.info("Grand total (yearly): %d, daily_avg: %d", grand_total, daily_average)

    top_chats = [
        {
            "name": d["name"],
            "total": _best_count(d),
            "pct": round(_best_count(d) / max(grand_total, 1) * 100, 1),
            "avatar": d.get("avatar"),
        }
        for d in dialog_stats[:10]
    ]

    # Per-dialog weight map for scaling sampled counts to estimated real counts.
    # Use user_fraction (sampled_count / total_sampled) to estimate the user's
    # share of yearly_total, avoiding the ~2x inflation from counting both parties.
    dialog_weight: dict[str, float] = {}
    for entry in dialog_stats:
        sampled = entry.get("sampled_count", 0)
        total_sampled = entry.get("total_sampled", 0)
        if sampled > 0 and total_sampled > 0:
            user_fraction = sampled / total_sampled
            estimated_user_yearly = _best_count(entry) * user_fraction
            dialog_weight[entry["name"]] = estimated_user_yearly / sampled
        else:
            dialog_weight[entry["name"]] = 1.0

    hour_activity: defaultdict[int, float] = defaultdict(float)
    hour_raw: defaultdict[int, int] = defaultdict(int)  # unweighted counts for peak hour
    per_dialog_days: dict[str, set[Any]] = defaultdict(set)
    weighted_texts: list[tuple[str, float]] = []
    best_reacted_msg: Any = None
    best_reaction_count = 0

    def _local_hour(msg_utc_hour: int) -> int:
        """Convert UTC hour to local hour using browser-reported offset."""
        return (msg_utc_hour + utc_offset_minutes // 60) % 24

    for msg in sampled_messages:
        dname = getattr(msg, "_dialog_name", None)
        weight = dialog_weight.get(dname, 1.0) if dname else 1.0

        local_h = _local_hour(msg.date.hour)
        hour_activity[local_h] += weight
        hour_raw[local_h] += 1  # unweighted: when did user actually send messages?
        msg_date = msg.date.date()

        if dname:
            per_dialog_days[dname].add(msg_date)

        if msg.message:
            weighted_texts.append((msg.message, weight))

        if hasattr(msg, "reactions") and msg.reactions:
            try:
                total_reactions = sum(
                    r.count for r in msg.reactions.results
                ) if hasattr(msg.reactions, "results") else 0
                if total_reactions > best_reaction_count:
                    best_reaction_count = total_reactions
                    best_reacted_msg = msg
            except Exception:
                pass

    # Peak hour from raw (unweighted) counts — reflects actual send-time, not chat size
    peak_hour = max(hour_raw, key=hour_raw.get) if hour_raw else 12
    peak_personality = _get_peak_personality(peak_hour)

    # Hourly distribution: use weighted counts so the shape reflects estimated real volume
    hourly_distribution = {h: round(hour_activity.get(h, 0)) for h in range(24)}

    # Night messages (22-4)
    night_hours = {22, 23, 0, 1, 2, 3}
    total_night_messages = sum(hourly_distribution.get(h, 0) for h in night_hours)

    # Streak -- hybrid: count-based heuristic for active chats + sampled for others
    longest_streak = 0
    streak_partner = top_chats[0]["name"] if top_chats else "Unknown"

    DAILY_MSG_THRESHOLD = 20
    for entry in dialog_stats:
        avg_daily = entry["total"] / max(days_in_range, 1)
        if avg_daily >= DAILY_MSG_THRESHOLD:
            if days_in_range > longest_streak:
                longest_streak = days_in_range
                streak_partner = entry["name"]
            break

    streak_source = all_samples_unfiltered if all_samples_unfiltered else sampled_messages
    unfiltered_per_dialog_days: dict[str, set[Any]] = defaultdict(set)
    for msg in streak_source:
        dname = getattr(msg, "_dialog_name", None)
        if dname:
            unfiltered_per_dialog_days[dname].add(msg.date.date())

    for dialog_name, days in unfiltered_per_dialog_days.items():
        if not days:
            continue
        sd = sorted(days)
        cur = 1
        best = 1
        for i in range(1, len(sd)):
            if (sd[i] - sd[i - 1]).days == 1:
                cur += 1
                best = max(best, cur)
            else:
                cur = 1
        best = max(best, cur)
        if best > longest_streak:
            longest_streak = best
            streak_partner = dialog_name

    # Conversation starter -- uses ALL samples (unfiltered) to see both sides
    CONVO_GAP_SECONDS = 4 * 3600
    user_starts = 0
    other_starts = 0
    if my_id is not None and all_samples_unfiltered:
        per_dialog_msgs: dict[str, list[Any]] = defaultdict(list)
        for msg in all_samples_unfiltered:
            dname = getattr(msg, "_dialog_name", None)
            if dname:
                per_dialog_msgs[dname].append(msg)

        for _dname, msgs in per_dialog_msgs.items():
            sorted_msgs = sorted(msgs, key=lambda m: m.date)
            for j, msg in enumerate(sorted_msgs):
                is_new_convo = j == 0 or (msg.date - sorted_msgs[j - 1].date).total_seconds() > CONVO_GAP_SECONDS
                if not is_new_convo:
                    continue
                sender_id = None
                if hasattr(msg, "from_id") and msg.from_id:
                    sender_id = getattr(msg.from_id, "user_id", None) or getattr(msg.from_id, "channel_id", None)
                if sender_id == my_id:
                    user_starts += 1
                else:
                    other_starts += 1

    total_starts = user_starts + other_starts
    if total_starts > 0:
        user_pct = round(user_starts / total_starts * 100)
        other_pct = 100 - user_pct
    else:
        user_pct, other_pct = 50, 50

    # Most reacted message
    most_reacted = None
    if best_reacted_msg and best_reaction_count > 0:
        reactions_list = []
        if hasattr(best_reacted_msg.reactions, "results"):
            for r in best_reacted_msg.reactions.results:
                emoji = getattr(r.reaction, "emoticon", None) or str(r.reaction)
                reactions_list.append({"emoji": emoji, "count": r.count})

        most_reacted = {
            "text": best_reacted_msg.message or "(media)",
            "chat": getattr(best_reacted_msg, "_dialog_name", "Unknown"),
            "sender": "You" if (my_id and hasattr(best_reacted_msg, "from_id") and best_reacted_msg.from_id and getattr(best_reacted_msg.from_id, "user_id", None) == my_id) else "Someone",
            "date": best_reacted_msg.date.strftime("%B %d"),
            "reactions": reactions_list,
            "reply_preview": None,
        }

    # Text analysis (weighted)
    text_results = _process_text_batch(weighted_texts)

    # Media totals (exact from Phase 2)
    media_totals: Counter[str] = Counter()
    for d in dialog_stats:
        if "media" in d:
            for k, v in d["media"].items():
                media_totals[k] += v

    sorted_emojis = sorted(text_results["emojis"].items(), key=lambda x: x[1], reverse=True)
    top_emojis = [{"emoji": e, "count": round(c)} for e, c in sorted_emojis[:10]]

    sorted_words = sorted(text_results["words"].items(), key=lambda x: x[1], reverse=True)
    top_words = [{"word": w, "count": round(c)} for w, c in sorted_words[:20]]

    sorted_bigrams = sorted(text_results["phrases"].items(), key=lambda x: x[1], reverse=True)
    top_bigrams = [{"phrase": p, "count": round(c)} for p, c in sorted_bigrams[:10]]

    # Sticker extraction — track by sticker document ID (unique per sticker image,
    # not just emoji) for accuracy. Use dedicated sticker msgs when available
    # (found by InputMessagesFilterDocument pass); fall back to sampled messages.
    sticker_id_counter: defaultdict[str, int] = defaultdict(int)   # raw counts
    sticker_weighted: defaultdict[str, float] = defaultdict(float)  # weighted counts
    sticker_docs: dict[str, Any] = {}   # sticker_id -> Document
    sticker_emoji: dict[str, str] = {}  # sticker_id -> emoji alt

    def _count_sticker_msg(msg: Any, weight: float = 1.0) -> None:
        sticker = getattr(msg, "sticker", None)
        if not sticker:
            return
        sticker_id = str(sticker.id)
        emoji_alt = None
        for attr in getattr(sticker, "attributes", []):
            if hasattr(attr, "alt") and attr.alt:
                emoji_alt = attr.alt
                break
        if emoji_alt is None:
            return
        sticker_id_counter[sticker_id] += 1
        sticker_weighted[sticker_id] += weight
        if sticker_id not in sticker_docs:
            sticker_docs[sticker_id] = sticker
            sticker_emoji[sticker_id] = emoji_alt

    if dedicated_sticker_msgs:
        # Dedicated search results: unweighted (direct counts from top dialogs)
        for msg in dedicated_sticker_msgs:
            _count_sticker_msg(msg, weight=1.0)
        log.info("Sticker counting: using %d dedicated sticker messages", len(dedicated_sticker_msgs))
    else:
        # Fall back to weighted counts from general sampled messages
        for msg in sampled_messages:
            dname = getattr(msg, "_dialog_name", None)
            weight = dialog_weight.get(dname, 1.0) if dname else 1.0
            _count_sticker_msg(msg, weight=weight)

    # Require at least 2 raw observations to avoid weighting artifacts
    MIN_STICKER_CONFIDENCE = 2
    # If dedicated search was used, 1 observation is meaningful (direct fetch)
    min_conf = 1 if dedicated_sticker_msgs else MIN_STICKER_CONFIDENCE

    sorted_stickers = sorted(sticker_weighted.items(), key=lambda x: x[1], reverse=True)
    top_stickers = [
        {
            "emoji": sticker_emoji.get(sid, "🔖"),
            "count": round(cnt),
            "_doc": sticker_docs.get(sid),
        }
        for sid, cnt in sorted_stickers[:10]
        if sticker_id_counter.get(sid, 0) >= min_conf
    ]

    # Self-calibration: compute per-dialog features for normalization
    from app.ml.features import (
        extract_features,
        compute_per_dialog_features,
        compute_self_calibration,
    )
    from app.ml.inference import classify_texter_type, self_calibrate_axes
    from app.ml.vibe_age import compute_vibe_age_from_texts

    # Group data by dialog for per-dialog feature computation
    per_dialog_texts: dict[str, list[tuple[str, float]]] = defaultdict(list)
    per_dialog_msgs: dict[str, list[Any]] = defaultdict(list)
    per_dialog_hours: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    sticker_per_dialog: dict[str, int] = defaultdict(int)

    for msg in sampled_messages:
        dname = getattr(msg, "_dialog_name", None)
        if not dname:
            continue
        weight = dialog_weight.get(dname, 1.0)
        per_dialog_msgs[dname].append(msg)
        if msg.message:
            per_dialog_texts[dname].append((msg.message, weight))
        per_dialog_hours[dname][msg.date.hour] += weight
        sticker = getattr(msg, "sticker", None)
        if sticker:
            sticker_per_dialog[dname] += 1

    media_per_dialog: dict[str, dict[str, int]] = {}
    dialog_total_map: dict[str, int] = {}
    for entry in dialog_stats:
        name = entry["name"]
        media_per_dialog[name] = entry.get("media", {})
        dialog_total_map[name] = _best_count(entry)

    per_dialog_feats = compute_per_dialog_features(
        per_dialog_texts=dict(per_dialog_texts),
        per_dialog_messages=dict(per_dialog_msgs),
        per_dialog_hours={k: dict(v) for k, v in per_dialog_hours.items()},
        media_per_dialog=media_per_dialog,
        dialog_totals=dialog_total_map,
        sticker_per_dialog=dict(sticker_per_dialog),
    )
    log.info("Self-calibration: computed features for %d dialogs", len(per_dialog_feats))

    # Self-calibrate axes (texter type) and vibe age
    axis_calibration = self_calibrate_axes(per_dialog_feats)
    vibe_calibration = compute_self_calibration(per_dialog_feats)

    if axis_calibration:
        log.info("Self-calibrated texter axes from %d dialogs", len(per_dialog_feats))
    else:
        log.info("Using default axis calibration (fewer than 5 dialogs)")

    # Global feature extraction (across all dialogs)
    features = extract_features(
        sampled_messages=sampled_messages,
        media_totals=dict(media_totals),
        grand_total=grand_total,
        hourly_distribution=hourly_distribution,
        weighted_texts=weighted_texts,
        sticker_count=round(sum(sticker_weighted.values())),
    )
    texter_type = classify_texter_type(
        features, conversation_starter_pct=user_pct, calibration=axis_calibration,
    )

    # Vibe age: self-calibrated normalization for this user's texting patterns
    vibe_age = compute_vibe_age_from_texts(weighted_texts, calibration=vibe_calibration)

    date_range = {
        "start": start.strftime("%b %Y"),
        "end": end.strftime("%b %Y"),
    }

    return {
        "grand_total": grand_total,
        "daily_average": daily_average,
        "top_chats": top_chats,
        "peak_hour": peak_hour,
        "peak_personality": peak_personality,
        "hourly_distribution": hourly_distribution,
        "total_night_messages": total_night_messages,
        "longest_streak": longest_streak,
        "streak_partner": streak_partner,
        "conversation_starter": {"user_pct": user_pct, "other_pct": other_pct},
        "most_reacted_message": most_reacted,
        "top_emojis": top_emojis,
        "top_stickers": top_stickers,
        "texter_type": texter_type,
        "top_sticker_pack": None,
        "top_words": top_words,
        "top_bigrams": top_bigrams,
        "media_totals": dict(media_totals),
        "date_range": date_range,
        "vibe_age": vibe_age,
    }


async def _download_sticker_thumbnails(
    client: TelegramClient,
    sticker_stats: list[dict[str, Any]],
    delay: float = API_DELAY,
) -> None:
    """Download thumbnail images for top stickers and embed as base64."""
    for entry in sticker_stats:
        doc = entry.pop("_doc", None)
        if doc is None:
            entry["image"] = None
            continue
        try:
            if hasattr(doc, "thumbs") and doc.thumbs:
                data = await client.download_media(doc, file=bytes, thumb=0)
            else:
                data = await client.download_media(doc, file=bytes)

            if data:
                b64 = base64.b64encode(data).decode()
                if data[:4] == b"RIFF":
                    mime = "image/webp"
                elif data[:3] == b"\xff\xd8\xff":
                    mime = "image/jpeg"
                elif data[:8] == b"\x89PNG\r\n\x1a\n":
                    mime = "image/png"
                else:
                    mime = "image/webp"
                entry["image"] = f"data:{mime};base64,{b64}"
            else:
                entry["image"] = None
        except Exception as e:
            log.warning("Failed to download sticker thumb: %s", e)
            entry["image"] = None
        await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------
def _select_candidate_dialogs(dialogs: list[Any], start: datetime) -> list[Any]:
    selected = []
    skipped: dict[str, int] = defaultdict(int)
    for d in dialogs:
        if not d.message:
            continue
        if d.message.date < start:
            continue
        entity = d.entity
        if not isinstance(entity, (User, Chat)):
            entity_type = type(entity).__name__
            skipped[entity_type] += 1
            log.debug(
                "Skipping dialog %s (entity_type=%s)",
                getattr(d, "name", "?"),
                entity_type,
            )
            continue
        selected.append(d)
    if skipped:
        for etype, count in skipped.items():
            log.info("Skipped %d dialogs of type %s", count, etype)
    log.info("Selected %d candidate dialogs (User/Chat only)", len(selected))
    return selected


async def _run_phases(
    scan_client: TelegramClient,
    download_client: TelegramClient,
    callback: ProgressCallback | None,
    start: datetime,
    end: datetime,
    my_id: int | None,
    api_delay: float,
    concurrent_limit: int,
    sampling_parallelism: int,
    utc_offset_minutes: int = 0,
) -> dict[str, Any]:
    """Core pipeline logic shared between takeout and standard modes."""
    throttle = _Throttle(limit=concurrent_limit, delay=api_delay)

    dialogs = await scan_client.get_dialogs()
    candidates = _select_candidate_dialogs(dialogs, start)
    log.info("Found %d candidate dialogs from %d total", len(candidates), len(dialogs))

    await _emit(callback, {"phase": "init", "message": f"Found {len(candidates)} active chats"})

    # Phase 1a -- fast lifetime counts (GetHistoryRequest)
    dialog_stats = await phase1_count_all_dialogs(
        scan_client, candidates, callback, my_id=my_id, throttle=throttle,
    )

    # Phase 1b -- accurate yearly counts (SearchRequest). Only run for dialogs with
    # enough lifetime messages that yearly count could differ significantly from total.
    # Small/new dialogs (total <= PHASE1B_MIN_TOTAL) likely started this year, so yearly ≈ total.
    phase1b_candidates = [d for d in dialog_stats if d["total"] > PHASE1B_MIN_TOTAL]
    skipped_1b = len(dialog_stats) - len(phase1b_candidates)
    if skipped_1b:
        log.info("Phase 1b: skipping %d small dialogs (total <= %d)", skipped_1b, PHASE1B_MIN_TOTAL)
    if phase1b_candidates:
        await _refine_yearly_counts(
            scan_client, phase1b_candidates, year_start=start, throttle=throttle, callback=callback,
        )

    # Phase 2 -- concurrent media counts
    await phase2_media_breakdown(
        scan_client, dialog_stats, callback, my_id=my_id, throttle=throttle,
    )

    # Phase 3 -- concurrent sampling with adaptive sample sizes.
    # Skip dialogs with very few yearly messages — they contribute negligible signal.
    def _yearly(d: dict[str, Any]) -> int:
        return d.get("yearly_total", d["total"])
    candidates_for_sampling = [d for d in dialog_stats if _yearly(d) >= MIN_YEARLY_TO_SAMPLE]
    skipped_3 = len(dialog_stats) - len(candidates_for_sampling)
    if skipped_3:
        log.info("Phase 3: skipping %d dialogs with < %d yearly msgs", skipped_3, MIN_YEARLY_TO_SAMPLE)
    to_sample = candidates_for_sampling[:TOP_DIALOGS_TO_SAMPLE]
    # Top 10 dialogs by yearly message count get denser sampling for better accuracy
    TOP_DIALOG_THRESHOLD = 10
    top_dialog_names: set[str] = {e["name"] for e in to_sample[:TOP_DIALOG_THRESHOLD]}
    all_sampled: list[Any] = []
    all_samples_unfiltered: list[Any] = []
    completed_sampling = 0
    sampling_lock = asyncio.Lock()
    sampling_sem = asyncio.Semaphore(sampling_parallelism)

    async def _sample_one(entry: dict[str, Any]) -> None:
        nonlocal completed_sampling
        yearly = entry.get("yearly_total", entry["total"])
        is_top = entry["name"] in top_dialog_names
        samples = await _sample_dialog_messages(
            scan_client, entry["dialog"], start, end,
            yearly_total=yearly, throttle=throttle, is_top_dialog=is_top,
        )
        for msg in samples:
            msg._dialog_name = entry["name"]  # type: ignore[attr-defined]

        user_samples = [
            msg for msg in samples
            if hasattr(msg, "from_id") and msg.from_id
            and getattr(msg.from_id, "user_id", None) == my_id
        ]

        async with sampling_lock:
            all_samples_unfiltered.extend(samples)
            entry["total_sampled"] = len(samples)
            entry["sampled_count"] = len(user_samples)
            all_sampled.extend(user_samples)
            completed_sampling += 1
            await _emit(callback, {
                "phase": "sampling",
                "progress": completed_sampling,
                "total": len(to_sample),
                "message": f"Sampling conversations... {completed_sampling}/{len(to_sample)} chats",
            })

    async def _guarded_sample(entry: dict[str, Any]) -> None:
        async with sampling_sem:
            await _sample_one(entry)

    await asyncio.gather(*(_guarded_sample(e) for e in to_sample))

    # Phase 3b — dedicated sticker search for top 15 dialogs.
    # Stickers are rare in general message samples; a dedicated document-filter
    # search gives an accurate count without relying on lucky random sampling.
    STICKER_SEARCH_DIALOGS = 15
    sticker_search_targets = to_sample[:STICKER_SEARCH_DIALOGS]
    dedicated_sticker_msgs: list[Any] = []
    if sticker_search_targets:
        await _emit(callback, {"phase": "sampling", "message": "Finding your most-used stickers..."})
        sticker_lock = asyncio.Lock()

        async def _sticker_one(entry: dict[str, Any]) -> None:
            msgs = await _fetch_user_stickers(
                scan_client, entry["dialog"], start, end,
                my_id=my_id, throttle=throttle,
            )
            for msg in msgs:
                msg._dialog_name = entry["name"]  # type: ignore[attr-defined]
            async with sticker_lock:
                dedicated_sticker_msgs.extend(msgs)

        await asyncio.gather(*(_sticker_one(e) for e in sticker_search_targets))
        log.info("Phase 3b: found %d dedicated sticker messages across top %d dialogs",
                 len(dedicated_sticker_msgs), len(sticker_search_targets))

    # Phase 4
    await _emit(callback, {"phase": "computing", "message": "Crunching the numbers..."})
    stats = phase4_compute_stats(
        dialog_stats, all_sampled, start, end, my_id,
        all_samples_unfiltered, utc_offset_minutes=utc_offset_minutes,
        dedicated_sticker_msgs=dedicated_sticker_msgs if dedicated_sticker_msgs else None,
    )

    if stats.get("top_stickers"):
        await _emit(callback, {"phase": "computing", "message": "Downloading sticker images..."})
        await _download_sticker_thumbnails(download_client, stats["top_stickers"], delay=api_delay)

    await _emit(callback, {"phase": "done", "message": "Your Wrapped is ready!"})
    return stats


async def _try_with_takeout(
    client: TelegramClient,
    callback: ProgressCallback | None,
    start: datetime,
    end: datetime,
    my_id: int | None,
    utc_offset_minutes: int = 0,
) -> dict[str, Any] | None:
    """Attempt to run the pipeline inside a Takeout session for faster processing.

    Returns the result dict on success, or None if takeout is unavailable
    (falls back to caller for standard-API mode).
    """
    for attempt in range(2):
        try:
            if attempt == 0:
                await _emit(callback, {
                    "phase": "init",
                    "message": "Requesting data export session...",
                })
            async with client.takeout(
                users=True,
                chats=True,
                megagroups=True,
                files=True,
                max_file_size=10 * 1024 * 1024,
            ) as takeout:
                log.info("Takeout session acquired (attempt %d)", attempt + 1)
                await _emit(callback, {
                    "phase": "init",
                    "message": "Export session active \u2014 faster processing!",
                })
                return await _run_phases(
                    scan_client=takeout,
                    download_client=takeout,
                    callback=callback,
                    start=start,
                    end=end,
                    my_id=my_id,
                    api_delay=API_DELAY_TAKEOUT,
                    concurrent_limit=CONCURRENT_LIMIT_TAKEOUT,
                    sampling_parallelism=SAMPLING_PARALLELISM_TAKEOUT,
                    utc_offset_minutes=utc_offset_minutes,
                )
        except errors.TakeoutInitDelayError as e:
            if attempt == 0 and e.seconds <= TAKEOUT_MAX_WAIT:
                log.info("Takeout requires %ds wait, sleeping...", e.seconds)
                await _emit(callback, {
                    "phase": "init",
                    "message": (
                        f"Telegram requires a {e.seconds}s wait before export. "
                        "You may see a notification on your devices."
                    ),
                })
                await asyncio.sleep(e.seconds)
                continue
            log.warning("Takeout delay too long (%ds), giving up", e.seconds)
            return None
        except Exception as e:
            log.warning("Takeout failed: %s: %s", type(e).__name__, e)
            return None
    return None


async def run_pipeline(
    client: TelegramClient,
    callback: ProgressCallback | None = None,
    utc_offset_minutes: int = 0,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=365)
    end = now

    me = await client.get_me()
    my_id = me.id if me else None

    await _emit(callback, {"phase": "init", "message": "Connecting to Telegram..."})

    # Try Takeout API first for 3-5x faster processing
    result = await _try_with_takeout(client, callback, start, end, my_id, utc_offset_minutes=utc_offset_minutes)
    if result is not None:
        return result

    # Fallback: standard API with conservative rate limiting
    log.info("Falling back to standard API")
    await _emit(callback, {"phase": "init", "message": "Using standard processing..."})
    return await _run_phases(
        scan_client=client,
        download_client=client,
        callback=callback,
        start=start,
        end=end,
        my_id=my_id,
        api_delay=API_DELAY,
        concurrent_limit=CONCURRENT_LIMIT,
        sampling_parallelism=SAMPLING_PARALLELISM,
        utc_offset_minutes=utc_offset_minutes,
    )
