"""Statistics computed from collected data.

Everything here is pure and CPU-only (no Telegram calls), so it can run in a
worker thread/process without blocking the event loop, and is unit tested with
synthetic data.

Weights: every :class:`~app.fetcher.MsgRecord` carries ``weight`` — 1.0 when
its time window was fetched completely, ``window_count / fetched`` otherwise —
so weighted sums are unbiased estimates of the user's real totals.
"""
from __future__ import annotations

import random
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from app.fetcher import Collected, DialogData, MsgRecord
from app.text_analysis import _get_peak_personality, _process_text_batch

MEDIA_KEYS = ["photos", "videos", "voice_notes", "round_videos", "gifs", "documents", "music", "links"]
CONVO_GAP_SECONDS = 4 * 3600
MAX_TEXTS_FOR_ANALYSIS = 25_000  # bounded CPU/memory for phrase extraction
MIN_REPLY_SAMPLES = 8
MAX_RECORDS_PER_DIALOG_FEATURES = 3_000  # per-chat feature means converge long before this


def _longest_run(days: set[date]) -> int:
    if not days:
        return 0
    ordered = sorted(days)
    best = cur = 1
    for prev, nxt in zip(ordered, ordered[1:]):
        cur = cur + 1 if (nxt - prev).days == 1 else 1
        best = max(best, cur)
    return best


def _sample_texts(texts: list[tuple[str, float]], limit: int, seed: int = 7) -> list[tuple[str, float]]:
    """Uniform subsample that preserves the weighted total."""
    if len(texts) <= limit:
        return texts
    rng = random.Random(seed)
    picked = rng.sample(texts, limit)
    scale = sum(w for _, w in texts) / max(sum(w for _, w in picked), 1e-9)
    return [(t, w * scale) for t, w in picked]


def conversation_dynamics(dialogs: list[DialogData]) -> tuple[int, int, dict[str, list[float]]]:
    """Conversation starts (user, other) and reply delays per chat.

    Only transitions *inside* one contiguous history batch are used: the
    first message of a batch is not a conversation start, it is merely where
    the sample happened to begin.
    """
    user_starts = other_starts = 0
    reply_delays: dict[str, list[float]] = defaultdict(list)
    for d in dialogs:
        for batch in d.history_batches:
            for prev, cur in zip(batch, batch[1:]):
                gap = (cur.date - prev.date).total_seconds()
                if gap > CONVO_GAP_SECONDS:
                    if cur.out:
                        user_starts += 1
                    else:
                        other_starts += 1
                elif cur.out and not prev.out:
                    reply_delays[d.name].append(gap)
    return user_starts, other_starts, reply_delays


