#!/usr/bin/env bash
# One-command local setup: installs everything, then runs backend + frontend.
#   ./dev.sh            # http://localhost:5173  (log in whenever you like)
#   ./dev.sh --demo     # also prints the no-login demo URL
# Ctrl-C stops both servers.
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd)

say() { printf '\033[1;34m▸ %s\033[0m\n' "$*"; }
die() { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# --- prerequisites -----------------------------------------------------------
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    PY=$c; break
  fi
done
[ -n "$PY" ] || die "Python 3.10+ is required (https://www.python.org/downloads/)"
command -v npm >/dev/null || die "Node.js 18+ is required (https://nodejs.org/)"

# --- credentials ---------------------------------------------------------------
ENV_FILE="$ROOT/backend/.env"
if [ ! -f "$ENV_FILE" ]; then
  cp "$ROOT/.env.example" "$ENV_FILE"
  say "Created backend/.env"
fi
if ! grep -qE '^TELEGRAM_API_ID=[0-9]+' "$ENV_FILE" || ! grep -qE '^TELEGRAM_API_HASH=[0-9a-f]{32}' "$ENV_FILE"; then
  echo
  echo "  Telegram API credentials are needed to log in (the demo works without them)."
  echo "  Get them at https://my.telegram.org → API development tools."
  echo "  Press Enter to skip for now."
  read -r -p "  API ID: " API_ID || true
  if [ -n "${API_ID:-}" ]; then
    read -r -p "  API hash: " API_HASH || true
    tmp=$(mktemp)
    grep -vE '^TELEGRAM_API_(ID|HASH)=' "$ENV_FILE" > "$tmp"
    { echo "TELEGRAM_API_ID=$API_ID"; echo "TELEGRAM_API_HASH=$API_HASH"; cat "$tmp"; } > "$ENV_FILE"
    rm -f "$tmp"
    say "Saved credentials to backend/.env (git-ignored)"
  fi
fi

# --- dependencies ----------------------------------------------------------------
if [ ! -x "$ROOT/backend/.venv/bin/python" ]; then
  say "Creating Python virtualenv"
  "$PY" -m venv "$ROOT/backend/.venv"
fi
VPY="$ROOT/backend/.venv/bin/python"
if [ ! -f "$ROOT/backend/.venv/.deps" ] || [ "$ROOT/backend/requirements.txt" -nt "$ROOT/backend/.venv/.deps" ]; then
  say "Installing backend dependencies"
  "$VPY" -m pip install -q --upgrade pip
  "$VPY" -m pip install -q -r "$ROOT/backend/requirements.txt"
  touch "$ROOT/backend/.venv/.deps"
fi
if [ ! -d "$ROOT/frontend/node_modules" ] || [ "$ROOT/frontend/package-lock.json" -nt "$ROOT/frontend/node_modules" ]; then
  say "Installing frontend dependencies"
  (cd "$ROOT/frontend" && npm install --silent)
  touch "$ROOT/frontend/node_modules"
fi

# --- run ----------------------------------------------------------------------------
pids=()
cleanup() { trap - INT TERM EXIT; kill "${pids[@]}" 2>/dev/null || true; wait 2>/dev/null || true; }
trap cleanup INT TERM EXIT

say "Starting backend on :8000"
(cd "$ROOT/backend" && exec "$VPY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
pids+=($!)

for _ in $(seq 1 60); do
  curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1 || die "Backend did not start — see the log above"

say "Starting frontend on :5173"
(cd "$ROOT/frontend" && exec npx vite --port 5173 --strictPort --clearScreen false) &
pids+=($!)

for _ in $(seq 1 60); do
  curl -sf http://localhost:5173/ >/dev/null 2>&1 && break
  sleep 0.5
done
echo
printf '\033[1;32m✓ Ready\033[0m\n'
echo "  Your Wrapped:  http://localhost:5173        (log in whenever you're ready)"
echo "  Demo deck:     http://localhost:5173/?demo=1"
echo "  Ctrl-C to stop."
echo
wait
