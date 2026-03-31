#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"
python3 -m pip install -r launcher/requirements.txt
python3 launcher/scripts/generate_icons.py
python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --icon launcher/assets/noobtrade.icns \
  --name NoobTrade \
  launcher/app.py

echo ""
echo "macOS build complete."
echo "Open: dist/NoobTrade.app"
