from __future__ import annotations

import re
import statistics
from typing import Any

FEATURE_COLS = [
    "voice_note_rate",
    "photo_rate",
    "gif_rate",
    "video_rate",
    "document_rate",
    "link_rate",
    "music_rate",
    "avg_length",
    "length_variance",
    "type_token_ratio",
    "cap_rate",
    "all_caps_rate",
    "initial_caps_rate",
    "question_rate",
    "ellipsis_rate",
    "forward_rate",
    "late_night_rate",
    "sticker_rate",
    "reply_rate",
    "edit_rate",
    "emoji_per_message",
    "media_rate",
    "morning_rate",
]

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]",
    flags=re.UNICODE,
)


def extract_features(
    sampled_messages: list[Any],
    media_totals: dict[str, int],
    grand_total: int,
    hourly_distribution: dict[int, int],
    weighted_texts: list[tuple[str, float]],
    sticker_count: int = 0,
) -> dict[str, float]:
    """Extract a feature vector from pipeline data for archetype classification.

    Text features now use weighted_texts (properly scaled by dialog weight)
    instead of unweighted sampled_messages. Metadata features (reply, edit,
    forward rates) are extracted from sampled_messages at zero API cost.
    """
    gt = max(grand_total, 1)

    # --- Exact rates from Phase 2 media counts (now across ALL dialogs) ---
    voice_note_rate = media_totals.get("voice_notes", 0) / gt
    photo_rate = media_totals.get("photos", 0) / gt
    gif_rate = media_totals.get("gifs", 0) / gt
    video_rate = (media_totals.get("videos", 0) + media_totals.get("round_videos", 0)) / gt
    document_rate = media_totals.get("documents", 0) / gt
    link_rate = media_totals.get("links", 0) / gt
    music_rate = media_totals.get("music", 0) / gt

    total_media = sum(media_totals.values())
    media_rate = total_media / gt

    sticker_rate_val = sticker_count / gt

    # --- Text-based features from WEIGHTED texts ---
    total_weight = 0.0
    weighted_length_sum = 0.0
    weighted_chars: list[str] = []
    weighted_words_all: list[str] = []
    weighted_word_set: set[str] = set()
    emoji_count_weighted = 0.0

    for text, weight in weighted_texts:
        total_weight += weight
        weighted_length_sum += len(text) * weight
        weighted_chars.append(text)
        words = text.lower().split()
        weighted_words_all.extend(words)
        weighted_word_set.update(words)
        emoji_count_weighted += len(_EMOJI_RE.findall(text)) * weight

    avg_length = weighted_length_sum / max(total_weight, 1.0)

    # Length variance (weighted)
    variance_sum = 0.0
    for text, weight in weighted_texts:
        variance_sum += ((len(text) - avg_length) ** 2) * weight
    length_variance = (variance_sum / max(total_weight, 1.0)) ** 0.5

    total_words = max(len(weighted_words_all), 1)
    unique_words = len(weighted_word_set)
    type_token_ratio = unique_words / total_words

    all_text = " ".join(weighted_chars) if weighted_chars else ""
    total_chars = max(len(all_text), 1)
    cap_rate = sum(1 for c in all_text if c.isupper()) / total_chars
    question_rate = all_text.count("?") / total_chars
    ellipsis_rate = len(re.findall(r"\.\.\.", all_text)) / total_chars

    # Split capitalization: ALL CAPS messages (young) vs initial-caps messages (old)
    all_caps_count = 0.0
    initial_caps_count = 0.0
    for text, weight in weighted_texts:
        alpha_chars = [c for c in text if c.isalpha()]
        if alpha_chars:
            upper_frac = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if upper_frac > 0.5:
                all_caps_count += weight
            first_alpha = next((c for c in text if c.isalpha()), None)
            if first_alpha and first_alpha.isupper():
                initial_caps_count += weight

    n_weighted_msgs = max(total_weight, 1.0)
    all_caps_rate = all_caps_count / n_weighted_msgs
    initial_caps_rate = initial_caps_count / n_weighted_msgs
    emoji_per_message = emoji_count_weighted / n_weighted_msgs

    # --- Metadata features from sampled messages (FREE, no API cost) ---
    n_samples = max(len(sampled_messages), 1)
    forward_count = sum(1 for msg in sampled_messages if getattr(msg, "forward", None))
    reply_count = sum(1 for msg in sampled_messages if getattr(msg, "reply_to", None))
    edit_count = sum(1 for msg in sampled_messages if getattr(msg, "edit_date", None))

    forward_rate = forward_count / n_samples
    reply_rate = reply_count / n_samples
    edit_rate = edit_count / n_samples

    # --- Time-of-day rates from hourly distribution ---
    total_hourly = sum(hourly_distribution.values()) or 1
    late_night = sum(hourly_distribution.get(h, 0) for h in (0, 1, 2, 3, 4))
    late_night_rate = late_night / total_hourly
    morning = sum(hourly_distribution.get(h, 0) for h in (6, 7, 8, 9))
    morning_rate = morning / total_hourly

    return {
        "voice_note_rate": voice_note_rate,
        "photo_rate": photo_rate,
        "gif_rate": gif_rate,
        "video_rate": video_rate,
        "document_rate": document_rate,
        "link_rate": link_rate,
        "music_rate": music_rate,
        "avg_length": avg_length,
        "length_variance": length_variance,
        "type_token_ratio": type_token_ratio,
        "cap_rate": cap_rate,
        "all_caps_rate": all_caps_rate,
        "initial_caps_rate": initial_caps_rate,
        "question_rate": question_rate,
        "ellipsis_rate": ellipsis_rate,
        "forward_rate": forward_rate,
        "late_night_rate": late_night_rate,
        "sticker_rate": sticker_rate_val,
        "reply_rate": reply_rate,
        "edit_rate": edit_rate,
        "emoji_per_message": emoji_per_message,
        "media_rate": media_rate,
        "morning_rate": morning_rate,
    }


