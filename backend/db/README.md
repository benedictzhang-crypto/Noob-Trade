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
