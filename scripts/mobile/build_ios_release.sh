#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "Preparing Noob Trade iOS shell..."
npm run mobile:prepare:ios

echo "Opening Xcode project..."
npx cap open ios
