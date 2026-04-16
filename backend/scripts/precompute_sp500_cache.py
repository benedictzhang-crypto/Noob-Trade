import argparse
import json
import sys
from pathlib import Path
import re
import time

import requests
from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from extensions import db
from services.precompute_service import PrecomputeService

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
DEFAULT_PROGRESS_PATH = BACKEND_DIR / ".runtime" / "sp500-precompute-progress.json"
DEFAULT_HISTORY_LIMIT = 2519
NO_PRICE_MARKERS = (
    "No price data returned from market API.",
    "No market data returned",
)


def fetch_sp500_symbols():
    response = requests.get(
        WIKI_URL,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    response.raise_for_status()
    html = response.text

    start = html.find('id="constituents"')
    if start == -1:
        raise ValueError("Could not locate the S&P 500 constituents table in the Wikipedia page.")

    segment = html[start:].split("</table>", 1)[0]
    symbols = re.findall(
        r'<tr>\s*<td><a rel="nofollow" class="external text" href="[^"]+">([A-Z.]+)</a>',
        segment,
    )

    if len(symbols) < 500:
        raise ValueError(f"Unexpected S&P 500 symbol count parsed from Wikipedia: {len(symbols)}")

    return symbols


def load_progress(progress_path):
    if not progress_path.exists():
        return {"completed": [], "failed": {}, "excluded": {}}

    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    progress.setdefault("completed", [])
    progress.setdefault("failed", {})
    progress.setdefault("excluded", {})
    return progress


def save_progress(progress_path, progress):
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(json.dumps(progress, indent=2, sort_keys=True), encoding="utf-8")


def parse_csv(raw_value):
    if not raw_value:
        return None
    return [item.strip().upper() for item in raw_value.split(",") if item.strip()]


def load_existing_symbols():
    rows = db.session.execute(text("select symbol from symbols")).all()
    return {row[0].upper() for row in rows if row and row[0]}


def should_exclude_symbol(error_message):
    normalized = (error_message or "").strip()
    return any(marker in normalized for marker in NO_PRICE_MARKERS)


def main():
    parser = argparse.ArgumentParser(
        description="Warm the local cache for the current S&P 500 constituent universe."
    )
    parser.add_argument(
        "--symbols",
        default="",
        help="Optional comma-separated override list. If omitted, fetch the current S&P 500 list from Wikipedia.",
    )
    parser.add_argument(
        "--timeframes",
        default="daily,5day,weekly,2week,monthly",
        help="Comma-separated timeframes to precompute.",
    )
    parser.add_argument(
        "--window-sizes",
        default="20,30,60",
        help="Comma-separated window sizes to precompute.",
    )
    parser.add_argument(
        "--progress-file",
        default=str(DEFAULT_PROGRESS_PATH),
        help="Where to store resumable progress state.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional cap for how many symbols to process this run.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.5,
        help="Optional pause between symbols to reduce API pressure.",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=DEFAULT_HISTORY_LIMIT,
        help="Daily history length to request per symbol before persisting indicators and pattern windows.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip symbols that already exist in the target database.",
    )
    args = parser.parse_args()

    progress_path = Path(args.progress_file).expanduser().resolve()
    progress = load_progress(progress_path)

    requested_symbols = parse_csv(args.symbols)
    symbols = requested_symbols or fetch_sp500_symbols()
    if args.limit and args.limit > 0:
        symbols = symbols[:args.limit]

    app = create_app()

    with app.app_context():
        completed = set(progress.get("completed", []))
        excluded = dict(progress.get("excluded", {}))
        failed = dict(progress.get("failed", {}))

        # This run treats any prior failure as an excluded symbol so we do not
        # keep rescanning the same failing symbols forever.
        if failed:
            for symbol, reason in failed.items():
                excluded.setdefault(symbol, reason)
            failed = {}

        existing_symbols = load_existing_symbols() if args.skip_existing else set()
        skipped_existing = existing_symbols.intersection(symbols)
        completed.update(skipped_existing)
        remaining_symbols = [
            symbol for symbol in symbols if symbol not in completed and symbol not in excluded
        ]

        print(
            {
                "total_symbols": len(symbols),
                "already_completed": len((set(progress.get("completed", []))).intersection(symbols)),
                "already_excluded": len(set(excluded).intersection(symbols)),
                "already_in_database": len(skipped_existing),
                "remaining": len(remaining_symbols),
                "progress_file": str(progress_path),
            }
        )

        precompute_service = PrecomputeService(app.config)

        for index, symbol in enumerate(remaining_symbols, start=1):
            try:
                results = precompute_service.warm_symbols(
                    symbols=[symbol],
                    timeframes=[item.strip() for item in args.timeframes.split(",") if item.strip()],
                    window_sizes=tuple(int(item.strip()) for item in args.window_sizes.split(",") if item.strip()),
                    history_limit=max(args.history_limit, 60),
                )
                completed.add(symbol)
                failed.pop(symbol, None)
                excluded.pop(symbol, None)
                print({"status": "ok", "symbol": symbol, "index": index, "result": results[0] if results else None})
            except Exception as error:
                error_message = str(error)
                excluded[symbol] = error_message
                failed.pop(symbol, None)
                print(
                    {
                        "status": "excluded",
                        "symbol": symbol,
                        "index": index,
                        "reason": error_message,
                    }
                )

            save_progress(
                progress_path,
                {
                    "completed": sorted(completed),
                    "excluded": excluded,
                    "failed": failed,
                },
            )

            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()
