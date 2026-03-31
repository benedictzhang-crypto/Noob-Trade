#!/bin/bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
BACKUP_DIR="${NOOBTRADE_DESKTOP_BACKUP_DIR:-/Users/benedict/Desktop/NoobTrade-backup}"

mkdir -p "$BACKUP_DIR"

rsync -a --delete \
  --exclude ".git/" \
  --exclude ".runtime/" \
  --exclude "node_modules/" \
  --exclude "frontend/node_modules/" \
  --exclude "frontend/dist/" \
  --exclude "frontend/playwright-report/" \
  --exclude "frontend/test-results/" \
  --exclude "build/" \
  --exclude "dist/" \
  --exclude "launcher/build/" \
  --exclude "launcher/dist/" \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  "$SOURCE_DIR/" "$BACKUP_DIR/"

echo "NoobTrade desktop backup synced to $BACKUP_DIR"
