import argparse
import json
import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def parse_csv_values(raw_value):
    return [item.strip().upper() for item in str(raw_value or "").split(",") if item.strip()]


def build_parser():
    parser = argparse.ArgumentParser(
        description="Incrementally sync recent symbol history into the configured database without rebuilding the full cache."
    )
    parser.add_argument(
        "--symbols",
        default="",
        help="Comma-separated symbols to sync. Default: use PRECOMPUTE_DEMO_SYMBOLS from config.",
    )
    parser.add_argument(
        "--timeframes",
        default="daily,5day,weekly,2week,monthly",
        help="Comma-separated timeframes to rebuild from the recent history window.",
    )
    parser.add_argument(
        "--window-sizes",
        default="20,30,60",
        help="Comma-separated window sizes to rebuild.",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=1400,
        help="How many recent daily bars to fetch per symbol for the incremental rebuild. Default: 1400.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    os.environ.setdefault("FLASK_DEBUG", "false")
    os.environ.setdefault("FLASK_USE_RELOADER", "false")

    from app import app
    from services.precompute_service import PrecomputeService

    symbols = parse_csv_values(args.symbols)
    timeframes = parse_csv_values(args.timeframes.lower())
    window_sizes = [int(item) for item in parse_csv_values(args.window_sizes)]

    with app.app_context():
        service = PrecomputeService(app.config)
        results = service.sync_symbols_incremental(
            symbols=symbols or None,
            timeframes=timeframes or None,
            window_sizes=window_sizes or None,
            history_limit=max(args.history_limit, 60),
        )

    print(json.dumps({"results": results}, indent=2, default=str))


if __name__ == "__main__":
    main()
