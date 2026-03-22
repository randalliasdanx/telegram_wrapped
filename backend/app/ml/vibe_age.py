"""Texting Vibe Age Estimator.

Deterministic scoring function that estimates a user's "texting vibe age" (13-75)
based on linguistic features calibrated against population statistics.

The model uses 8 linguistic features, each z-score normalized against population
statistics derived from the user's Telegram data export. Features are combined
with research-backed weights reflecting known age-correlated texting patterns:

- Higher emoji usage -> younger
- More abbreviations -> younger
- Shorter messages -> younger
- Less capitalization -> younger
- Less punctuation -> younger
- More lowercase -> younger
- More exclamation marks -> younger
- Lower vocabulary richness -> younger
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

_STATS_PATH = Path(__file__).resolve().parent / "models" / "vibe_age_stats.json"
_stats_cache: dict[str, Any] | None = None

# Feature weights: positive = feature correlates with OLDER texting style.
# Negative = feature correlates with YOUNGER texting style.
# Calibrated from sociolinguistic research on digital communication and age.
FEATURE_WEIGHTS: dict[str, float] = {
    "emoji_per_message": -8.0,      # younger texters use more emoji
    "abbreviation_rate": -10.0,     # younger texters abbreviate more
    "avg_msg_length": 6.0,          # older texters write longer messages
    "all_caps_rate": -6.0,          # ALL CAPS messages = younger style
    "initial_caps_rate": 5.0,       # starting messages with capital = older style
    "punctuation_rate": 7.0,        # older texters punctuate more
    "lowercase_ratio": -3.0,        # younger texters use more lowercase
    "exclamation_rate": -4.0,       # younger texters use more exclamation marks
    "vocabulary_richness": 8.0,     # older texters have richer vocabulary
}

BASE_AGE = 25.0
AGE_MIN = 13
AGE_MAX = 75

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


def _load_stats() -> dict[str, dict[str, float]]:
    global _stats_cache
    if _stats_cache is None:
        try:
            with open(_STATS_PATH) as f:
                _stats_cache = json.load(f)
        except FileNotFoundError:
            _stats_cache = {}
    return _stats_cache


def _z_score(value: float, stat: dict[str, float]) -> float:
    """Compute z-score clipped to [-3, 3] to prevent extreme outliers."""
    std = stat.get("std", 1.0)
    if std <= 0:
        return 0.0
    z = (value - stat.get("mean", 0.0)) / std
    return max(-3.0, min(3.0, z))


def _sigmoid(x: float) -> float:
    """Smooth sigmoid to map raw score to [0, 1] range."""
    return 1.0 / (1.0 + math.exp(-x))


def compute_vibe_age(
    features: dict[str, float],
    calibration: dict[str, dict[str, float]] | None = None,
) -> int:
    """Compute texting vibe age from extracted features.

    Args:
        features: dict produced by extract_features() in features.py.
        calibration: optional self-calibrated stats dict, overrides shipped defaults

    Returns:
        int: Estimated vibe age in range [13, 75].
    """
    stats = calibration if calibration is not None else _load_stats()

    feature_values = _extract_vibe_features(features)

    weighted_z_sum = 0.0
    total_weight = 0.0

    for feat_name, weight in FEATURE_WEIGHTS.items():
        if feat_name not in feature_values:
            continue
        stat = stats.get(feat_name)
        if stat is None:
            continue

        z = _z_score(feature_values[feat_name], stat)
        weighted_z_sum += z * weight
        total_weight += abs(weight)

    if total_weight == 0:
        return int(BASE_AGE)

    normalized_score = weighted_z_sum / total_weight

    age_offset = normalized_score * 20.0
    raw_age = BASE_AGE + age_offset

    return max(AGE_MIN, min(AGE_MAX, round(raw_age)))


def _extract_vibe_features(features: dict[str, float]) -> dict[str, float]:
    """Map extract_features() output to vibe-age feature names."""
    vibe = {}

    vibe["emoji_per_message"] = features.get("emoji_per_message", 0.0)
    vibe["avg_msg_length"] = features.get("avg_length", 0.0)
    vibe["all_caps_rate"] = features.get("all_caps_rate", 0.0)
    vibe["initial_caps_rate"] = features.get("initial_caps_rate", 0.0)
    vibe["vocabulary_richness"] = features.get("type_token_ratio", 0.0)
    vibe["exclamation_rate"] = features.get("exclamation_rate", 0.0)

    vibe["punctuation_rate"] = features.get("question_rate", 0.0) + features.get("ellipsis_rate", 0.0)

    vibe["abbreviation_rate"] = features.get("abbreviation_rate", 0.015)
    vibe["lowercase_ratio"] = 1.0 - features.get("cap_rate", 0.0)

    return vibe


def compute_vibe_age_from_texts(
    weighted_texts: list[tuple[str, float]],
    calibration: dict[str, dict[str, float]] | None = None,
) -> int:
    """Compute vibe age directly from raw weighted texts for maximum accuracy.

    Args:
        weighted_texts: list of (text, weight) tuples
        calibration: optional self-calibrated stats dict, overrides shipped defaults
    """
    if not weighted_texts:
        return int(BASE_AGE)

    total_weight = 0.0
    total_chars = 0
    total_upper = 0
    total_lower = 0
    total_punct = 0
    total_exclaim = 0
    total_emoji = 0
    total_words = 0
    total_abbrev = 0
    total_length_weighted = 0.0
    all_caps_count = 0.0
    initial_caps_count = 0.0
    unique_words: set[str] = set()

    import re
    emoji_re = re.compile(
        "["
        "\U0001F300-\U0001FAFF"
        "\U00002700-\U000027BF"
        "\U0001F1E6-\U0001F1FF"
        "]",
        flags=re.UNICODE,
    )

    for text, weight in weighted_texts:
        total_weight += weight
        total_length_weighted += len(text) * weight

        for c in text:
            if c.isupper():
                total_upper += 1
            elif c.islower():
                total_lower += 1
            total_chars += 1

        # ALL CAPS detection: >50% of alphabetic chars are uppercase
        alpha_chars = [c for c in text if c.isalpha()]
        if alpha_chars:
            upper_frac = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if upper_frac > 0.5:
                all_caps_count += weight
            first_alpha = next((c for c in text if c.isalpha()), None)
            if first_alpha and first_alpha.isupper():
                initial_caps_count += weight

        total_punct += text.count(".") + text.count(",") + text.count(";") + text.count(":")
        total_exclaim += text.count("!")
        total_emoji += len(emoji_re.findall(text))

        words = text.lower().split()
        total_words += len(words)
        unique_words.update(words)
        total_abbrev += sum(1 for w in words if w in COMMON_ABBREVIATIONS)

    n = max(total_weight, 1.0)
    tc = max(total_chars, 1)
    tw = max(total_words, 1)

    raw_features = {
        "emoji_per_message": total_emoji / n,
        "abbreviation_rate": total_abbrev / tw,
        "avg_msg_length": total_length_weighted / n,
        "all_caps_rate": all_caps_count / n,
        "initial_caps_rate": initial_caps_count / n,
        "punctuation_rate": total_punct / tc,
        "lowercase_ratio": total_lower / tc,
        "exclamation_rate": total_exclaim / tc,
        "vocabulary_richness": len(unique_words) / tw,
    }

    stats = calibration if calibration is not None else _load_stats()

    weighted_z_sum = 0.0
    total_w = 0.0

    for feat_name, weight in FEATURE_WEIGHTS.items():
        stat = stats.get(feat_name)
        if stat is None:
            continue
        z = _z_score(raw_features.get(feat_name, 0.0), stat)
        weighted_z_sum += z * weight
        total_w += abs(weight)

    if total_w == 0:
        return int(BASE_AGE)

    normalized = weighted_z_sum / total_w
    raw_age = BASE_AGE + normalized * 20.0
    return max(AGE_MIN, min(AGE_MAX, round(raw_age)))
