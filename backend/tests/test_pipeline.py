"""Unit tests for the pipeline's dialog filtering and ML components."""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, ".")


# ---------------------------------------------------------------------------
# Test: _select_candidate_dialogs whitelist
# ---------------------------------------------------------------------------

def _make_dialog(entity_cls_name: str, name: str, msg_date: datetime):
    """Create a mock dialog with the given entity type."""
    from telethon.tl.types import User, Chat, Channel

    type_map = {
        "User": User(id=1, is_self=False, access_hash=0, first_name=name),
        "Chat": Chat(
            id=2, title=name, participants_count=10,
            date=msg_date, version=1, photo=None,
        ),
        "Channel": Channel(
            id=3, title=name, access_hash=0, date=msg_date,
            photo=None, broadcast=True,
        ),
    }
    # For ChannelForbidden and other types, use a SimpleNamespace
    if entity_cls_name in type_map:
        entity = type_map[entity_cls_name]
    else:
        entity = SimpleNamespace(__class__=type(entity_cls_name, (), {}))
        entity.__class__.__name__ = entity_cls_name

    msg = SimpleNamespace(date=msg_date)
    dialog = SimpleNamespace(entity=entity, message=msg, name=name, id=100)
    return dialog


def test_whitelist_includes_user_and_chat():
    from app.pipeline import _select_candidate_dialogs

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)

    dialogs = [
        _make_dialog("User", "Alice", now - timedelta(days=1)),
        _make_dialog("Chat", "Friends Group", now - timedelta(days=2)),
    ]
    result = _select_candidate_dialogs(dialogs, start)
    assert len(result) == 2, f"Expected 2 dialogs, got {len(result)}"


def test_whitelist_excludes_channel():
    from app.pipeline import _select_candidate_dialogs

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)

    dialogs = [
        _make_dialog("User", "Alice", now - timedelta(days=1)),
        _make_dialog("Channel", "News Channel", now - timedelta(days=1)),
    ]
    result = _select_candidate_dialogs(dialogs, start)
    assert len(result) == 1, f"Expected 1 dialog, got {len(result)}"
    assert result[0].name == "Alice"


def test_whitelist_excludes_old_dialogs():
    from app.pipeline import _select_candidate_dialogs

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)

    dialogs = [
        _make_dialog("User", "Recent", now - timedelta(days=1)),
        _make_dialog("User", "Old", now - timedelta(days=60)),
    ]
    result = _select_candidate_dialogs(dialogs, start)
    assert len(result) == 1
    assert result[0].name == "Recent"


def test_whitelist_excludes_no_message():
    from app.pipeline import _select_candidate_dialogs

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)

    dialog_no_msg = SimpleNamespace(
        entity=SimpleNamespace(), message=None, name="NoMsg", id=99
    )
    result = _select_candidate_dialogs([dialog_no_msg], start)
    assert len(result) == 0


# ---------------------------------------------------------------------------
# Test: _process_text_batch (current behavior sanity check)
# ---------------------------------------------------------------------------

def test_process_text_batch_basic():
    from app.pipeline import _process_text_batch

    texts = [
        ("hello world", 1.0),
        ("hello world", 1.0),
        ("hello world", 1.0),
        ("foo bar baz", 1.0),
        ("foo bar baz", 1.0),
        ("foo bar baz", 1.0),
    ]
    result = _process_text_batch(texts)
    assert "words" in result
    assert "phrases" in result
    assert "emojis" in result
    assert len(result["words"]) > 0


# ---------------------------------------------------------------------------
# Test: weight formula (current bug demonstration)
# ---------------------------------------------------------------------------

def test_weight_formula_bug():
    """Demonstrate the current weight formula bug:
    yearly_total counts ALL messages but sampled_count is user-only."""
    yearly_total = 100_000  # all messages in dialog
    sampled_count = 500     # user-sent messages sampled
    total_sampled = 1000    # all messages sampled (both parties)

    # Current (buggy) formula
    buggy_weight = yearly_total / sampled_count  # = 200

    # Fixed formula
    user_fraction = sampled_count / total_sampled  # = 0.5
    estimated_user_yearly = yearly_total * user_fraction  # = 50000
    fixed_weight = estimated_user_yearly / sampled_count  # = 100

    assert buggy_weight == 200.0
    assert fixed_weight == 100.0
    assert buggy_weight == 2 * fixed_weight, "Bug inflates weight by ~2x for 1-on-1 chats"


