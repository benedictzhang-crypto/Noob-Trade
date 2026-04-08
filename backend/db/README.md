# Database Setup

This project uses PostgreSQL for:

- symbol metadata
- daily OHLCV prices
- daily technical indicators
- pattern-matching feature windows
- analysis runs and historical matches
- watchlists and paper trades

## Initialize the schema

```bash
createdb stock_pattern_project
psql -d stock_pattern_project -f backend/db/init.sql
```

## Environment variable

Set the database URL before starting Flask:

```bash
export DATABASE_URL="postgresql+psycopg://localhost/stock_pattern_project"
```

If your PostgreSQL user or host is different, adjust the URL accordingly.

## Recommended next step

After the schema is created, connect Flask with SQLAlchemy or psycopg and build:

1. a daily ingestion job for `daily_prices`
2. an indicator calculation job for `daily_indicators`
3. a feature-window job for `pattern_windows`

## Rebuild the tracked SQLite seed database

If you need a clean local seed database for the repo, run:

```bash
python backend/scripts/build_seed_db.py
```

That script creates a fresh SQLite database at `backend/noobtrade_local.db`,
initializes the schema, seeds the tracked top-50 symbol metadata, and
verifies the file with `PRAGMA integrity_check`.

## Build the full local daily cache from seeded prices

The tracked SQLite file intentionally keeps only a lighter cache footprint in
git. If you want a full local daily cache for Generate or backtesting, build it
from the existing `daily_prices` rows:

```bash
python backend/scripts/build_full_daily_cache.py
```

What this script does:

- reads the existing `daily_prices` rows already stored in `backend/noobtrade_local.db`
- rebuilds `daily_indicators` for the same daily date coverage
- rebuilds `pattern_windows` for `timeframe=daily` and `window_size=30`
- skips symbols that already appear complete, so it is safe to rerun
- prints per-symbol progress plus final row counts
- runs `PRAGMA integrity_check` at the end

Useful options:

```bash
python backend/scripts/build_full_daily_cache.py --symbols AAPL,NVDA
python backend/scripts/build_full_daily_cache.py --force
```

Use `--symbols` to resume or test a smaller scope. Use `--force` if you want to
recompute the cache even when a symbol already looks complete.
