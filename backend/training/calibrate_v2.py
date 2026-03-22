"""Calibrate population statistics for 4-axis texter personality + vibe age.

Reads a Telegram Desktop export (result.json), computes per-chat features,
and outputs calibration files used at runtime by inference.py and vibe_age.py.

Usage:
    python -m training.calibrate_v2 --export path/to/result.json

Outputs:
    training/data/axis_calibration.json   (4-axis population stats)
    training/data/vibe_age_stats.json     (vibe age population stats)
    app/ml/models/vibe_age_stats.json     (runtime copy)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

COMMON_ABBREVIATIONS = {
    "lol", "lmao", "omg", "idk", "imo", "tbh", "ngl", "brb", "gtg", "ttyl",
    "smh", "fyi", "iirc", "tldr", "afk", "btw", "icymi", "rofl", "wbu", "hbu",
    "rn", "nvm", "imo", "imho", "irl", "dm", "pm", "ty", "thx", "np", "pls",
    "plz", "bc", "cuz", "tho", "gonna", "wanna", "gotta", "lemme", "kinda",
    "sorta", "lmk", "wdym", "istg", "ikr", "fr", "ofc", "jk", "ily",
    "bff", "fomo", "yolo", "goat", "sus", "nah", "ya", "yea", "yep", "yup",
    "aight", "bet", "haha", "hahaha", "hehe", "hihi", "lolol", "xd",
    "omfg", "stfu", "wtf", "wth", "ftw", "w", "l",
}

EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]",
    flags=re.UNICODE,
)


def load_messages(path: str) -> list[dict]:
    print(f"Loading {path}...")
    with open(path) as f:
        data = json.load(f)

    messages = []
    for chat in data.get("chats", {}).get("list", []):
        chat_type = chat.get("type", "")
        if chat_type not in ("personal_chat", "private_group", "private_supergroup"):
            continue

        for msg in chat.get("messages", []):
            if msg.get("type") != "message":
                continue
            text = msg.get("text", "")
            if isinstance(text, list):
                text = "".join(
                    t["text"] if isinstance(t, dict) else t for t in text
                )
            messages.append({
                "from_id": msg.get("from_id", ""),
                "date": msg.get("date", ""),
                "text": text,
                "media_type": msg.get("media_type"),
                "forwarded_from": msg.get("forwarded_from"),
                "reply_to_message_id": msg.get("reply_to_message_id"),
                "chat_id": chat.get("id"),
            })

    print(f"Loaded {len(messages)} messages from {len(data.get('chats', {}).get('list', []))} chats")
    return messages


def compute_features_per_chat(messages: list[dict], my_id: str) -> list[dict]:
    """Compute features per chat for the user's messages."""
    by_chat: dict[Any, list[dict]] = defaultdict(list)
    for msg in messages:
        if msg["from_id"] == my_id:
            by_chat[msg["chat_id"]].append(msg)

    all_chat_features = []

    for chat_id, msgs in by_chat.items():
        if len(msgs) < 10:
            continue

        texts = [m["text"] for m in msgs if m["text"]]
        if not texts:
            continue

        # Texter axis features
        total = len(msgs)
        media_count = sum(1 for m in msgs if m.get("media_type"))
        sticker_count = sum(1 for m in msgs if m.get("media_type") == "sticker")
        gif_count = sum(1 for m in msgs if m.get("media_type") == "animation")
        voice_count = sum(1 for m in msgs if m.get("media_type") == "voice_message")
        photo_count = sum(1 for m in msgs if m.get("media_type") == "photo")
        forward_count = sum(1 for m in msgs if m.get("forwarded_from"))
        reply_count = sum(1 for m in msgs if m.get("reply_to_message_id"))

        all_text = " ".join(texts)
        words = all_text.lower().split()
        total_words = max(len(words), 1)
        unique_words = len(set(words))
        emoji_count = len(EMOJI_RE.findall(all_text))
        total_chars = max(len(all_text), 1)

        lengths = [len(t) for t in texts]
        avg_length = np.mean(lengths)
        length_std = np.std(lengths) if len(lengths) > 1 else 0.0
        ttr = unique_words / total_words

        upper = sum(1 for c in all_text if c.isupper())
        cap_rate = upper / total_chars
        question_rate = all_text.count("?") / total_chars
        ellipsis_rate = len(re.findall(r"\.\.\.", all_text)) / total_chars

        # Per-message caps style (for vibe age)
        all_caps_count = 0
        initial_caps_count = 0
        for t in texts:
            alpha_chars = [c for c in t if c.isalpha()]
            if alpha_chars:
                upper_frac = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
                if upper_frac > 0.5:
                    all_caps_count += 1
                first_alpha = next((c for c in t if c.isalpha()), None)
                if first_alpha and first_alpha.isupper():
                    initial_caps_count += 1
        all_caps_rate = all_caps_count / max(len(texts), 1)
        initial_caps_rate = initial_caps_count / max(len(texts), 1)

        # Time-of-day features
        hours = []
        for m in msgs:
            try:
                dt = datetime.fromisoformat(m["date"])
                hours.append(dt.hour)
            except (ValueError, TypeError):
                pass

        late_night = sum(1 for h in hours if h in (0, 1, 2, 3, 4)) / max(len(hours), 1)
        morning = sum(1 for h in hours if h in (6, 7, 8, 9)) / max(len(hours), 1)

        # Vibe age features
        punct_count = sum(1 for c in all_text if c in ".,:;")
        exclaim_count = all_text.count("!")
        lower_count = sum(1 for c in all_text if c.islower())
        abbrev_count = sum(1 for w in words if w in COMMON_ABBREVIATIONS)

        features = {
            # Texter axes
            "media_rate": media_count / total,
            "sticker_rate": sticker_count / total,
            "gif_rate": gif_count / total,
            "voice_note_rate": voice_count / total,
            "photo_rate": photo_count / total,
            "emoji_per_message": emoji_count / total,
            "avg_length": float(avg_length),
            "length_variance": float(length_std),
            "type_token_ratio": ttr,
            "edit_rate": 0.0,
            "forward_rate": forward_count / total,
            "reply_rate": reply_count / total,
            "late_night_rate": late_night,
            "morning_rate": morning,
            "cap_rate": cap_rate,
            "question_rate": question_rate,
            "ellipsis_rate": ellipsis_rate,
            # Vibe age features
            "avg_msg_length": float(avg_length),
            "all_caps_rate": all_caps_rate,
            "initial_caps_rate": initial_caps_rate,
            "punctuation_rate": punct_count / total_chars,
            "exclamation_rate": exclaim_count / total_chars,
            "lowercase_ratio": lower_count / total_chars,
            "abbreviation_rate": abbrev_count / total_words,
            "vocabulary_richness": ttr,
        }
        all_chat_features.append(features)

    return all_chat_features