def compute_stats(
    collected: Collected,
    start: datetime,
    end: datetime,
    utc_offset_minutes: int = 0,
    duration_seconds: float = 0.0,
    takeout: bool = False,
) -> dict[str, Any]:
    dialogs = collected.dialogs
    offset = timedelta(minutes=utc_offset_minutes)
    records: list[MsgRecord] = [r for d in dialogs for r in d.records]

    grand_total = sum(d.sent_count for d in dialogs)
    days_in_range = max((end - start).days, 1)
    daily_average = round(grand_total / days_in_range)

    # ---- top chats (ranked by messages the user sent) -------------------
    top_chats = []
    for d in dialogs[:10]:
        total = d.total_count if d.total_count else d.sent_count
        top_chats.append({
            "name": d.name,
            "total": total,
            "pct": round(d.sent_count / max(grand_total, 1) * 100, 1),
            "sent": d.sent_count,
            "sent_share": round(min(d.sent_count / max(total, 1), 1.0) * 100, 1),
            "is_group": d.is_group,
            "avatar": None,
        })

    # ---- time distributions --------------------------------------------
    hour_w: defaultdict[int, float] = defaultdict(float)
    weekday_w: defaultdict[int, float] = defaultdict(float)
    month_w: defaultdict[tuple[int, int], float] = defaultdict(float)
    day_exact: Counter[date] = Counter()
    day_chat: dict[date, Counter[str]] = defaultdict(Counter)
    active_days: set[date] = set()
    per_dialog_days: dict[str, set[date]] = defaultdict(set)

    for r in records:
        local = r.date + offset
        hour_w[local.hour] += r.weight
        weekday_w[local.weekday()] += r.weight
        month_w[(local.year, local.month)] += r.weight
        day = local.date()
        active_days.add(day)
        per_dialog_days[r.dialog].add(day)
        if r.exact:
            day_exact[day] += 1
            day_chat[day][r.dialog] += 1

    hourly_distribution = {h: round(hour_w.get(h, 0.0)) for h in range(24)}
    peak_hour = max(range(24), key=lambda h: hour_w.get(h, 0.0)) if hour_w else 12
    total_night_messages = sum(hourly_distribution[h] for h in (22, 23, 0, 1, 2, 3))
    weekday_distribution = {d: round(weekday_w.get(d, 0.0)) for d in range(7)}

    monthly_activity = []
    cursor = (start + offset).replace(day=1)
    last = (end + offset)
    while (cursor.year, cursor.month) <= (last.year, last.month):
        monthly_activity.append({
            "month": cursor.strftime("%b"),
            "year": cursor.year,
            "count": round(month_w.get((cursor.year, cursor.month), 0.0)),
        })
        cursor = (cursor + timedelta(days=32)).replace(day=1)

    busiest_day = None
    if day_exact:
        bday, bcount = max(day_exact.items(), key=lambda kv: (kv[1], kv[0]))
        busiest_day = {
            "date": f"{bday.strftime('%B')} {bday.day}, {bday.year}",
            "count": bcount,
            "top_chat": day_chat[bday].most_common(1)[0][0] if day_chat[bday] else None,
        }

    # ---- streak ----------------------------------------------------------
    longest_streak = 0
    streak_partner = top_chats[0]["name"] if top_chats else "Unknown"
    for name, days in per_dialog_days.items():
        run = _longest_run(days)
        if run > longest_streak:
            longest_streak, streak_partner = run, name

    # ---- conversation dynamics ------------------------------------------
    user_starts, other_starts, reply_delays = conversation_dynamics(dialogs)
    starts = user_starts + other_starts
    user_pct = round(user_starts / starts * 100) if starts else 50

    reply_speed = None
    all_delays = [x for v in reply_delays.values() for x in v]
    if len(all_delays) >= MIN_REPLY_SAMPLES:
        fastest = None
        for name, delays in reply_delays.items():
            if len(delays) >= MIN_REPLY_SAMPLES:
                med = statistics.median(delays)
                if fastest is None or med < fastest[1]:
                    fastest = (name, med)
        reply_speed = {
            "median_seconds": round(statistics.median(all_delays)),
            "samples": len(all_delays),
            "fastest_chat": fastest[0] if fastest else None,
            "fastest_seconds": round(fastest[1]) if fastest else None,
        }

    # ---- most reacted ------------------------------------------------------
    most_reacted = None
    best = max(records, key=lambda r: r.reaction_total, default=None)
    if best is not None and best.reaction_total > 0:
        most_reacted = {
            "text": best.message or "(media)",
            "chat": best.dialog,
            "sender": "You",
            "date": (best.date + offset).strftime("%B %d"),
            "reactions": [{"emoji": e, "count": c} for e, c in (best.reactions or [])],
            "reply_preview": None,
        }

    # ---- media & stickers ------------------------------------------------
    media_w: defaultdict[str, float] = defaultdict(float)
    sticker_w: defaultdict[int, float] = defaultdict(float)
    sticker_raw: Counter[int] = Counter()
    sticker_emoji: dict[int, str] = {}
    for r in records:
        if r.media_kind == "sticker" and r.sticker_id is not None:
            sticker_w[r.sticker_id] += r.weight
            sticker_raw[r.sticker_id] += 1
            sticker_emoji.setdefault(r.sticker_id, r.sticker_emoji or "🔖")
        elif r.media_kind:
            media_w[r.media_kind] += r.weight
        if r.has_link:
            media_w["links"] += r.weight
    media_totals = {k: round(media_w.get(k, 0.0)) for k in MEDIA_KEYS}
    stickers_sent = round(sum(sticker_w.values()))
    min_conf = 1 if collected.exact else 2
    top_stickers = [
        {"emoji": sticker_emoji[sid], "count": round(w), "sticker_id": sid}
        for sid, w in sorted(sticker_w.items(), key=lambda kv: kv[1], reverse=True)
        if sticker_raw[sid] >= min_conf
    ][:10]

    # ---- text ------------------------------------------------------------
    weighted_texts = [(r.message, r.weight) for r in records if r.message]
    text_results = _process_text_batch(_sample_texts(weighted_texts, MAX_TEXTS_FOR_ANALYSIS))
    top_emojis = [
        {"emoji": e, "count": round(c)}
        for e, c in sorted(text_results["emojis"].items(), key=lambda x: x[1], reverse=True)[:10]
    ]
    top_words = [
        {"word": w, "count": round(c)}
        for w, c in sorted(text_results["words"].items(), key=lambda x: x[1], reverse=True)[:20]
    ]
    top_bigrams = [
        {"phrase": p, "count": round(c)}
        for p, c in sorted(text_results["phrases"].items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    # ---- ML: texter type & vibe age ---------------------------------------
    texter_type, vibe_age = _classify(
        dialogs, records, media_totals, grand_total, hourly_distribution,
        weighted_texts, stickers_sent, user_pct,
    )

    fetched = sum(d.fetched_unique for d in dialogs)
    accuracy = {
        "mode": "exact" if collected.exact else "estimated",
        "coverage_pct": round(min(fetched / max(grand_total, 1), 1.0) * 100, 1),
        "total_exact": collected.total_exact,
        "messages_analyzed": fetched,
        "chats_analyzed": len(dialogs),
        "takeout": takeout,
        "duration_seconds": round(duration_seconds, 1),
        "api_calls": collected.api_calls,
    }

    return {
        "grand_total": grand_total,
        "daily_average": daily_average,
        "top_chats": top_chats,
        "peak_hour": peak_hour,
        "peak_personality": _get_peak_personality(peak_hour),
        "hourly_distribution": hourly_distribution,
        "total_night_messages": total_night_messages,
        "longest_streak": longest_streak,
        "streak_partner": streak_partner,
        "conversation_starter": {"user_pct": user_pct, "other_pct": 100 - user_pct},
        "most_reacted_message": most_reacted,
        "top_emojis": top_emojis,
        "top_stickers": top_stickers,
        "texter_type": texter_type,
        "top_sticker_pack": None,
        "top_words": top_words,
        "top_bigrams": top_bigrams,
        "media_totals": media_totals,
        "date_range": {"start": start.strftime("%b %Y"), "end": end.strftime("%b %Y")},
        "vibe_age": vibe_age,
        "total_chats": len(dialogs),
        "active_days": len(active_days),
        "stickers_sent": stickers_sent,
        "monthly_activity": monthly_activity,
        "weekday_distribution": weekday_distribution,
        "busiest_day": busiest_day,
        "reply_speed": reply_speed,
        "accuracy": accuracy,
    }


def _classify(
    dialogs: list[DialogData],
    records: list[MsgRecord],
    media_totals: dict[str, int],
    grand_total: int,
    hourly_distribution: dict[int, int],
    weighted_texts: list[tuple[str, float]],
    stickers_sent: int,
    user_pct: int,
) -> tuple[dict[str, Any] | None, int | None]:
    from app.ml.features import compute_per_dialog_features, compute_self_calibration, extract_features
    from app.ml.inference import classify_texter_type, self_calibrate_axes
    from app.ml.vibe_age import compute_vibe_age_from_texts

    per_texts: dict[str, list[tuple[str, float]]] = {}
    per_msgs: dict[str, list[MsgRecord]] = {}
    per_hours: dict[str, dict[int, float]] = {}
    per_media: dict[str, dict[str, int]] = {}
    per_stickers: dict[str, int] = {}
    per_totals: dict[str, int] = {}
    rng = random.Random(11)
    for d in dialogs:
        if not d.records:
            continue
        sample = d.records
        if len(sample) > MAX_RECORDS_PER_DIALOG_FEATURES:
            sample = rng.sample(sample, MAX_RECORDS_PER_DIALOG_FEATURES)
        hours: defaultdict[int, float] = defaultdict(float)
        media: defaultdict[str, float] = defaultdict(float)
        stickers = 0.0
        for r in sample:
            hours[r.date.hour] += r.weight
            if r.media_kind == "sticker":
                stickers += r.weight
            elif r.media_kind:
                media[r.media_kind] += r.weight
            if r.has_link:
                media["links"] += r.weight
        # Rates are ratios, so a sample uses the sample's weighted size as denominator
        per_texts[d.name] = [(r.message, r.weight) for r in sample if r.message]
        per_msgs[d.name] = sample
        per_hours[d.name] = dict(hours)
        per_media[d.name] = {k: round(v) for k, v in media.items()}
        per_stickers[d.name] = round(stickers)
        per_totals[d.name] = max(round(sum(r.weight for r in sample)), 1)

    per_dialog_feats = compute_per_dialog_features(
        per_dialog_texts=per_texts,
        per_dialog_messages=per_msgs,
        per_dialog_hours=per_hours,
        media_per_dialog=per_media,
        dialog_totals=per_totals,
        sticker_per_dialog=per_stickers,
    )
    axis_calibration = self_calibrate_axes(per_dialog_feats)
    vibe_calibration = compute_self_calibration(per_dialog_feats)

    texts = _sample_texts(weighted_texts, MAX_TEXTS_FOR_ANALYSIS)
    features = extract_features(
        sampled_messages=records,
        media_totals=media_totals,
        grand_total=grand_total,
        hourly_distribution=hourly_distribution,
        weighted_texts=texts,
        sticker_count=stickers_sent,
    )
    texter_type = classify_texter_type(features, conversation_starter_pct=user_pct, calibration=axis_calibration)
    vibe_age = compute_vibe_age_from_texts(texts, calibration=vibe_calibration)
    return texter_type, vibe_age
