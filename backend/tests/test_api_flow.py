"""API flow: start -> progress/status -> result, with a fake Telegram client
and both store backends (memory and Redis via fakeredis)."""
from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app import store as store_mod
from app import telegram_service as svc
from app.routers import wrapped as wrapped_router
from tests.fake_telegram import FakeClient, build_chat, user

NOW = datetime.now(timezone.utc)


def _fake_client() -> FakeClient:
    rng = random.Random(4)
    s, e = NOW - timedelta(days=360), NOW - timedelta(minutes=5)
    return FakeClient([
        build_chat(user(11, "Alice"), "Alice", s, e, 800, 0.5, rng),
        build_chat(user(12, "Bob"), "Bob", s, e, 300, 0.5, rng),
    ])


@pytest.fixture(params=["memory", "redis"])
async def backend(request, monkeypatch):
    if request.param == "redis":
        fakeredis = pytest.importorskip("fakeredis")
        st = store_mod.RedisStore.__new__(store_mod.RedisStore)
        st._r = fakeredis.FakeAsyncRedis(decode_responses=True)
        st._p = "test:"
    else:
        st = store_mod.MemoryStore()
    store_mod.set_store(st)
    monkeypatch.setenv("SESSION_ENCRYPTION_KEY", "")
    svc._fernet = None
    destroyed: list[str] = []

    async def fake_get_client(sid):
        return _fake_client()

    async def fake_destroy(sid, revoke=True):
        destroyed.append(sid)
        await st.delete(f"session:{sid}")

    monkeypatch.setattr(wrapped_router, "get_client", fake_get_client)
    monkeypatch.setattr(wrapped_router, "destroy_session", fake_destroy)
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, st, destroyed
    store_mod.set_store(None)


async def _authenticated_session(st, sid="sid-1"):
    await st.set_json(f"session:{sid}", {"phone": "+15550000000", "authenticated": True,
                                        "created_at": time.time(), "secret": "x"}, 600)
    return sid


async def test_full_flow(backend):
    client, st, destroyed = backend
    sid = await _authenticated_session(st)

    r = await client.post("/api/wrapped/start", json={"session_id": sid, "utc_offset_minutes": 480})
    assert r.status_code == 202

    r = await client.post("/api/wrapped/start", json={"session_id": sid})
    assert r.status_code == 409  # already running

    for _ in range(200):
        status = (await client.get(f"/api/wrapped/status/{sid}")).json()
        if status["phase"] in ("done", "error"):
            break
        await asyncio.sleep(0.05)
    assert status["phase"] == "done", status

    r = await client.get(f"/api/wrapped/result/{sid}")
    assert r.status_code == 200
    data = r.json()
    assert data["grand_total"] > 0
    assert data["accuracy"]["mode"] == "exact"
    assert destroyed == [sid]  # Telegram authorization revoked right after

    # SSE replays the final state and closes
    async with client.stream("GET", f"/api/wrapped/progress/{sid}") as resp:
        body = b"".join([chunk async for chunk in resp.aiter_bytes()])
    assert b'"phase": "done"' in body


async def test_unknown_session(backend):
    client, _, _ = backend
    assert (await client.post("/api/wrapped/start", json={"session_id": "nope"})).status_code == 404
    assert (await client.get("/api/wrapped/status/nope")).status_code == 404
    assert (await client.get("/api/wrapped/result/nope")).status_code == 404


async def test_unauthenticated_session_rejected(backend):
    client, st, _ = backend
    await st.set_json("session:s2", {"phone": "+1555", "authenticated": False}, 600)
    assert (await client.post("/api/wrapped/start", json={"session_id": "s2"})).status_code == 400


async def test_stale_progress_reported_as_error(backend):
    client, st, _ = backend
    await st.set_json("progress:s3", {"phase": "fetching", "message": "x", "updated_at": time.time() - 999}, 600)
    status = (await client.get("/api/wrapped/status/s3")).json()
    assert status["phase"] == "error"


async def test_rate_limit_per_phone(backend, monkeypatch):
    _, st, _ = backend
    monkeypatch.setattr(svc, "_RATE_LIMIT_PHONE", 2)
    results = [await svc.check_send_code_rate(f"10.0.0.{i}", "+15551234567") for i in range(4)]
    assert results == [True, True, False, False]


async def test_session_secret_is_encrypted_roundtrip(backend):
    sealed = svc._seal("1BVtsOK8Bu...secret")
    assert "secret" not in sealed
    assert svc._unseal(sealed) == "1BVtsOK8Bu...secret"


async def test_expiry_claim_is_exclusive(backend):
    _, st, _ = backend
    await st.schedule("a", time.time() - 1)
    await st.schedule("b", time.time() + 999)
    first, second = await asyncio.gather(st.claim_due(time.time()), st.claim_due(time.time()))
    assert sorted(first + second) == ["a"]


async def test_expiry_sweeper_spares_running_pipelines(backend, monkeypatch):
    _, st, _ = backend
    revoked: list[str] = []

    async def fake_destroy(sid, revoke=True):
        revoked.append(sid)

    monkeypatch.setattr(svc, "destroy_session", fake_destroy)
    now = time.time()
    await st.schedule("running", now - 1)
    await svc.set_progress("running", {"phase": "fetching", "message": "x"})
    await st.schedule("idle", now - 1)
    await svc._cleanup_once()
    assert revoked == ["idle"]
    assert await st.claim_due(now + 301) == ["running"]  # pushed back, not dropped


async def test_missing_credentials_give_clear_error(backend, monkeypatch):
    client, _, _ = backend
    monkeypatch.setenv("TELEGRAM_API_ID", "")
    monkeypatch.setenv("TELEGRAM_API_HASH", "")
    r = await client.post("/api/auth/send-code", json={"phone": "+15551234567"})
    assert r.status_code == 500
    assert "TELEGRAM_API_ID" in r.json()["detail"]