def compute_per_dialog_features(
    per_dialog_texts: dict[str, list[tuple[str, float]]],
    per_dialog_messages: dict[str, list[Any]],
    per_dialog_hours: dict[str, dict[int, float]],
    media_per_dialog: dict[str, dict[str, int]],
    dialog_totals: dict[str, int],
    sticker_per_dialog: dict[str, int],
) -> list[dict[str, float]]:
    """Compute feature vectors per dialog for self-calibration.

    Each dialog yields one feature dict, computed from that dialog's
    sampled messages only. The collection of per-dialog features then
    provides the user's own "population" for normalization.
    """
    all_features = []

    for dname in per_dialog_texts:
        texts = per_dialog_texts[dname]
        msgs = per_dialog_messages.get(dname, [])
        hours = per_dialog_hours.get(dname, {})
        media = media_per_dialog.get(dname, {})
        total = dialog_totals.get(dname, max(len(msgs), 1))
        stickers = sticker_per_dialog.get(dname, 0)

        if len(texts) < 3:
            continue

        feats = extract_features(
            sampled_messages=msgs,
            media_totals=media,
            grand_total=total,
            hourly_distribution=hours,
            weighted_texts=texts,
            sticker_count=stickers,
        )
        all_features.append(feats)

    return all_features


def compute_self_calibration(
    per_dialog_features: list[dict[str, float]],
    min_dialogs: int = 5,
) -> dict[str, dict[str, float]] | None:
    """Compute population stats (mean/std) from per-dialog feature vectors.

    Returns None if fewer than min_dialogs are available (falls back to
    shipped defaults in that case).
    """
    if len(per_dialog_features) < min_dialogs:
        return None

    stats: dict[str, dict[str, float]] = {}
    feature_names = per_dialog_features[0].keys()

    for feat in feature_names:
        values = [d[feat] for d in per_dialog_features if feat in d]
        if len(values) < min_dialogs:
            continue
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.01
        std = max(std, 1e-6)
        stats[feat] = {
            "mean": mean,
            "std": std,
            "p50": statistics.median(values),
        }

    return stats if stats else None