def compute_axis_calibration(features_list: list[dict]) -> dict:
    """Compute population center and scale for each texter axis."""
    from app.ml.inference import AXIS_DEFINITIONS, _compute_axis_score

    axis_stats = {}
    for axis_name, axis_def in AXIS_DEFINITIONS.items():
        scores = [_compute_axis_score(f, axis_def) for f in features_list]
        axis_stats[axis_name] = {
            "center": float(np.median(scores)),
            "scale": float(np.std(scores)) if len(scores) > 1 else 0.1,
            "mean": float(np.mean(scores)),
            "p25": float(np.percentile(scores, 25)),
            "p75": float(np.percentile(scores, 75)),
            "n": len(scores),
        }

    return axis_stats


def compute_vibe_age_calibration(features_list: list[dict]) -> dict:
    """Compute population stats for each vibe age feature."""
    vibe_features = [
        "emoji_per_message", "abbreviation_rate", "avg_msg_length",
        "all_caps_rate", "initial_caps_rate", "punctuation_rate", "lowercase_ratio",
        "exclamation_rate", "vocabulary_richness",
    ]

    stats = {}
    for feat in vibe_features:
        values = [f.get(feat, 0.0) for f in features_list]
        if not values:
            continue
        stats[feat] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)) if len(values) > 1 else 0.01,
            "p25": float(np.percentile(values, 25)),
            "p50": float(np.percentile(values, 50)),
            "p75": float(np.percentile(values, 75)),
        }

    return stats


def main():
    parser = argparse.ArgumentParser(description="Calibrate ML models from Telegram export")
    parser.add_argument("--export", required=True, help="Path to result.json")
    parser.add_argument("--my-id", default=None, help="Your from_id. If not set, uses the most common sender.")
    args = parser.parse_args()

    messages = load_messages(args.export)

    if args.my_id:
        my_id = args.my_id
    else:
        sender_counts: dict[str, int] = defaultdict(int)
        for m in messages:
            if m["from_id"]:
                sender_counts[m["from_id"]] += 1
        my_id = max(sender_counts, key=sender_counts.get)  # type: ignore
        print(f"Auto-detected user ID: {my_id} ({sender_counts[my_id]} messages)")

    features_list = compute_features_per_chat(messages, my_id)
    print(f"Computed features for {len(features_list)} chats")

    if not features_list:
        print("ERROR: No features computed. Check export path and user ID.")
        sys.exit(1)

    # Calibrate 4-axis texter personality
    axis_stats = compute_axis_calibration(features_list)
    axis_path = Path("training/data/axis_calibration.json")
    axis_path.parent.mkdir(parents=True, exist_ok=True)
    with open(axis_path, "w") as f:
        json.dump(axis_stats, f, indent=2)
    print(f"Wrote axis calibration to {axis_path}")

    # Calibrate vibe age
    vibe_stats = compute_vibe_age_calibration(features_list)
    vibe_path = Path("training/data/vibe_age_stats.json")
    with open(vibe_path, "w") as f:
        json.dump(vibe_stats, f, indent=2)
    print(f"Wrote vibe age stats to {vibe_path}")

    # Copy to runtime paths
    runtime_vibe = Path("app/ml/models/vibe_age_stats.json")
    runtime_vibe.parent.mkdir(parents=True, exist_ok=True)
    with open(runtime_vibe, "w") as f:
        json.dump(vibe_stats, f, indent=2)
    print(f"Copied vibe age stats to {runtime_vibe}")

    # Update axis definitions in inference.py
    print("\n--- Axis Calibration Results ---")
    for axis_name, stats in axis_stats.items():
        print(f"  {axis_name}: center={stats['center']:.4f}, scale={stats['scale']:.4f} (n={stats['n']})")

    print("\n--- Vibe Age Stats ---")
    for feat, stats in vibe_stats.items():
        print(f"  {feat}: mean={stats['mean']:.4f}, std={stats['std']:.4f}")

    print("\nCalibration complete. To apply axis calibration to inference.py, update AXIS_DEFINITIONS.")


if __name__ == "__main__":
    main()
