#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$PROJECT_ROOT/.runtime"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
TUNNEL_LOG="$RUNTIME_DIR/tunnel.log"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
TUNNEL_PID_FILE="$RUNTIME_DIR/tunnel.pid"
SHARE_URL_FILE="$RUNTIME_DIR/share-url.txt"
LOCAL_PORT="${LOCAL_PORT:-5010}"

mkdir -p "$RUNTIME_DIR"

cd "$PROJECT_ROOT/frontend"
npm run build

if [[ -f "$BACKEND_PID_FILE" ]]; then
  OLD_BACKEND_PID="$(cat "$BACKEND_PID_FILE" 2>/dev/null || true)"
  if [[ -n "${OLD_BACKEND_PID}" ]] && kill -0 "$OLD_BACKEND_PID" 2>/dev/null; then
    kill "$OLD_BACKEND_PID" 2>/dev/null || true
  fi
fi

if [[ -f "$TUNNEL_PID_FILE" ]]; then
  OLD_TUNNEL_PID="$(cat "$TUNNEL_PID_FILE" 2>/dev/null || true)"
  if [[ -n "${OLD_TUNNEL_PID}" ]] && kill -0 "$OLD_TUNNEL_PID" 2>/dev/null; then
    kill "$OLD_TUNNEL_PID" 2>/dev/null || true
  fi
fi

cd "$PROJECT_ROOT/backend"
export FLASK_DEBUG=false
export HOST=127.0.0.1
export PORT="$LOCAL_PORT"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://localhost/stock_pattern_project}"
export MARKET_DATA_TOKEN="${MARKET_DATA_TOKEN:-fintech_20260601_a114e3df2bac0dc7eb432a1369b69113}"
export USE_MOCK_FALLBACK="${USE_MOCK_FALLBACK:-false}"

nohup python app.py > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$BACKEND_PID_FILE"

sleep 3

if ! curl -sS "http://127.0.0.1:${LOCAL_PORT}/api/health" >/dev/null; then
  echo "Backend failed to start. Check $BACKEND_LOG"
  exit 1
fi

cd "$PROJECT_ROOT"
nohup ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:127.0.0.1:${LOCAL_PORT} nokey@localhost.run > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!
echo "$TUNNEL_PID" > "$TUNNEL_PID_FILE"

echo ""
echo "Starting tunnel..."
ATTEMPTS=0
SHARE_URL=""

while [[ $ATTEMPTS -lt 30 ]]; do
  if grep -Eo 'https://[a-zA-Z0-9.-]+\.lhr\.life|https://[a-zA-Z0-9.-]+\.localhost\.run' "$TUNNEL_LOG" >/dev/null 2>&1; then
    SHARE_URL="$(grep -Eo 'https://[a-zA-Z0-9.-]+\.lhr\.life|https://[a-zA-Z0-9.-]+\.localhost\.run' "$TUNNEL_LOG" | head -n 1)"
    break
  fi

  if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
    echo "Tunnel process exited early. Check $TUNNEL_LOG"
    exit 1
  fi

  sleep 1
  ATTEMPTS=$((ATTEMPTS + 1))
done

if [[ -z "$SHARE_URL" ]]; then
  echo "Could not detect a public URL yet. Check $TUNNEL_LOG"
  exit 1
fi

printf '%s\n' "$SHARE_URL" > "$SHARE_URL_FILE"

echo ""
echo "Noob Trade is live:"
echo "$SHARE_URL"
echo ""
echo "Local server: http://127.0.0.1:${LOCAL_PORT}"
echo "Backend log: $BACKEND_LOG"
echo "Tunnel log: $TUNNEL_LOG"
echo "Share URL file: $SHARE_URL_FILE"
