import os
import sqlite3
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
SEED_HISTORY_LIMIT = 700
SEED_TIMEFRAMES = ("daily",)
SEED_WINDOW_SIZES = (30,)

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
    {
        "symbol": "V",
        "company_name": "Visa Inc.",
        "sector": "Financial Services",
        "industry": "Credit Services",
        "exchange": "NYSE",
    },
    {
        "symbol": "XOM",
        "company_name": "Exxon Mobil Corporation",
        "sector": "Energy",
        "industry": "Oil & Gas Integrated",
        "exchange": "NYSE",
    },
    {
        "symbol": "UNH",
        "company_name": "UnitedHealth Group Incorporated",
        "sector": "Healthcare",
        "industry": "Healthcare Plans",
        "exchange": "NYSE",
    },
    {
        "symbol": "MA",
        "company_name": "Mastercard Incorporated",
        "sector": "Financial Services",
        "industry": "Credit Services",
        "exchange": "NYSE",
    },
    {
        "symbol": "COST",
        "company_name": "Costco Wholesale Corporation",
        "sector": "Consumer Defensive",
        "industry": "Discount Stores",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "JNJ",
        "company_name": "Johnson & Johnson",
        "sector": "Healthcare",
        "industry": "Drug Manufacturers - General",
        "exchange": "NYSE",
    },
    {
        "symbol": "HD",
        "company_name": "The Home Depot, Inc.",
        "sector": "Consumer Cyclical",
        "industry": "Home Improvement Retail",
        "exchange": "NYSE",
    },
    {
        "symbol": "ORCL",
        "company_name": "Oracle Corporation",
        "sector": "Technology",
        "industry": "Software - Infrastructure",
        "exchange": "NYSE",
    },
    {
        "symbol": "PG",
        "company_name": "The Procter & Gamble Company",
        "sector": "Consumer Defensive",
        "industry": "Household & Personal Products",
        "exchange": "NYSE",
    },
    {
        "symbol": "MRK",
        "company_name": "Merck & Co., Inc.",
        "sector": "Healthcare",
        "industry": "Drug Manufacturers - General",
        "exchange": "NYSE",
    },
    {
        "symbol": "NFLX",
        "company_name": "Netflix, Inc.",
        "sector": "Communication Services",
        "industry": "Entertainment",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "ABBV",
        "company_name": "AbbVie Inc.",
        "sector": "Healthcare",
        "industry": "Drug Manufacturers - General",
        "exchange": "NYSE",
    },
    {
        "symbol": "BAC",
        "company_name": "Bank of America Corporation",
        "sector": "Financial Services",
        "industry": "Banks - Diversified",
        "exchange": "NYSE",
    },
    {
        "symbol": "KO",
        "company_name": "The Coca-Cola Company",
        "sector": "Consumer Defensive",
        "industry": "Beverages - Non-Alcoholic",
        "exchange": "NYSE",
    },
    {
        "symbol": "AMD",
        "company_name": "Advanced Micro Devices, Inc.",
        "sector": "Technology",
        "industry": "Semiconductors",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "CVX",
        "company_name": "Chevron Corporation",
        "sector": "Energy",
        "industry": "Oil & Gas Integrated",
        "exchange": "NYSE",
    },
    {
        "symbol": "PEP",
        "company_name": "PepsiCo, Inc.",
        "sector": "Consumer Defensive",
        "industry": "Beverages - Non-Alcoholic",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "CRM",
        "company_name": "Salesforce, Inc.",
        "sector": "Technology",
        "industry": "Software - Application",
        "exchange": "NYSE",
    },
    {
        "symbol": "WMT",
        "company_name": "Walmart Inc.",
        "sector": "Consumer Defensive",
        "industry": "Discount Stores",
        "exchange": "NYSE",
    },
    {
        "symbol": "TMO",
        "company_name": "Thermo Fisher Scientific Inc.",
        "sector": "Healthcare",
        "industry": "Diagnostics & Research",
        "exchange": "NYSE",
    },
    {
        "symbol": "ACN",
        "company_name": "Accenture plc",
        "sector": "Technology",
        "industry": "Information Technology Services",
        "exchange": "NYSE",
    },
    {
        "symbol": "CSCO",
        "company_name": "Cisco Systems, Inc.",
        "sector": "Technology",
        "industry": "Communication Equipment",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "MCD",
        "company_name": "McDonald's Corporation",
        "sector": "Consumer Cyclical",
        "industry": "Restaurants",
        "exchange": "NYSE",
    },
    {
        "symbol": "ABT",
        "company_name": "Abbott Laboratories",
        "sector": "Healthcare",
        "industry": "Medical Devices",
        "exchange": "NYSE",
    },
    {
        "symbol": "IBM",
        "company_name": "International Business Machines Corporation",
        "sector": "Technology",
        "industry": "Information Technology Services",
        "exchange": "NYSE",
    },
    {
        "symbol": "GE",
        "company_name": "GE Aerospace",
        "sector": "Industrials",
        "industry": "Aerospace & Defense",
        "exchange": "NYSE",
    },
    {
        "symbol": "LIN",
        "company_name": "Linde plc",
        "sector": "Basic Materials",
        "industry": "Specialty Chemicals",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "DIS",
        "company_name": "The Walt Disney Company",
        "sector": "Communication Services",
        "industry": "Entertainment",
        "exchange": "NYSE",
    },
    {
        "symbol": "ADBE",
        "company_name": "Adobe Inc.",
        "sector": "Technology",
        "industry": "Software - Infrastructure",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "NOW",
        "company_name": "ServiceNow, Inc.",
        "sector": "Technology",
        "industry": "Software - Application",
        "exchange": "NYSE",
    },
    {
        "symbol": "INTU",
        "company_name": "Intuit Inc.",
        "sector": "Technology",
        "industry": "Software - Application",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "QCOM",
        "company_name": "QUALCOMM Incorporated",
        "sector": "Technology",
        "industry": "Semiconductors",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "CAT",
        "company_name": "Caterpillar Inc.",
        "sector": "Industrials",
        "industry": "Farm & Heavy Construction Machinery",
        "exchange": "NYSE",
    },
    {
        "symbol": "TXN",
        "company_name": "Texas Instruments Incorporated",
        "sector": "Technology",
        "industry": "Semiconductors",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "AXP",
        "company_name": "American Express Company",
        "sector": "Financial Services",
        "industry": "Credit Services",
        "exchange": "NYSE",
    },
    {
        "symbol": "AMAT",
        "company_name": "Applied Materials, Inc.",
        "sector": "Technology",
        "industry": "Semiconductor Equipment & Materials",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "BKNG",
        "company_name": "Booking Holdings Inc.",
        "sector": "Consumer Cyclical",
        "industry": "Travel Services",
        "exchange": "NASDAQ",
    },
    {
        "symbol": "UBER",
        "company_name": "Uber Technologies, Inc.",
        "sector": "Technology",
        "industry": "Software - Application",
        "exchange": "NYSE",
    },
    {
        "symbol": "GS",
        "company_name": "The Goldman Sachs Group, Inc.",
        "sector": "Financial Services",
        "industry": "Capital Markets",
        "exchange": "NYSE",
    },
    {
        "symbol": "SPY",
        "company_name": "SPDR S&P 500 ETF Trust",
        "sector": "Financial Services",
        "industry": "Exchange Traded Fund",
        "exchange": "NYSEARCA",
    },
]


