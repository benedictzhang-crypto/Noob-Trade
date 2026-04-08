import argparse
import sqlite3
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
TARGET_TIMEFRAME = "daily"
TARGET_WINDOW_SIZE = 30

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build full daily_indicators and pattern_windows cache rows "
            "from the existing daily_prices table."
        )
    )
    parser.add_argument(
        "--symbols",
        help="Comma-separated symbol list to limit the rebuild scope. Defaults to all active symbols in the DB.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even when a symbol already appears complete for daily indicators and daily 30-bar windows.",
    )
    return parser.parse_args()


def _integrity_check(database_path):
    with sqlite3.connect(database_path) as connection:
        result = connection.execute("PRAGMA integrity_check;").fetchone()
        return result[0] if result else "unknown"


def _table_count(database_path, table_name):
    with sqlite3.connect(database_path) as connection:
        result = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return int(result[0]) if result else 0


def _selected_symbols(raw_symbols):
    if not raw_symbols:
        return None

    cleaned = []
    for symbol in raw_symbols.split(","):
        normalized = symbol.strip().upper()
        if normalized:
            cleaned.append(normalized)

    return cleaned or None


def main():
    args = _parse_args()

    from app import app
    from extensions import db
    from models.market_data import DailyIndicator, DailyPrice, PatternWindow, Symbol
    from services.persistence_service import PersistenceService

    requested_symbols = _selected_symbols(args.symbols)
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    database_path = None

    if database_uri.startswith("sqlite:///"):
        database_path = Path(database_uri.removeprefix("sqlite:///"))

    with app.app_context():
        persistence_service = PersistenceService()

        symbol_query = Symbol.query.filter(Symbol.is_active.is_(True)).order_by(Symbol.symbol.asc())
        if requested_symbols:
            symbol_query = symbol_query.filter(Symbol.symbol.in_(requested_symbols))

        symbols = symbol_query.all()
        if not symbols:
            raise RuntimeError("No active symbols found for the requested rebuild scope.")

        total_symbols = len(symbols)
        processed = 0
        skipped = 0

        for index, symbol_record in enumerate(symbols, start=1):
            symbol_id = symbol_record.id
            symbol_code = symbol_record.symbol
            price_rows = DailyPrice.query.filter_by(symbol_id=symbol_id).order_by(DailyPrice.trade_date.asc()).all()
            price_count = len(price_rows)
            expected_window_count = max(price_count - TARGET_WINDOW_SIZE + 1, 0)

            indicator_count = DailyIndicator.query.filter_by(symbol_id=symbol_id).count()
            window_count = PatternWindow.query.filter_by(
                symbol_id=symbol_id,
                timeframe=TARGET_TIMEFRAME,
                window_size=TARGET_WINDOW_SIZE,
            ).count()

            if price_count == 0:
                print(
                    {
                        "status": "skipped-no-prices",
                        "index": index,
                        "total": total_symbols,
                        "symbol": symbol_code,
                    },
                    flush=True,
                )
                skipped += 1
                continue

            if (
                not args.force
                and indicator_count >= price_count
                and window_count >= expected_window_count
            ):
                print(
                    {
                        "status": "skipped-complete",
                        "index": index,
                        "total": total_symbols,
                        "symbol": symbol_code,
                        "priceRows": price_count,
                        "indicatorRows": indicator_count,
                        "patternWindows": window_count,
                        "expectedPatternWindows": expected_window_count,
                    },
                    flush=True,
                )
                skipped += 1
                continue

            prepared_candles = [
                {
                    "trade_date": row.trade_date,
                    "open": persistence_service._to_float(row.open),
                    "high": persistence_service._to_float(row.high),
                    "low": persistence_service._to_float(row.low),
                    "close": persistence_service._to_float(row.close),
                    "volume": persistence_service._to_float(row.volume or 0),
                }
                for row in price_rows
                if row.trade_date is not None
            ]

            try:
                persistence_service._upsert_daily_indicators(symbol_id, prepared_candles)
                built_windows = persistence_service._upsert_pattern_windows(
                    symbol_id,
                    prepared_candles,
                    TARGET_TIMEFRAME,
                    TARGET_WINDOW_SIZE,
                )
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
            finally:
                db.session.remove()

            refreshed_indicator_count = DailyIndicator.query.filter_by(symbol_id=symbol_id).count()
            refreshed_window_count = PatternWindow.query.filter_by(
                symbol_id=symbol_id,
                timeframe=TARGET_TIMEFRAME,
                window_size=TARGET_WINDOW_SIZE,
            ).count()

            processed += 1
            print(
                {
                    "status": "rebuilt",
                    "index": index,
                    "total": total_symbols,
                    "symbol": symbol_code,
                    "priceRows": price_count,
                    "indicatorRows": refreshed_indicator_count,
                    "patternWindows": refreshed_window_count,
                    "expectedPatternWindows": expected_window_count,
                    "windowsTouchedThisRun": built_windows,
                },
                flush=True,
            )

    if database_path is not None and database_path.exists():
        integrity = _integrity_check(database_path)
        summary = {
            "database": str(database_path),
            "rebuiltSymbols": processed,
            "skippedSymbols": skipped,
            "timeframe": TARGET_TIMEFRAME,
            "windowSize": TARGET_WINDOW_SIZE,
            "dailyPriceCount": _table_count(database_path, "daily_prices"),
            "dailyIndicatorCount": _table_count(database_path, "daily_indicators"),
            "patternWindowCount": _table_count(database_path, "pattern_windows"),
            "integrityCheck": integrity,
        }
        print(summary, flush=True)

        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {integrity}")


if __name__ == "__main__":
    main()
