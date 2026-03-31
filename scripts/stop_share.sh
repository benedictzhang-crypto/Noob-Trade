#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_DIR="$PROJECT_ROOT/.runtime"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
TUNNEL_PID_FILE="$RUNTIME_DIR/tunnel.pid"

stop_from_file() {
  local pid_file="$1"

  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file" 2>/dev/null || true)"

    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi

    rm -f "$pid_file"
  fi
}

stop_from_file "$BACKEND_PID_FILE"
stop_from_file "$TUNNEL_PID_FILE"

echo "Noob Trade share stopped."