def _integrity_check(database_path):
    with sqlite3.connect(database_path) as connection:
        result = connection.execute("PRAGMA integrity_check;").fetchone()
        return result[0] if result else "unknown"


def _table_count(database_path, table_name):
    with sqlite3.connect(database_path) as connection:
        result = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return int(result[0]) if result else 0


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
    from services.precompute_service import PrecomputeService

    with app.app_context():
        precompute_service = PrecomputeService(app.config)
        timeframes = SEED_TIMEFRAMES
        window_sizes = SEED_WINDOW_SIZES

        for index, item in enumerate(SEED_SYMBOLS, start=1):
            response_data = precompute_service._build_cache_seed_response(item["symbol"], window_sizes)
            daily_history = list(response_data.get("chartData", {}).get("history", {}).get("daily", []))
            if daily_history:
                response_data["chartData"]["history"]["daily"] = daily_history[-SEED_HISTORY_LIMIT:]
            response_data["stock"].update(
                {
                    "symbol": item["symbol"],
                    "companyName": item["company_name"],
                    "sector": item["sector"],
                    "industry": item["industry"],
                    "exchange": item["exchange"],
                }
            )
            precompute_service.persistence_service.warm_symbol_cache(
                response_data,
                timeframes=timeframes,
                window_sizes=window_sizes,
            )
            print(
                {
                    "status": "seeded",
                    "index": index,
                    "total": len(SEED_SYMBOLS),
                    "symbol": item["symbol"],
                    "history_limit": SEED_HISTORY_LIMIT,
                },
                flush=True,
            )

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
            "symbol_count": len(SEED_SYMBOLS),
            "history_limit": SEED_HISTORY_LIMIT,
            "timeframes": list(SEED_TIMEFRAMES),
            "window_sizes": list(SEED_WINDOW_SIZES),
            "daily_price_count": _table_count(final_db_path, "daily_prices"),
            "daily_indicator_count": _table_count(final_db_path, "daily_indicators"),
            "pattern_window_count": _table_count(final_db_path, "pattern_windows"),
            "symbols": [item["symbol"] for item in SEED_SYMBOLS],
            "integrity_check": _integrity_check(final_db_path),
        }
    )


if __name__ == "__main__":
    main()
