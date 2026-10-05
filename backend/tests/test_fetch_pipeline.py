"""End-to-end tests of the fetch strategy and statistics against a fake
Telegram with known ground truth."""
from __future__ import annotations

import asyncio
import math
import random
from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest

from app import pipeline
from app.fetcher import HistoryMsg, DialogData, plan_fetch, select_candidate_dialogs
from app.stats import conversation_dynamics
from app.throttle import AdaptiveThrottle, BudgetExceeded
from tests.fake_telegram import FakeClient, basic_group, build_chat, megagroup, user

NOW = datetime.now(timezone.utc)
START = NOW - timedelta(days=365)


def _world(seed: int = 1, scale: int = 1) -> list:
    rng = random.Random(seed)
    s, e = START + timedelta(minutes=1), NOW - timedelta(minutes=1)
    chats = [
        build_chat(user(11, "Alice"), "Alice", s, e, 4200 * scale, 0.5, rng, first_id=1, sticker_every=40, photo_every=25),
        build_chat(user(12, "Bob"), "Bob", s, e, 900 * scale, 0.4, rng, first_id=1, photo_every=30),
        build_chat(megagroup(21, "Climbing Crew", START), "Climbing Crew", s, e, 8000 * scale, 0.05, rng, first_id=1),
        build_chat(basic_group(22, "Family", START), "Family", s, e, 600 * scale, 0.3, rng, first_id=1),
    ]
    for uid in range(30, 45):  # long tail of small chats
        chats.append(build_chat(user(uid, f"Friend {uid}"), f"Friend {uid}", s, e, rng.randint(3, 60), 0.5, rng))
    return chats


def _truth(chats: list) -> dict:
    out = [m for c in chats for m in c.messages if m.out and START <= m.date <= NOW]
    return {
        "grand_total": len(out),
        "hours": Counter(m.date.hour for m in out),
        "photos": sum(1 for m in out if m.photo is not None),
        "stickers": sum(1 for m in out if m.sticker is not None),
        "per_chat": {c.name: sum(1 for m in c.messages if m.out) for c in chats},
    }


@pytest.fixture(autouse=True)
def _fast_settings(monkeypatch):
    monkeypatch.setattr(pipeline, "STANDARD", dict(pipeline.STANDARD, initial_limit=8, max_limit=16))


def run(client, **kw):
    return asyncio.run(pipeline.run_pipeline(client, None, **kw))


# ---------------------------------------------------------------------------
def test_exact_mode_matches_ground_truth():
    chats = _world()
    truth = _truth(chats)
    client = FakeClient(chats)
    result = run(client)

    assert result["accuracy"]["mode"] == "exact"
    assert result["accuracy"]["coverage_pct"] == 100.0
    assert result["accuracy"]["total_exact"] is True
    assert result["grand_total"] == truth["grand_total"]
    assert result["media_totals"]["photos"] == truth["photos"]
    assert result["stickers_sent"] == truth["stickers"]
    assert result["hourly_distribution"] == {h: truth["hours"].get(h, 0) for h in range(24)}
    # Top chats are ranked by what the user sent and include both-sides totals
    names = [c["name"] for c in result["top_chats"]]
    expected = sorted(truth["per_chat"], key=truth["per_chat"].get, reverse=True)
    assert names[:4] == expected[:4]
    alice = next(c for c in result["top_chats"] if c["name"] == "Alice")
    assert alice["total"] == len(chats[0].messages)
    assert alice["sent"] == truth["per_chat"]["Alice"]
    assert 40 <= alice["sent_share"] <= 60
    assert alice["avatar"] is None  # fake users have no photo
    group = next(c for c in result["top_chats"] if c["name"] == "Climbing Crew")
    assert group["is_group"] is True
    assert result["top_stickers"] and result["top_stickers"][0]["image"].startswith("data:image/webp")
    assert sum(m["count"] for m in result["monthly_activity"]) == truth["grand_total"]
    assert result["busiest_day"]["count"] >= 1
    assert result["reply_speed"] is not None
    assert result["total_chats"] == len(chats)


def test_exact_mode_uses_few_api_calls():
    chats = _world(scale=5)
    truth = _truth(chats)
    client = FakeClient(chats)
    run(client)
    # Lower bound for *any* exact approach reading only the user's messages
    pages = sum(math.ceil(n / 100) for n in truth["per_chat"].values())
    both_sides_pages = sum(math.ceil(len(c.messages) / 100) for c in chats)
    # Reading is within ~15% of the theoretical minimum (+ the 12 total-count calls)
    assert client.calls["search"] <= pages * 1.15 + 12
    # Conversation sampling is a small fixed cost
    assert client.calls["history"] <= 48
    # ...and everything together is far below paging through both sides of every chat
    assert client.total_calls < both_sides_pages * 0.4


