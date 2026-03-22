"""4-Axis Texter Personality Classifier (Spotify-style).

Inspired by Spotify's Listening Personality system: 4 independent binary axes,
each scored from multiple features and normalized against population statistics.
4 binary axes = 2^4 = 16 unique personality types.

Axes:
  E/T  Expressive vs Text-Purist  (media usage)
  V/M  Verbose vs Minimal         (message length / richness)
  I/R  Initiator vs Reactor       (conversation starting / replying)
  N/D  Night Owl vs Day Person    (time-of-day patterns)

No ML model files required — pure deterministic scoring with population normalization.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

_META_PATH = Path(__file__).resolve().parent / "models" / "personality_types.json"
_meta_cache: dict[str, Any] | None = None

# Population statistics for each axis.
# center = population median, scale = population std dev.
# These are calibrated from the user's Telegram data export.
# If calibration hasn't been run, these defaults provide reasonable behavior.
AXIS_DEFINITIONS: dict[str, dict[str, Any]] = {
    "expressiveness": {
        "features": {
            "media_rate": 1.0,
            "sticker_rate": 0.8,
            "voice_note_rate": 0.7,
            "gif_rate": 0.6,
            "video_rate": 0.6,       # round videos + regular videos
            "emoji_per_message": 0.5,
            "photo_rate": 0.4,
            "document_rate": 0.3,
        },
        "center": 0.0126,
        "scale": 0.0265,
        "letters": ("E", "T"),
        "names": ("Expressive", "Text-Purist"),
    },
    "verbosity": {
        "features": {
            "avg_length": 1.0,
            "type_token_ratio": 0.6,
            "length_variance": 0.3,
            "question_rate": 0.3,    # questions signal engagement/elaboration
            "ellipsis_rate": 0.2,    # "..." suggests trailing thought / verbose style
        },
        "center": 12.8222,
        "scale": 15.4778,
        "letters": ("V", "M"),
        "names": ("Verbose", "Minimal"),
    },
    "initiative": {
        # initiative_score = conversation_starter_pct/100, injected into features before scoring
        "features": {
            "initiative_score": 1.0,   # primary signal: explicit starter %
            "reply_rate": -0.5,        # high reply rate = reactor tendency
            "forward_rate": -0.3,      # forwarding = passive engagement
        },
        "center": 0.44,    # ~50% starter pct minus small reply/forward drag
        "scale": 0.18,
        "letters": ("I", "R"),
        "names": ("Initiator", "Reactor"),
    },
    "time_of_day": {
        "features": {
            "late_night_rate": 1.0,
            "morning_rate": -0.8,
        },
        "center": -0.0038,
        "scale": 0.0788,
        "letters": ("N", "D"),
        "names": ("Night Owl", "Day Person"),
    },
}


def _load_personality_meta() -> dict[str, Any]:
    global _meta_cache
    if _meta_cache is None:
        try:
            with open(_META_PATH) as f:
                _meta_cache = json.load(f)
        except FileNotFoundError:
            _meta_cache = {}
    return _meta_cache


def _compute_axis_score(features: dict[str, float], axis_def: dict[str, Any]) -> float:
    """Compute a single axis score from multiple weighted features."""
    feature_weights = axis_def["features"]
    weighted_sum = 0.0
    weight_total = 0.0

    for feat_name, weight in feature_weights.items():
        value = features.get(feat_name, 0.0)
        weighted_sum += value * weight
        weight_total += abs(weight)

    if weight_total == 0:
        return 0.0
    return weighted_sum / weight_total


def _z_score(value: float, center: float, scale: float) -> float:
    """Normalize a value to a z-score relative to population stats."""
    if scale <= 0:
        return 0.0
    return (value - center) / scale


def self_calibrate_axes(
    per_dialog_features: list[dict[str, float]],
) -> dict[str, dict[str, Any]] | None:
    """Compute per-user axis calibration from per-dialog feature vectors.

    Returns a copy of AXIS_DEFINITIONS with center/scale overridden to
    the user's own median/std. Applies Tukey IQR outlier filtering so
    one anomalous chat (e.g. a bot dump or spam thread) doesn't skew all axes.
    Returns None if insufficient data after filtering.
    """
    if len(per_dialog_features) < 5:
        return None

    import statistics

    calibrated = {}
    for axis_name, axis_def in AXIS_DEFINITIONS.items():
        scores = [_compute_axis_score(f, axis_def) for f in per_dialog_features]

        # Tukey IQR filter: remove scores beyond 1.5 * IQR from Q1/Q3
        sorted_s = sorted(scores)
        n = len(sorted_s)
        q1 = sorted_s[n // 4]
        q3 = sorted_s[(3 * n) // 4]
        iqr = q3 - q1
        fence_lo = q1 - 1.5 * iqr
        fence_hi = q3 + 1.5 * iqr
        clean = [s for s in scores if fence_lo <= s <= fence_hi]
        if len(clean) < 3:
            clean = scores  # fallback: too aggressive, keep all

        calibrated[axis_name] = dict(axis_def)
        calibrated[axis_name]["center"] = statistics.median(clean)
        std = statistics.stdev(clean) if len(clean) > 1 else 0.01
        calibrated[axis_name]["scale"] = max(std, 1e-6)

    return calibrated


def classify_texter_type(
    features: dict[str, float],
    conversation_starter_pct: float = 50.0,
    calibration: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Classify a user into one of 16 personality types using 4 binary axes.

    Args:
        features: dict produced by extract_features() in features.py
        conversation_starter_pct: percentage of conversations the user initiated
        calibration: optional self-calibrated axis definitions (overrides defaults)

    Returns:
        dict with keys: type, description, fun_fact, traits, code
    """
    meta = _load_personality_meta()
    axes = calibration if calibration is not None else AXIS_DEFINITIONS

    enriched = dict(features)
    enriched["initiative_score"] = conversation_starter_pct / 100.0

    code = ""
    axis_scores: dict[str, float] = {}
    axis_labels: list[str] = []

    for axis_name, axis_def in axes.items():
        raw = _compute_axis_score(enriched, axis_def)

        z = _z_score(raw, axis_def["center"], axis_def["scale"])
        axis_scores[axis_name] = z

        letters = axis_def["letters"]
        names = axis_def["names"]
        if z > 0:
            code += letters[0]
            axis_labels.append(names[0])
        else:
            code += letters[1]
            axis_labels.append(names[1])

    personality = meta.get(code)
    if personality is None:
        personality = {
            "display_name": " / ".join(axis_labels),
            "description": f"Your texting personality code is {code} — a unique blend of {', '.join(axis_labels).lower()}.",
            "fun_fact": f"Only 1 in 16 texters shares your exact {code} personality code.",
            "traits": axis_labels,
        }

    return {
        "type": personality["display_name"],
        "description": personality["description"],
        "fun_fact": personality.get("fun_fact", ""),
        "traits": personality.get("traits", axis_labels),
        "code": code,
    }