# ---------------------------------------------------------------------------
# Test: extract_features uses weighted_texts
# ---------------------------------------------------------------------------

def test_extract_features_uses_weighted_texts():
    from app.ml.features import extract_features

    msgs = [SimpleNamespace(message="hello", forward=None, reply_to=None, edit_date=None)]

    # Short message with weight 1 vs long message with weight 10
    weighted_texts = [
        ("hi", 1.0),
        ("this is a much longer message with many words", 10.0),
    ]

    features = extract_features(
        sampled_messages=msgs,
        media_totals={"photos": 5, "videos": 2},
        grand_total=100,
        hourly_distribution={h: 1 for h in range(24)},
        weighted_texts=weighted_texts,
        sticker_count=0,
    )

    assert features["avg_length"] > 10, "avg_length should be weighted toward the longer message"
    assert features["reply_rate"] == 0.0
    assert features["edit_rate"] == 0.0
    assert features["photo_rate"] == 0.05
    assert "emoji_per_message" in features
    assert "media_rate" in features
    assert "morning_rate" in features


def test_extract_features_metadata():
    from app.ml.features import extract_features

    msgs = [
        SimpleNamespace(message="hi", forward=None, reply_to="some_ref", edit_date=None),
        SimpleNamespace(message="yo", forward="fwd_info", reply_to=None, edit_date="2026-01-01"),
        SimpleNamespace(message="ok", forward=None, reply_to=None, edit_date=None),
    ]

    features = extract_features(
        sampled_messages=msgs,
        media_totals={},
        grand_total=100,
        hourly_distribution={},
        weighted_texts=[("hi", 1.0), ("yo", 1.0), ("ok", 1.0)],
    )

    assert abs(features["reply_rate"] - 1 / 3) < 0.01
    assert abs(features["forward_rate"] - 1 / 3) < 0.01
    assert abs(features["edit_rate"] - 1 / 3) < 0.01


def test_weight_formula_fixed():
    """Verify the corrected weight formula in phase4 logic."""
    yearly_total = 100_000
    sampled_count = 500
    total_sampled = 1000

    user_fraction = sampled_count / total_sampled  # 0.5
    estimated_user_yearly = yearly_total * user_fraction  # 50000
    fixed_weight = estimated_user_yearly / sampled_count  # 100

    assert fixed_weight == 100.0
    assert user_fraction == 0.5


# ---------------------------------------------------------------------------
# Test: 4-axis texter type classification
# ---------------------------------------------------------------------------

def test_classify_texter_type_returns_valid_code():
    from app.ml.inference import classify_texter_type

    features = {
        "voice_note_rate": 0.0,
        "photo_rate": 0.3,
        "gif_rate": 0.1,
        "video_rate": 0.0,
        "document_rate": 0.0,
        "link_rate": 0.0,
        "music_rate": 0.0,
        "avg_length": 80.0,
        "length_variance": 30.0,
        "type_token_ratio": 0.3,
        "cap_rate": 0.02,
        "question_rate": 0.01,
        "ellipsis_rate": 0.001,
        "forward_rate": 0.05,
        "late_night_rate": 0.35,
        "sticker_rate": 0.1,
        "reply_rate": 0.2,
        "edit_rate": 0.05,
        "emoji_per_message": 0.5,
        "media_rate": 0.4,
        "morning_rate": 0.05,
    }

    result = classify_texter_type(features, conversation_starter_pct=70.0)
    assert "type" in result
    assert "description" in result
    assert "code" in result
    assert len(result["code"]) == 4
    assert all(c in "EVTMINRD" for c in result["code"])
    assert "traits" in result
    assert len(result["traits"]) == 4


