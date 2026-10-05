# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram Wrapped is a "Spotify Wrapped"-style stats app for Telegram. Users authenticate via their phone number, and the backend runs a 4-phase data pipeline against the Telegram MTProto API to generate yearly messaging statistics, then displays them as a swipeable slide deck.

## Development Commands

### Backend (from `backend/`)
```bash
uvicorn app.main:app --reload   # Dev server on :8000
pip install -r requirements-dev.txt
pytest                          # Run all tests
pytest tests/test_pipeline.py::test_name  # Run a single test
python -m scripts.live_check --verify 3   # Run against your own account
python -m app.bot               # Standalone bot poller (scaled deployments)
```

### Frontend (from `frontend/`)
```bash
npm run dev     # Dev server on :5173, proxies /api → :8000
npm run build   # tsc -b && vite build
npm run lint    # ESLint
```

### Environment
Copy `.env.example` to `backend/.env` and fill in:
- `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` — from https://my.telegram.org (required)
- `APP_ENV=development` (controls CORS and HSTS)
- `CORS_ORIGIN` — used in production only
- `REDIS_URL` + `SESSION_ENCRYPTION_KEY` — required for multi-instance deployments (see `docker-compose.yml`)
- Pacing/limits: `TG_*`, `MAX_CONCURRENT_PIPELINES`, `STATS_WORKERS`, `SESSION_TTL`, `RESULT_TTL` (documented in `.env.example`)

## Architecture

### Request Flow
1. Frontend `AuthSlide` → `POST /api/auth/send-code` → creates a `UserSession` with a Telethon client, sends OTP
2. `POST /api/auth/verify-code` → signs in the Telethon client, marks session authenticated
3. `POST /api/wrapped/start` → queues `run_pipeline()` on the instance's `JobScheduler`
4. `GET /api/wrapped/progress/{id}` (SSE) → streams progress from the store until `phase=done|error`; `GET /api/wrapped/status/{id}` returns it once (polling fallback / resume)
5. `GET /api/wrapped/result/{id}` → returns `WrappedData` JSON (from the store, valid for `RESULT_TTL`)

### Session System (`backend/app/telegram_service.py`, `backend/app/store.py`)
Sessions are Telethon `StringSession`s, Fernet-encrypted and stored in a shared `Store` (`MemoryStore` by default, `RedisStore` when `REDIS_URL` is set — then any API instance/worker can serve any request). Keys: `session:{id}` (phone, code hash, encrypted secret), `progress:{id}`, `result:{id}`, `botchat:{id}`, rate-limit counters. Connected clients are cached per process and disconnected when idle. After a successful pipeline the Telegram authorization is revoked (`log_out`) and the secret deleted; unused logins are revoked by `_cleanup_loop` after `SESSION_TTL` (expiry claimed atomically via a sorted set, skipping sessions whose progress is still live). Results live for `RESULT_TTL`.

### Jobs (`backend/app/jobs.py`)
`JobScheduler` caps concurrent pipelines per instance (`MAX_CONCURRENT_PIPELINES`); waiting users get `phase=queued` with `queue_position`. `routers/wrapped.py` heartbeats progress every 20 s; progress older than 180 s in an active phase is reported as an error (worker died).

