import argparse
import sys
from pathlib import Path
from pprint import pprint

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from services.precompute_service import PrecomputeService


def parse_csv_values(raw_value):
    if not raw_value:
        return None

    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    return values or None


def parse_window_sizes(raw_value):
    values = parse_csv_values(raw_value)

    if not values:
        return None

    return tuple(int(value) for value in values)


def main():
    parser = argparse.ArgumentParser(
        description="Precompute factor windows so Generate can read from cache."
    )
    parser.add_argument(
        "--symbols",
        default="AAPL,NVDA,MSFT,AMZN,GOOGL,GOOG,META,AVGO,TSLA,BRK.B",
        help="Comma-separated stock symbols to warm. Default: AAPL,NVDA,MSFT,AMZN,GOOGL,GOOG,META,AVGO,TSLA,BRK.B",
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
    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        precompute_service = PrecomputeService(app.config)
        results = precompute_service.warm_symbols(
            symbols=parse_csv_values(args.symbols),
            timeframes=parse_csv_values(args.timeframes),
            window_sizes=parse_window_sizes(args.window_sizes),
        )
        pprint(results)


if __name__ == "__main__":
    main()