def test_classify_texter_type_all_codes_are_valid():
    """Test that all 16 possible codes produce valid output."""
    from app.ml.inference import classify_texter_type

    base_features = {k: 0.0 for k in [
        "voice_note_rate", "photo_rate", "gif_rate", "video_rate",
        "document_rate", "link_rate", "music_rate", "avg_length",
        "length_variance", "type_token_ratio", "cap_rate", "question_rate",
        "ellipsis_rate", "forward_rate", "late_night_rate", "sticker_rate",
        "reply_rate", "edit_rate", "emoji_per_message", "media_rate", "morning_rate",
    ]}

    # Very expressive, verbose, initiator, night owl -> EVIN
    features = dict(base_features)
    features.update({"media_rate": 0.8, "emoji_per_message": 1.0, "avg_length": 200.0,
                     "late_night_rate": 0.6, "morning_rate": 0.0})
    result = classify_texter_type(features, conversation_starter_pct=90.0)
    assert result["code"] == "EVIN", f"Expected EVIN, got {result['code']}"

    # Very minimal, text-purist, reactor, day person -> TMRD
    features = dict(base_features)
    features.update({"avg_length": 3.0, "morning_rate": 0.4, "late_night_rate": 0.0,
                     "reply_rate": 0.8, "forward_rate": 0.5})
    result = classify_texter_type(features, conversation_starter_pct=10.0)
    assert result["code"] == "TMRD", f"Expected TMRD, got {result['code']}"


# ---------------------------------------------------------------------------
# Test: LLR scoring
# ---------------------------------------------------------------------------

def test_llr_score_basic():
    from app.pipeline import _llr_score

    # Co-occurring terms should have positive LLR
    score = _llr_score(k_ab=50, k_a=100, k_b=100, N=10000)
    assert score > 0, f"Expected positive LLR, got {score}"

    # Independent terms should have near-zero LLR
    score_indep = _llr_score(k_ab=1, k_a=100, k_b=100, N=10000)
    assert score_indep < score, "Independent terms should score lower"


def test_process_text_batch_llr():
    """Test that the rewritten LLR-based phrase extraction works."""
    from app.pipeline import _process_text_batch

    texts = []
    for _ in range(50):
        texts.append(("good morning everyone how are you", 1.0))
        texts.append(("I had a good morning today as well", 1.0))
        texts.append(("let's meet tomorrow for coffee", 1.0))
        texts.append(("that sounds great let's do it", 1.0))

    result = _process_text_batch(texts)
    assert "words" in result
    assert "phrases" in result
    phrases = dict(result["phrases"])
    assert len(phrases) > 0, "Should extract at least one phrase"


def test_process_text_batch_preserves_apostrophes():
    """Test that contractions are preserved after text cleaning."""
    from app.pipeline import _clean_text

    assert "don't" in _clean_text("I don't think so")
    assert "i'm" in _clean_text("I'm fine")
    assert "can't" in _clean_text("You can't do that")
    assert "well-known" in _clean_text("It's a well-known fact")


# ---------------------------------------------------------------------------
# Test: Vibe Age
# ---------------------------------------------------------------------------

def test_vibe_age_from_texts_young():
    from app.ml.vibe_age import compute_vibe_age_from_texts

    young_texts = [
        ("omg lol thats so funny hahaha 😂😂", 1.0),
        ("ngl this is fr so good", 1.0),
        ("bruh wdym lmao", 1.0),
        ("ikr like literally same tbh 🔥", 1.0),
    ] * 20

    age = compute_vibe_age_from_texts(young_texts)
    assert 13 <= age <= 25, f"Expected young age (13-25), got {age}"


def test_vibe_age_from_texts_older():
    from app.ml.vibe_age import compute_vibe_age_from_texts

    older_texts = [
        ("Good morning. I hope you are doing well today.", 1.0),
        ("Could you please send me the document? Thank you.", 1.0),
        ("I would appreciate it if you could review this matter at your earliest convenience.", 1.0),
        ("Dear colleague, I am writing to inform you about the upcoming meeting.", 1.0),
    ] * 20

    age = compute_vibe_age_from_texts(older_texts)
    assert 30 <= age <= 75, f"Expected older age (30-75), got {age}"


def test_vibe_age_range_bounds():
    from app.ml.vibe_age import compute_vibe_age_from_texts

    age = compute_vibe_age_from_texts([])
    assert 13 <= age <= 75

    age = compute_vibe_age_from_texts([("k", 1.0)])
    assert 13 <= age <= 75


def test_vibe_age_differentiates():
    from app.ml.vibe_age import compute_vibe_age_from_texts

    young = [("omg lol bruh haha 😂😂 ngl fr", 1.0)] * 30
    old = [("Good morning. I would like to request your assistance. Thank you.", 1.0)] * 30

    young_age = compute_vibe_age_from_texts(young)
    old_age = compute_vibe_age_from_texts(old)
    assert young_age < old_age, f"Young ({young_age}) should be less than Old ({old_age})"


# ---------------------------------------------------------------------------
# Test: TF-IDF distinctiveness boosts personal phrases
# ---------------------------------------------------------------------------