def test_estimated_mode_is_close_and_counts_stay_exact(monkeypatch):
    monkeypatch.setattr(pipeline, "STANDARD", dict(pipeline.STANDARD, page_budget=20))
    chats = _world(seed=3, scale=3)
    truth = _truth(chats)
    client = FakeClient(chats)
    result = run(client)

    assert result["accuracy"]["mode"] == "estimated"
    assert result["accuracy"]["coverage_pct"] < 100
    # Totals come from Telegram's exact counts, never from sampling
    assert result["grand_total"] == truth["grand_total"]
    # Weighted estimates of distributions stay close to the truth
    est_total = sum(result["hourly_distribution"].values())
    assert abs(est_total - truth["grand_total"]) / truth["grand_total"] < 0.03
    assert abs(result["media_totals"]["photos"] - truth["photos"]) / max(truth["photos"], 1) < 0.35


def test_flood_waits_are_absorbed():
    chats = _world(seed=5)
    truth = _truth(chats)
    client = FakeClient(chats, flood_every=40, flood_seconds=0)
    result = run(client)
    assert result["grand_total"] == truth["grand_total"]
    assert result["accuracy"]["mode"] == "exact"


def test_deadline_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(pipeline, "STANDARD", dict(pipeline.STANDARD, deadline=0))
    chats = _world(seed=7)
    truth = _truth(chats)
    result = run(FakeClient(chats))
    # Counting is essential and still exact; optional deep fetching was skipped
    assert result["grand_total"] == truth["grand_total"]
    assert result["accuracy"]["mode"] == "estimated"


def test_utc_offset_shifts_hours_with_minutes():
    chats = _world(seed=9)
    base = run(FakeClient(chats))
    shifted = run(FakeClient(chats), utc_offset_minutes=330)  # India, UTC+5:30
    assert sum(base["hourly_distribution"].values()) == sum(shifted["hourly_distribution"].values())
    assert base["hourly_distribution"] != shifted["hourly_distribution"]


# ---------------------------------------------------------------------------
def test_plan_fetch_exact_when_budget_allows():
    plan = plan_fetch([50, 5000, 250], [50, 0, 0], page_budget=100)
    assert plan.exact
    assert 0 not in plan.per_dialog  # already complete from the count call
    assert plan.per_dialog[1][1] is None  # unlimited pages


def test_plan_fetch_estimated_spreads_budget():
    plan = plan_fetch([100_000, 10_000, 500], [0, 0, 0], page_budget=100)
    assert not plan.exact
    pages = {i: w * p for i, (w, p) in plan.per_dialog.items()}
    assert pages[0] > pages[1] >= pages[2] >= 2
    assert all(w <= 52 for w, _ in plan.per_dialog.values())


def test_select_candidates_includes_supergroups_excludes_noise():
    from types import SimpleNamespace
    from telethon.tl.types import Channel

    recent = SimpleNamespace(date=NOW)
    def d(entity):
        return SimpleNamespace(entity=entity, message=recent, name="x", id=entity.id)

    dialogs = [
        d(user(1, "Human")),
        d(user(2, "Bot", bot=True)),
        d(user(3, "Me", is_self=True)),
        d(user(777000, "Telegram")),
        d(megagroup(4, "Supergroup", START)),
        d(basic_group(5, "Basic", START)),
        d(Channel(id=6, title="News", access_hash=1, date=START, photo=None, broadcast=True)),
    ]
    picked = {x.entity.id for x in select_candidate_dialogs(dialogs, START)}
    assert picked == {1, 4, 5}


def test_conversation_starts_ignore_batch_boundaries():
    t = NOW
    d = DialogData(name="A", is_group=False, is_private=True)
    d.history_batches = [
        # batch starts with the other person's message: NOT a conversation start
        [HistoryMsg(t, False), HistoryMsg(t + timedelta(minutes=2), True)],
        # gap of 5h inside a batch: user starts a new conversation
        [HistoryMsg(t, False), HistoryMsg(t + timedelta(hours=5), True), HistoryMsg(t + timedelta(hours=5, minutes=1), False)],
    ]
    user_starts, other_starts, delays = conversation_dynamics([d])
    assert (user_starts, other_starts) == (1, 0)
    assert delays["A"] == [120.0]


