import os
import sqlite3
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


SEED_SYMBOLS = [
    {
        "symbol": "AAPL",
        "company_name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "NVDA",
        "company_name": "NVIDIA Corporation",
        "sector": "Technology",
        "industry": "Semiconductors",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "MSFT",
        "company_name": "Microsoft Corporation",
        "sector": "Technology",
        "industry": "Software",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "AMZN",
        "company_name": "Amazon.com, Inc.",
        "sector": "Consumer Discretionary",
        "industry": "Internet Retail",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "GOOGL",
        "company_name": "Alphabet Inc. Class A",
        "sector": "Communication Services",
        "industry": "Internet Content & Information",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "GOOG",
        "company_name": "Alphabet Inc. Class C",
        "sector": "Communication Services",
        "industry": "Internet Content & Information",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "META",
        "company_name": "Meta Platforms, Inc.",
        "sector": "Communication Services",
        "industry": "Internet Content & Information",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "AVGO",
        "company_name": "Broadcom Inc.",
        "sector": "Technology",
        "industry": "Semiconductors",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "TSLA",
        "company_name": "Tesla, Inc.",
        "sector": "Consumer Discretionary",
        "industry": "Auto Manufacturers",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "BRK.B",
        "company_name": "Berkshire Hathaway Inc. Class B",
        "sector": "Financial Services",
        "industry": "Insurance - Diversified",
        "exchange": "NYSE",
    },
]


def _integrity_check(database_path):
    with sqlite3.connect(database_path) as connection:
        result = connection.execute("PRAGMA integrity_check;").fetchone()
        return result[0] if result else "unknown"


def main():
    final_db_path = BACKEND_DIR / "noobtrade_local.db"
    temp_db_path = BACKEND_DIR / "noobtrade_local.seed-build.db"

    if temp_db_path.exists():
        temp_db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"
    os.environ["MARKET_DATA_TOKEN"] = ""
    os.environ["USE_MOCK_FALLBACK"] = "true"
    os.environ["FLASK_DEBUG"] = "false"

    from app import app
    from extensions import db
    from models.market_data import Symbol

    with app.app_context():
        for item in SEED_SYMBOLS:
            record = Symbol.query.filter_by(symbol=item["symbol"]).first()

            if record is None:
                record = Symbol(symbol=item["symbol"])
                db.session.add(record)

            record.company_name = item["company_name"]
            record.sector = item["sector"]
            record.industry = item["industry"]
            record.exchange = item["exchange"]
            record.is_active = True

        db.session.commit()
        db.session.remove()
        db.engine.dispose()

    integrity_result = _integrity_check(temp_db_path)
    if integrity_result != "ok":
        raise RuntimeError(f"Seed database failed integrity check: {integrity_result}")

    temp_db_path.replace(final_db_path)
    print(
        {
            "database": str(final_db_path),
            "symbols": [item["symbol"] for item in SEED_SYMBOLS],
            "integrity_check": _integrity_check(final_db_path),
        }
    )


if __name__ == "__main__":
    main()
