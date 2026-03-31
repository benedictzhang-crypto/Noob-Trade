import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2] / 'backend'
sys.path.insert(0, str(BACKEND_ROOT))

from app import create_app  # noqa: E402

app = create_app()
port = int(os.getenv('PORT', '5000'))
app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
