# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram Wrapped is a "Spotify Wrapped"-style stats app for Telegram. Users authenticate via their phone number, and the backend runs a 4-phase data pipeline against the Telegram MTProto API to generate yearly messaging statistics, then displays them as a swipeable slide deck.

## Development Commands

### Backend (from `backend/`)
```bash
uvicorn app.main:app --reload   # Dev server on :8000
pytest                          # Run all tests
pytest tests/test_pipeline.py::test_name  # Run a single test
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

## Architecture

### Request Flow
1. Frontend `AuthSlide` → `POST /api/auth/send-code` → creates a `UserSession` with a Telethon client, sends OTP
2. `POST /api/auth/verify-code` → signs in the Telethon client, marks session authenticated
3. `POST /api/wrapped/start` → spawns an async `asyncio.Task` running `run_pipeline()`
4. `GET /api/wrapped/progress/{id}` (SSE) → streams `session.progress` updates until `phase=done`
5. `GET /api/wrapped/result/{id}` → returns `WrappedData` JSON

### Session System (`backend/app/telegram_service.py`)
Sessions are in-memory `UserSession` dataclasses keyed by UUID. Each session holds a `TelegramClient` whose SQLite session file lives in a `tempfile.mkdtemp()` directory. Sessions expire after 30 minutes (TTL enforced by a background cleanup task started at app startup). The cleanup loop skips sessions whose `pipeline_task` is still running.

### Data Pipeline (`backend/app/pipeline.py`)
Four phases run sequentially via `_run_phases()`:

- **Phase 1a** – Count lifetime message totals for all User/Chat dialogs (not Channels) using `get_messages(limit=0)`.
- **Phase 1b** – Refine to yearly counts using `SearchRequest` with `min_date`, then re-sort by yearly count.
- **Phase 2** – Fetch media type breakdowns per dialog using a single `GetSearchCountersRequest` (8 media types in one call).
- **Phase 3** – Adaptively sample messages month-by-month (200–1000 msgs/month per dialog scaled by chat size). Only the user's own messages (`from_id == my_id`) go into `all_sampled`; both sides go into `all_samples_unfiltered` (used for conversation-starter and streak detection).
- **Phase 4** – Compute statistics: top chats, hourly distribution, peak personality, streak, most-reacted message, text analysis (LLR + TF-IDF phrase extraction), sticker counts, and ML classification.

The pipeline tries **Takeout mode** first (3–5× faster, relaxed rate limits); falls back to standard API on failure. Rate limiting is handled by `_Throttle` (semaphore + shared flood-wait event).

Dialog weighting in Phase 4: `weight = (yearly_total × user_fraction) / sampled_count` where `user_fraction = sampled_count / total_sampled`. This estimates the user's real yearly message count per dialog without double-counting both parties.

### ML Pipeline (`backend/app/ml/`)
All classifiers are **purely deterministic** — no sklearn inference at runtime.

- **`features.py`** — Extracts a 23-feature vector from pipeline data. Media rates come from exact Phase 2 counts; text features (avg length, TTR, caps, emoji) come from weighted texts; metadata features (reply/forward/edit rates) come from sampled message objects.
- **`inference.py`** — 4-axis personality classifier (EVTM × INRD = 16 types). Each axis is a weighted sum of features, z-score normalized against population stats. The center/scale can be **self-calibrated** from per-dialog feature vectors (requires ≥5 dialogs); falls back to hardcoded defaults otherwise.
- **`vibe_age.py`** — Estimates "texting vibe age" (13–75) from 9 linguistic features using weighted z-scores against stats in `models/vibe_age_stats.json`.
- **`models/`** — JSON files: `personality_types.json` (display names/descriptions for 16 codes), `vibe_age_stats.json` (population mean/std), `background_bigrams.json` (Google n-gram corpus for TF-IDF distinctiveness), `archetype_meta.json`, `conversation_starter_meta.json`.

### Phrase Extraction (`pipeline._process_text_batch`)
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
`telegram_service.py` has a simple in-memory rate limiter for `POST /auth/send-code`: 10 requests per IP per 10-minute window (configurable via `RATE_LIMIT_SEND_CODE` env var).

## Key Constraints
- Telethon sessions are not persistent across server restarts (in-memory only).
- 2FA (cloud password) is not supported — users must temporarily disable it.
- Only `User` and `Chat` entity types are processed; `Channel` dialogs are skipped.
- The `top_chats` stat uses avatar images (base64) from the pipeline, while `top_stickers` downloads thumbnails via `_download_sticker_thumbnails`.