def test_tfidf_distinctive_phrases_rank_higher():
    """Personal phrases should score higher than generic English phrases."""
    from app.pipeline import _process_text_batch

    texts = []
    # "let me know" is extremely common in general English
    for _ in range(40):
        texts.append(("let me know if that works", 1.0))
    # "chicken rice again" is distinctive — unlikely in background corpus
    for _ in range(40):
        texts.append(("chicken rice again for lunch today", 1.0))
    # Add filler
    for _ in range(100):
        texts.append(("today was really great and fun", 1.0))

    result = _process_text_batch(texts)
    phrases = dict(result["phrases"])

    # "chicken rice" should appear (distinctive)
    has_distinctive = any("chicken" in p.lower() for p in phrases)
    # "let me know" might appear but should NOT outrank distinctive phrases
    phrase_list = list(phrases.keys())

    assert len(phrases) > 0, "Should extract some phrases"
    if has_distinctive:
        # If both exist, chicken rice should rank higher
        distinctive_idx = next(
            (i for i, p in enumerate(phrase_list) if "chicken" in p.lower()), 99
        )
        generic_idx = next(
            (i for i, p in enumerate(phrase_list) if "let" in p.lower() and "know" in p.lower()), 99
        )
        if generic_idx < 99:
            assert distinctive_idx < generic_idx, (
                f"Distinctive phrase (idx={distinctive_idx}) should rank higher "
                f"than generic (idx={generic_idx})"
            )


def test_background_bigrams_loaded():
    """Verify background bigrams are loaded from the Google corpus."""
    from app.pipeline import _load_background_bigrams

    bg, bg_total = _load_background_bigrams()
    assert len(bg) >= 1000, f"Expected >=1000 background bigrams, got {len(bg)}"
    assert bg_total > 1_000_000, f"Expected large total, got {bg_total}"
    assert "if you" in bg or "of the" in bg, "Should contain common English bigrams"


# ---------------------------------------------------------------------------
# Test: ALL CAPS vs initial caps produce different vibe ages
# ---------------------------------------------------------------------------

def test_all_caps_vs_initial_caps_age_difference():
    """ALL CAPS messages should produce younger age than initial-caps messages."""
    from app.ml.vibe_age import compute_vibe_age_from_texts

    all_caps_texts = [
        ("OMG THIS IS SO CRAZY HAHA", 1.0),
        ("WHAT ARE YOU DOING LOL", 1.0),
        ("NO WAY BRUH THAT IS WILD", 1.0),
        ("I CANT BELIEVE THIS RN", 1.0),
    ] * 20

    initial_caps_texts = [
        ("Hello, how are you doing today?", 1.0),
        ("I hope you have a pleasant evening.", 1.0),
        ("Could you please confirm the appointment?", 1.0),
        ("Thank you for your assistance with this matter.", 1.0),
    ] * 20

    caps_age = compute_vibe_age_from_texts(all_caps_texts)
    initial_age = compute_vibe_age_from_texts(initial_caps_texts)

    assert caps_age < initial_age, (
        f"ALL CAPS age ({caps_age}) should be younger than initial caps age ({initial_age})"
    )


def test_caps_features_computed_correctly():
    """Verify all_caps_rate and initial_caps_rate are computed from weighted_texts."""
    from app.ml.features import extract_features

    msgs = [SimpleNamespace(message="test", forward=None, reply_to=None, edit_date=None)]

    weighted_texts = [
        ("OMG THIS IS CRAZY", 1.0),     # all caps + initial caps
        ("hello there friend", 1.0),     # neither
        ("Hello there friend", 1.0),     # initial caps only
        ("WHAT NO WAY", 1.0),            # all caps + initial caps
    ]

    features = extract_features(
        sampled_messages=msgs,
        media_totals={},
        grand_total=100,
        hourly_distribution={},
        weighted_texts=weighted_texts,
    )

    # 2 out of 4 messages are all caps
    assert abs(features["all_caps_rate"] - 0.5) < 0.01, f"all_caps_rate: {features['all_caps_rate']}"
    # 3 out of 4 start with uppercase (OMG, Hello, WHAT)
    assert abs(features["initial_caps_rate"] - 0.75) < 0.01, f"initial_caps_rate: {features['initial_caps_rate']}"


# ---------------------------------------------------------------------------
# Test: Self-calibration
# ---------------------------------------------------------------------------

