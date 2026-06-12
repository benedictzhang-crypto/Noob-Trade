#!/usr/bin/env python3
"""Sync the independent crypto pattern-store SQLite into Render Postgres.

Only `crypto_pattern_*` tables are created/replaced. This keeps the fast
NoobTrade crypto Generate/Scan inventory separate from stock history tables and
from the larger crypto minute/interval history tables.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path

import psycopg


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_PATH = BACKEND_DIR / "data" / "noobtrade_crypto_pattern_store.sqlite"

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite-path", default=str(DEFAULT_SQLITE_PATH))
    parser.add_argument("--database-url", default=os.getenv("CRYPTO_PATTERN_STORE_DATABASE_URL") or os.getenv("DATABASE_URL") or "")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate only crypto_pattern_* tables before import.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect SQLite counts without writing Postgres.")
    return parser.parse_args()


def normalize_database_url(raw_url: str) -> str:
    normalized = str(raw_url or "").strip()
    if normalized.startswith("postgresql+psycopg://"):
        return "postgresql://" + normalized.removeprefix("postgresql+psycopg://")
    return normalized


def mask_database_url(raw_url: str) -> str:
    normalized = str(raw_url or "")
    if "@" not in normalized:
        return normalized
    prefix, suffix = normalized.rsplit("@", 1)
    scheme = prefix.split("://", 1)[0] if "://" in prefix else "postgresql"
    return f"{scheme}://<redacted>@{suffix}"


def sqlite_connection(path: Path):
    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def decode_json(raw_value, fallback):
    if raw_value is None:
        return fallback
    if isinstance(raw_value, (dict, list)):
        return raw_value
    try:
        return json.loads(raw_value)
    except (TypeError, ValueError):
        return fallback


def inspect_sqlite(source):
    return {
        "assets": source.execute("SELECT COUNT(*) FROM assets").fetchone()[0],
        "candles": source.execute("SELECT COUNT(*) FROM candles").fetchone()[0],
        "windows": source.execute("SELECT COUNT(*) FROM pattern_windows").fetchone()[0],
        "manifest": source.execute("SELECT COUNT(*) FROM build_manifest").fetchone()[0],
    }


def create_schema(connection, reset=False):
    if reset:
        connection.execute("DROP TABLE IF EXISTS crypto_pattern_windows")
        connection.execute("DROP TABLE IF EXISTS crypto_pattern_candles")
        connection.execute("DROP TABLE IF EXISTS crypto_pattern_assets")
        connection.execute("DROP TABLE IF EXISTS crypto_pattern_build_manifest")

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS crypto_pattern_assets (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            market_cap_rank INTEGER,
            market_cap DOUBLE PRECISION,
            venue_symbol TEXT NOT NULL,
            exchange TEXT NOT NULL DEFAULT 'okx',
            sample_target INTEGER NOT NULL,
            candle_count INTEGER NOT NULL DEFAULT 0,
            first_bar_time DATE,
            last_bar_time DATE,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS crypto_pattern_candles (
            symbol TEXT NOT NULL,
            interval TEXT NOT NULL,
            bar_time DATE NOT NULL,
            open DOUBLE PRECISION NOT NULL,
            high DOUBLE PRECISION NOT NULL,
            low DOUBLE PRECISION NOT NULL,
            close DOUBLE PRECISION NOT NULL,
            volume DOUBLE PRECISION,
            PRIMARY KEY(symbol, interval, bar_time)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS crypto_pattern_windows (
            id BIGINT PRIMARY KEY,
            symbol TEXT NOT NULL,
            interval TEXT NOT NULL,
            window_size INTEGER NOT NULL,
            start_time DATE NOT NULL,
            end_time DATE NOT NULL,
            regime TEXT NOT NULL,
            diversity_key TEXT NOT NULL,
            return_pct DOUBLE PRECISION,
            avg_return DOUBLE PRECISION,
            max_drawdown DOUBLE PRECISION,
            volatility DOUBLE PRECISION,
            probability_score DOUBLE PRECISION,
            ma_slope DOUBLE PRECISION,
            ema_slope DOUBLE PRECISION,
            macd_trend DOUBLE PRECISION,
            rsi_avg DOUBLE PRECISION,
            rsi_min DOUBLE PRECISION,
            rsi_max DOUBLE PRECISION,
            volume_change_ratio DOUBLE PRECISION,
            future_max_up_pct DOUBLE PRECISION,
            future_max_down_pct DOUBLE PRECISION,
            feature_vector_json JSONB NOT NULL,
            candles_json JSONB NOT NULL,
            future_stats_json JSONB NOT NULL,
            source TEXT NOT NULL DEFAULT 'okx_daily',
            UNIQUE(symbol, interval, window_size, end_time)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS crypto_pattern_build_manifest (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS ix_crypto_pattern_windows_lookup ON crypto_pattern_windows(interval, window_size, regime)")
    connection.execute("CREATE INDEX IF NOT EXISTS ix_crypto_pattern_windows_symbol_time ON crypto_pattern_windows(symbol, interval, end_time)")
    connection.execute("CREATE INDEX IF NOT EXISTS ix_crypto_pattern_windows_diversity ON crypto_pattern_windows(interval, window_size, diversity_key)")
    connection.execute("CREATE INDEX IF NOT EXISTS ix_crypto_pattern_candles_symbol_time ON crypto_pattern_candles(symbol, interval, bar_time)")


def copy_rows(connection, table_name, columns, rows):
    column_list = ", ".join(columns)
    copy_sql = f"COPY {table_name} ({column_list}) FROM STDIN"
    count = 0
    with connection.cursor() as cursor:
        with cursor.copy(copy_sql) as copy:
            for row in rows:
                copy.write_row(row)
                count += 1
    return count


def sync_assets(source, target):
    columns = (
        "symbol", "name", "category", "market_cap_rank", "market_cap", "venue_symbol", "exchange",
        "sample_target", "candle_count", "first_bar_time", "last_bar_time", "updated_at",
    )
    rows = (tuple(row) for row in source.execute(f"SELECT {', '.join(columns)} FROM assets ORDER BY symbol"))
    return copy_rows(target, "crypto_pattern_assets", columns, rows)


def sync_candles(source, target):
    columns = ("symbol", "interval", "bar_time", "open", "high", "low", "close", "volume")
    rows = (tuple(row) for row in source.execute(f"SELECT {', '.join(columns)} FROM candles ORDER BY symbol, interval, bar_time"))
    return copy_rows(target, "crypto_pattern_candles", columns, rows)


def sync_windows(source, target):
    columns = (
        "id", "symbol", "interval", "window_size", "start_time", "end_time", "regime", "diversity_key",
        "return_pct", "avg_return", "max_drawdown", "volatility", "probability_score",
        "ma_slope", "ema_slope", "macd_trend", "rsi_avg", "rsi_min", "rsi_max", "volume_change_ratio",
        "future_max_up_pct", "future_max_down_pct", "feature_vector_json", "candles_json",
        "future_stats_json", "source",
    )

    def rows():
        for row in source.execute(f"SELECT {', '.join(columns)} FROM pattern_windows ORDER BY id"):
            values = list(row)
            values[22] = json.dumps(decode_json(values[22], {}), separators=(",", ":"))
            values[23] = json.dumps(decode_json(values[23], []), separators=(",", ":"))
            values[24] = json.dumps(decode_json(values[24], {}), separators=(",", ":"))
            yield tuple(values)

    return copy_rows(target, "crypto_pattern_windows", columns, rows())


def sync_manifest(source, target):
    rows = [tuple(row) for row in source.execute("SELECT key, value FROM build_manifest ORDER BY key")]
    rows.append(("storageTarget", "render-postgres:noobtrade-db:crypto_pattern_*"))
    return copy_rows(target, "crypto_pattern_build_manifest", ("key", "value"), rows)


def verify_target(target):
    return {
        "assets": target.execute("SELECT COUNT(*) FROM crypto_pattern_assets").fetchone()[0],
        "candles": target.execute("SELECT COUNT(*) FROM crypto_pattern_candles").fetchone()[0],
        "windows": target.execute("SELECT COUNT(*) FROM crypto_pattern_windows").fetchone()[0],
        "manifest": target.execute("SELECT COUNT(*) FROM crypto_pattern_build_manifest").fetchone()[0],
    }


def main():
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).expanduser()
    if not sqlite_path.exists():
        raise RuntimeError(f"SQLite pattern-store not found: {sqlite_path}")

    database_url = normalize_database_url(args.database_url)
    if not database_url.startswith("postgresql://"):
        raise RuntimeError("A PostgreSQL DATABASE_URL or CRYPTO_PATTERN_STORE_DATABASE_URL is required.")

    with sqlite_connection(sqlite_path) as source:
        source_counts = inspect_sqlite(source)
        print({"source": str(sqlite_path), "counts": source_counts})
        if args.dry_run:
            return

        with psycopg.connect(database_url) as target:
            with target.transaction():
                create_schema(target, reset=args.reset)
                imported = {
                    "assets": sync_assets(source, target),
                    "candles": sync_candles(source, target),
                    "windows": sync_windows(source, target),
                    "manifest": sync_manifest(source, target),
                }
                verified = verify_target(target)
        print({
            "target": mask_database_url(database_url),
            "imported": imported,
            "verified": verified,
            "tables": "crypto_pattern_*",
        })


if __name__ == "__main__":
    main()