# ---------------------------------------------------------------------------
def test_throttle_grows_and_halves_on_flood():
    from telethon import errors

    async def scenario():
        thr = AdaptiveThrottle(initial_limit=4, max_limit=8, grow_every=2)
        async def ok():
            return 1
        for _ in range(10):
            await thr.run(ok)
        grown = thr.limit
        state = {"n": 0}
        async def flaky():
            state["n"] += 1
            if state["n"] == 1:
                raise errors.FloodWaitError(request=None, capture=0)
            return 2
        assert await thr.run(flaky) == 2
        return grown, thr.limit, thr.flood_waits

    grown, after, floods = asyncio.run(scenario())
    assert grown == 8
    assert after == 4
    assert floods == 1


def test_throttle_optional_work_respects_budget():
    from telethon import errors

    async def scenario():
        thr = AdaptiveThrottle(max_wait=5)  # explicit cap
        async def long_flood():
            raise errors.FloodWaitError(request=None, capture=60)
        with pytest.raises(errors.FloodWaitError):
            await thr.run(long_flood, retries=0)
        async def ok():
            return 1
        with pytest.raises(BudgetExceeded):
            await thr.run(ok)  # optional: refuses to wait 60s
        thr.set_deadline(0)
        thr._resume_at = 0
        with pytest.raises(BudgetExceeded):
            await thr.run(ok)
        return await thr.run(ok, essential=True)

    assert asyncio.run(scenario()) == 1


def test_same_named_chats_do_not_merge():
    rng = random.Random(2)
    s, e = START + timedelta(minutes=1), NOW - timedelta(minutes=1)
    chats = [
        build_chat(user(51, "Alex"), "Alex", s, e, 300, 0.5, rng),
        build_chat(user(52, "Alex"), "Alex", s, e, 200, 0.5, rng),
    ]
    result = run(FakeClient(chats))
    names = sorted(c["name"] for c in result["top_chats"])
    assert names == ["Alex", "Alex (2)"]


def test_slow_counting_still_leaves_time_to_read(monkeypatch):
    """Regression: the read deadline used to start before counting, so a slow
    count phase (rate limits) left no time to read -> "Estimated from 0%"."""
    # 19 chats / 8 parallel x 0.4 s latency: counting alone takes ~1.2 s > the 1 s budget
    monkeypatch.setattr(pipeline, "STANDARD", dict(pipeline.STANDARD, deadline=1, page_budget=40))
    chats = _world(seed=11, scale=3)
    truth = _truth(chats)
    result = run(FakeClient(chats, latency=0.4))
    acc = result["accuracy"]
    assert result["grand_total"] == truth["grand_total"]
    assert acc["coverage_pct"] >= 5, acc
    # Distributions must reflect the whole account, not just the small chats
    est = sum(result["hourly_distribution"].values())
    assert abs(est - truth["grand_total"]) / truth["grand_total"] < 0.1


def test_ignored_from_filter_is_detected_and_corrected():
    """If Telegram ignores from_id (e.g. in private chats), other people's
    messages must not be counted as the user's."""
    chats = _world(seed=13)
    truth = _truth(chats)
    result = run(FakeClient(chats, ignore_from_id_in_private=True))
    err = abs(result["grand_total"] - truth["grand_total"]) / truth["grand_total"]
    assert err < 0.1, (result["grand_total"], truth["grand_total"])
    alice = next(c for c in result["top_chats"] if c["name"] == "Alice")
    assert abs(alice["sent"] - truth["per_chat"]["Alice"]) / truth["per_chat"]["Alice"] < 0.15
    assert result["accuracy"]["mode"] == "estimated"
    assert result["accuracy"]["total_exact"] is False


def test_ignored_filter_with_tight_budget_extrapolates(monkeypatch):
    monkeypatch.setattr(pipeline, "STANDARD", dict(pipeline.STANDARD, page_budget=15))
    chats = _world(seed=17, scale=3)
    truth = _truth(chats)
    result = run(FakeClient(chats, ignore_from_id_in_private=True))
    err = abs(result["grand_total"] - truth["grand_total"]) / truth["grand_total"]
    assert err < 0.12, (result["grand_total"], truth["grand_total"])
    assert result["accuracy"]["mode"] == "estimated"


def test_long_flood_wait_inside_budget_keeps_reading():
    from telethon import errors

    async def scenario():
        thr = AdaptiveThrottle()
        thr.set_deadline(60)
        thr._on_flood(0.3)  # a pause well inside the deadline: optional calls wait, not abort
        async def ok():
            return 1
        return await thr.run(ok)

    assert asyncio.run(scenario()) == 1