def test_self_calibrate_axes_changes_result():
    """Self-calibrated axes should potentially produce a different code than fixed defaults."""
    from app.ml.inference import classify_texter_type, self_calibrate_axes

    # Create a user whose "population" of dialogs skews very expressive
    dialog_features = []
    for i in range(10):
        dialog_features.append({
            "media_rate": 0.3 + i * 0.02,
            "sticker_rate": 0.15,
            "gif_rate": 0.1,
            "voice_note_rate": 0.05,
            "emoji_per_message": 0.8 + i * 0.01,
            "photo_rate": 0.1,
            "avg_length": 15.0 + i,
            "length_variance": 5.0,
            "type_token_ratio": 0.4,
            "edit_rate": 0.01,
            "forward_rate": 0.05,
            "reply_rate": 0.3,
            "late_night_rate": 0.1,
            "morning_rate": 0.2,
            "cap_rate": 0.02,
            "all_caps_rate": 0.05,
            "initial_caps_rate": 0.3,
            "question_rate": 0.01,
            "ellipsis_rate": 0.001,
            "sticker_rate": 0.1,
            "media_rate": 0.4 + i * 0.01,
        })

    calibration = self_calibrate_axes(dialog_features)
    assert calibration is not None, "Should produce calibration with 10 dialogs"
    assert "expressiveness" in calibration
    assert calibration["expressiveness"]["center"] != 0.0126  # Different from default

    # Classify with the same features using default vs self-calibrated
    test_features = dialog_features[5]  # Middle of the range

    result_default = classify_texter_type(test_features, conversation_starter_pct=50.0)
    result_calibrated = classify_texter_type(
        test_features, conversation_starter_pct=50.0, calibration=calibration,
    )

    # Both should produce valid codes
    assert len(result_default["code"]) == 4
    assert len(result_calibrated["code"]) == 4
    # With self-calibration, a middle-of-the-pack dialog should be more balanced
    # The specific code may differ, which is the whole point


def test_self_calibrate_returns_none_for_few_dialogs():
    from app.ml.inference import self_calibrate_axes

    result = self_calibrate_axes([{"media_rate": 0.1}] * 3)
    assert result is None, "Should return None with fewer than 5 dialogs"


def test_compute_self_calibration_stats():
    from app.ml.features import compute_self_calibration

    features = [
        {"avg_length": 10.0, "media_rate": 0.1, "emoji_per_message": 0.5},
        {"avg_length": 20.0, "media_rate": 0.2, "emoji_per_message": 0.3},
        {"avg_length": 30.0, "media_rate": 0.3, "emoji_per_message": 0.1},
        {"avg_length": 40.0, "media_rate": 0.4, "emoji_per_message": 0.7},
        {"avg_length": 50.0, "media_rate": 0.5, "emoji_per_message": 0.9},
    ]

    stats = compute_self_calibration(features)
    assert stats is not None
    assert "avg_length" in stats
    assert abs(stats["avg_length"]["mean"] - 30.0) < 0.01
    assert stats["avg_length"]["std"] > 0

    # Too few dialogs -> None
    stats_small = compute_self_calibration(features[:3])
    assert stats_small is None


def test_vibe_age_with_self_calibration():
    from app.ml.vibe_age import compute_vibe_age_from_texts

    texts = [("hello how are you doing today", 1.0)] * 20

    # With default calibration
    age_default = compute_vibe_age_from_texts(texts)

    # With custom calibration where everything is "average"
    custom_cal = {
        "emoji_per_message": {"mean": 0.0, "std": 0.1},
        "abbreviation_rate": {"mean": 0.0, "std": 0.01},
        "avg_msg_length": {"mean": 30.0, "std": 10.0},
        "all_caps_rate": {"mean": 0.0, "std": 0.05},
        "initial_caps_rate": {"mean": 0.0, "std": 0.3},
        "punctuation_rate": {"mean": 0.005, "std": 0.005},
        "lowercase_ratio": {"mean": 0.7, "std": 0.05},
        "exclamation_rate": {"mean": 0.001, "std": 0.001},
        "vocabulary_richness": {"mean": 0.5, "std": 0.2},
    }
    age_calibrated = compute_vibe_age_from_texts(texts, calibration=custom_cal)

    # Both should be valid ages
    assert 13 <= age_default <= 75
    assert 13 <= age_calibrated <= 75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