### Data Pipeline (`backend/app/pipeline.py`, `fetcher.py`, `stats.py`, `throttle.py`)
- **Dialog selection** (`fetcher.select_candidate_dialogs`): private chats with humans, basic groups and **supergroups** (`Channel.megagroup`). Broadcast channels, bots, Saved Messages and service chats (777000) are skipped.
- **Count**: one `messages.search(from_id=InputPeerSelf, min_date, max_date)` per dialog → exact number of messages the user sent + newest 100.
- **Read** (`plan_fetch`): if all remaining pages fit `TG_PAGE_BUDGET` → exact mode (every sent message, split into time windows for parallelism). Otherwise estimated mode: pages proportional to chat size over ≤52 time windows; each window's exact count gives per-message `weight = window_count / fetched`.
- **Conversations**: both-sides totals (`limit=1` search) for the top 12 chats; 6 contiguous `get_messages(offset_date=…)` windows for the top 8 private chats → reply speed and conversation starts (only transitions *inside* a batch count).
- **Stats** (`stats.compute_stats`, pure, runs in a thread or process pool via `STATS_WORKERS`): grand total = Σ exact sent counts; hourly/weekday/monthly distributions from weighted records (local time with minute-precision `utc_offset_minutes`); busiest day, active days and streaks from exactly-fetched windows; media/sticker totals from the user's messages; phrases via `text_analysis._process_text_batch` (subsampled above 25k texts); ML on records (per-chat features capped at 3k records).
- **Throttle** (`AdaptiveThrottle`): AIMD concurrency, shared pause on `FLOOD_WAIT`, retries, and a soft deadline (`TG_FETCH_DEADLINE`) after which optional requests raise `BudgetExceeded` and the pipeline degrades to estimates instead of stalling. Counting calls are `essential=True`.
- **Takeout** is used only if Telegram grants it immediately (`TAKEOUT_MAX_WAIT`, default 0); searches fall back to the normal client if the server rejects them inside takeout.
- Every result includes `accuracy` (mode, coverage %, messages analysed, API calls, duration).
- `tests/fake_telegram.py` emulates `messages.search`/`get_messages` with ground truth; `tests/test_fetch_pipeline.py` checks exactness, call counts, estimates, flood waits and deadlines. `scripts/live_check.py` runs against a real account.

### ML Pipeline (`backend/app/ml/`)
All classifiers are **purely deterministic** — no sklearn inference at runtime.

- **`features.py`** — Extracts a 23-feature vector from pipeline data. Media rates come from exact Phase 2 counts; text features (avg length, TTR, caps, emoji) come from weighted texts; metadata features (reply/forward/edit rates) come from sampled message objects.
- **`inference.py`** — 4-axis personality classifier (EVTM × INRD = 16 types). Each axis is a weighted sum of features, z-score normalized against population stats. The center/scale can be **self-calibrated** from per-dialog feature vectors (requires ≥5 dialogs); falls back to hardcoded defaults otherwise.
- **`vibe_age.py`** — Estimates "texting vibe age" (13–75) from 9 linguistic features using weighted z-scores against stats in `models/vibe_age_stats.json`.
- **`models/`** — JSON files: `personality_types.json` (display names/descriptions for 16 codes), `vibe_age_stats.json` (population mean/std), `background_bigrams.json` (Google n-gram corpus for TF-IDF distinctiveness), `archetype_meta.json`, `conversation_starter_meta.json`.

### Phrase Extraction (`text_analysis._process_text_batch`, re-exported from `pipeline`)
Uses **LLR (log-likelihood ratio) × TF-IDF distinctiveness × length bonus** to rank 2–5 word phrases. Background bigrams from `background_bigrams.json` dampen generic English phrases. Deduplication prefers longer phrases over sub-phrases.

### Frontend (`frontend/src/`)
- **`App.tsx`** — State machine: `auth → loading → viewing`
- **`components/LoadingScreen.tsx`** — Connects to SSE progress endpoint, transitions to viewing after `phase=done`
- **`components/WrappedViewer.tsx`** — 12-slide deck with swipe/tap navigation (Framer Motion). Tap right half = next, tap left half = prev.
- **`components/slides/`** — One component per stat slide
- **`hooks/useSSE.ts`** — `EventSource` wrapper that closes on `done` or `error` phase
- **`api/client.ts`** — All API calls; uses `/api` base (proxied by Vite to `:8000` in dev)
- **`api/types.ts`** — TypeScript types mirroring `backend/app/schemas.py`

### Rate Limiting
`check_send_code_rate` (store-backed, shared across instances) limits `POST /auth/send-code` to `RATE_LIMIT_SEND_CODE` (10) per IP and `RATE_LIMIT_SEND_CODE_PHONE` (3) per phone number per 10 minutes. Set `TRUST_PROXY=1` behind your own proxy to use `X-Forwarded-For`.

## Key Constraints
- Without `REDIS_URL`, sessions/results are in-memory and lost on restart.
- 2FA (cloud password) is not supported — users must temporarily disable it.
- Broadcast channels are skipped; supergroups are included.
- `top_chats` (top 5) get base64 avatars and `top_stickers` base64 thumbnails via `pipeline._attach_images` (best effort, 15 s budget).
