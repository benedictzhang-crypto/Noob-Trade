import argparse
import csv
import hashlib
import json
import os
import sqlite3
from datetime import date
from pathlib import Path

import psycopg


BATCH_SIZE = 500


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sync one isolated strategy dataset from SQLite to PostgreSQL."
    )
    parser.add_argument("--strategy-key", required=True)
    parser.add_argument("--sqlite", required=True, type=Path)
    parser.add_argument("--universe-csv", type=Path)
    parser.add_argument("--symbols", default="")
    parser.add_argument("--dataset-name", default="")
    parser.add_argument("--source-label", default="")
    parser.add_argument("--local-cache", type=Path)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--price-start", default="2026-01-01")
    parser.add_argument("--recent-window-limit", type=int, default=5000)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def normalize_strategy_key(value):
    normalized = str(value or "").strip().lower()
    if not normalized or len(normalized) > 32:
        raise RuntimeError("strategy-key must contain 1-32 characters.")
    if not all(character.isalnum() or character in {"_", "-"} for character in normalized):
        raise RuntimeError("strategy-key may contain only letters, numbers, underscores, and hyphens.")
    return normalized


def load_universe(csv_path, raw_symbols):
    symbols = []
    if csv_path:
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            symbols.extend(
                str(row.get("symbol") or "").strip().upper()
                for row in csv.DictReader(handle)
            )
    symbols.extend(str(item or "").strip().upper() for item in raw_symbols.split(","))
    symbols = list(dict.fromkeys(symbol for symbol in symbols if symbol))
    if not symbols:
        raise RuntimeError("Provide --universe-csv or --symbols.")
    return symbols


def placeholders(values):
    return ",".join("?" for _ in values)


def read_source(sqlite_path, symbols, price_start, recent_window_limit):
    if not sqlite_path.exists():
        raise RuntimeError(f"SQLite source not found: {sqlite_path}")
    if recent_window_limit < 2000:
        raise RuntimeError("recent-window-limit must be at least 2000.")

    with sqlite3.connect(sqlite_path) as source:
        source.row_factory = sqlite3.Row
        symbol_rows = source.execute(
            f"""
            SELECT id, symbol, company_name, sector, industry, exchange, market_cap, is_active
            FROM symbols
            WHERE symbol IN ({placeholders(symbols)})
            ORDER BY symbol
            """,
            symbols,
        ).fetchall()
        source_ids = [row["id"] for row in symbol_rows]
        if len(symbol_rows) != len(symbols):
            found = {row["symbol"] for row in symbol_rows}
            missing = sorted(set(symbols) - found)
            raise RuntimeError(f"SQLite source is missing universe symbols: {', '.join(missing)}")

        daily_rows = source.execute(
            f"""
            SELECT symbol_id, trade_date, open, high, low, close, adjusted_close, volume, source
            FROM daily_prices
            WHERE symbol_id IN ({placeholders(source_ids)})
              AND trade_date >= ?
            ORDER BY trade_date, symbol_id
            """,
            (*source_ids, price_start),
        ).fetchall()
        window_rows = source.execute(
            f"""
            SELECT symbol_id, timeframe, window_size, start_date, end_date,
                   return_pct, avg_return, max_drawdown, volatility, probability_score,
                   ma_slope, ema_slope, macd_trend, rsi_avg, rsi_min, rsi_max,
                   volume_change_ratio, feature_vector
            FROM pattern_windows
            WHERE symbol_id IN ({placeholders(source_ids)})
              AND timeframe = 'daily'
              AND window_size = 30
              AND json_extract(feature_vector, '$.forwardExtremes.5d.maxUpPct') IS NOT NULL
              AND json_extract(feature_vector, '$.forwardExtremes.5d.maxDownPct') IS NOT NULL
            ORDER BY end_date DESC, id DESC
            LIMIT ?
            """,
            (*source_ids, recent_window_limit),
        ).fetchall()

    return symbol_rows, daily_rows, window_rows


def batched(rows):
    for index in range(0, len(rows), BATCH_SIZE):
        yield rows[index:index + BATCH_SIZE]


def ensure_strategy_tables(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS strategy_datasets (
            strategy_key varchar(32) PRIMARY KEY,
            dataset_name text NOT NULL,
            source_label text,
            universe_symbols jsonb NOT NULL,
            source_max_date date,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS strategy_daily_prices (
            id bigserial PRIMARY KEY,
            strategy_key varchar(32) NOT NULL,
            symbol_id bigint NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
            trade_date date NOT NULL,
            open numeric(18,6) NOT NULL,
            high numeric(18,6) NOT NULL,
            low numeric(18,6) NOT NULL,
            close numeric(18,6) NOT NULL,
            adjusted_close numeric(18,6),
            volume bigint,
            source varchar(64) NOT NULL DEFAULT 'strategy_cache',
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_strategy_daily_prices_lookup
                UNIQUE (strategy_key, symbol_id, trade_date)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS strategy_pattern_windows (
            id bigserial PRIMARY KEY,
            strategy_key varchar(32) NOT NULL,
            symbol_id bigint NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
            timeframe varchar(16) NOT NULL,
            window_size integer NOT NULL,
            start_date date NOT NULL,
            end_date date NOT NULL,
            return_pct numeric(12,6),
            avg_return numeric(12,6),
            max_drawdown numeric(12,6),
            volatility numeric(12,6),
            probability_score numeric(12,6),
            ma_slope numeric(12,6),
            ema_slope numeric(12,6),
            macd_trend numeric(12,6),
            rsi_avg numeric(12,6),
            rsi_min numeric(12,6),
            rsi_max numeric(12,6),
            volume_change_ratio numeric(12,6),
            feature_vector jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_strategy_pattern_windows_lookup
                UNIQUE (strategy_key, symbol_id, timeframe, window_size, end_date)
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_strategy_daily_prices_symbol_date
        ON strategy_daily_prices (strategy_key, symbol_id, trade_date DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_strategy_pattern_windows_recent
        ON strategy_pattern_windows (strategy_key, timeframe, window_size, end_date DESC, id DESC)
        """
    )


def write_local_cache(
    cache_path,
    strategy_key,
    dataset_name,
    source_label,
    symbol_rows,
    daily_rows,
    window_rows,
):
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(cache_path) as target:
        target.executescript(
            """
            PRAGMA journal_mode = DELETE;
            CREATE TABLE IF NOT EXISTS dataset_metadata (
                strategy_key TEXT PRIMARY KEY,
                dataset_name TEXT NOT NULL,
                source_label TEXT,
                universe_symbols TEXT NOT NULL,
                source_max_date TEXT,
                metadata TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL UNIQUE,
                company_name TEXT,
                sector TEXT,
                industry TEXT,
                exchange TEXT,
                market_cap NUMERIC,
                is_active INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS daily_prices (
                symbol_id INTEGER NOT NULL,
                trade_date TEXT NOT NULL,
                open NUMERIC NOT NULL,
                high NUMERIC NOT NULL,
                low NUMERIC NOT NULL,
                close NUMERIC NOT NULL,
                adjusted_close NUMERIC,
                volume INTEGER,
                source TEXT NOT NULL,
                PRIMARY KEY (symbol_id, trade_date)
            );
            CREATE TABLE IF NOT EXISTS pattern_windows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol_id INTEGER NOT NULL,
                timeframe TEXT NOT NULL,
                window_size INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                return_pct NUMERIC,
                avg_return NUMERIC,
                max_drawdown NUMERIC,
                volatility NUMERIC,
                probability_score NUMERIC,
                ma_slope NUMERIC,
                ema_slope NUMERIC,
                macd_trend NUMERIC,
                rsi_avg NUMERIC,
                rsi_min NUMERIC,
                rsi_max NUMERIC,
                volume_change_ratio NUMERIC,
                feature_vector TEXT,
                UNIQUE (symbol_id, timeframe, window_size, end_date)
            );
            CREATE INDEX IF NOT EXISTS ix_local_strategy_windows_recent
                ON pattern_windows (timeframe, window_size, end_date DESC, id DESC);
            DELETE FROM dataset_metadata;
            DELETE FROM daily_prices;
            DELETE FROM pattern_windows;
            DELETE FROM symbols;
            """
        )
        target.executemany(
            """
            INSERT INTO symbols (
                id, symbol, company_name, sector, industry, exchange, market_cap, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["id"], row["symbol"], row["company_name"], row["sector"],
                    row["industry"], row["exchange"], row["market_cap"], int(bool(row["is_active"])),
                )
                for row in symbol_rows
            ],
        )
        target.executemany(
            """
            INSERT INTO daily_prices (
                symbol_id, trade_date, open, high, low, close, adjusted_close, volume, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["symbol_id"], row["trade_date"], row["open"], row["high"],
                    row["low"], row["close"], row["adjusted_close"], row["volume"],
                    row["source"] or "strategy_cache",
                )
                for row in daily_rows
            ],
        )
        target.executemany(
            """
            INSERT INTO pattern_windows (
                symbol_id, timeframe, window_size, start_date, end_date,
                return_pct, avg_return, max_drawdown, volatility, probability_score,
                ma_slope, ema_slope, macd_trend, rsi_avg, rsi_min, rsi_max,
                volume_change_ratio, feature_vector
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["symbol_id"], row["timeframe"], row["window_size"], row["start_date"],
                    row["end_date"], row["return_pct"], row["avg_return"], row["max_drawdown"],
                    row["volatility"], row["probability_score"], row["ma_slope"],
                    row["ema_slope"], row["macd_trend"], row["rsi_avg"], row["rsi_min"],
                    row["rsi_max"], row["volume_change_ratio"], row["feature_vector"] or "{}",
                )
                for row in window_rows
            ],
        )
        universe_symbols = [row["symbol"] for row in symbol_rows]
        source_max_date = max((row["trade_date"] for row in daily_rows), default=None)
        metadata = {
            "symbolCount": len(symbol_rows),
            "dailyRowCount": len(daily_rows),
            "windowRowCount": len(window_rows),
            "timeframe": "daily",
            "windowSize": 30,
        }
        target.execute(
            """
            INSERT INTO dataset_metadata (
                strategy_key, dataset_name, source_label, universe_symbols, source_max_date, metadata
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                strategy_key,
                dataset_name,
                source_label,
                json.dumps(universe_symbols),
                source_max_date,
                json.dumps(metadata, sort_keys=True),
            ),
        )
    return hashlib.sha256(cache_path.read_bytes()).hexdigest()


def sync_cache(
    database_url,
    strategy_key,
    dataset_name,
    source_label,
    symbol_rows,
    daily_rows,
    window_rows,
):
    source_to_symbol = {row["id"]: row["symbol"] for row in symbol_rows}
    universe_symbols = [row["symbol"] for row in symbol_rows]
    universe_hash = hashlib.sha256(",".join(universe_symbols).encode("ascii")).hexdigest()
    source_max_date = max((row["trade_date"] for row in daily_rows), default=None)
    with psycopg.connect(database_url) as target:
        with target.cursor() as cursor:
            ensure_strategy_tables(cursor)
            cursor.executemany(
                """
                INSERT INTO symbols (
                    symbol, company_name, sector, industry, exchange, market_cap, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO NOTHING
                """,
                [
                    (
                        row["symbol"], row["company_name"], row["sector"], row["industry"],
                        row["exchange"], row["market_cap"], bool(row["is_active"]),
                    )
                    for row in symbol_rows
                ],
            )
            cursor.execute(
                "SELECT id, symbol FROM symbols WHERE symbol = ANY(%s)",
                (universe_symbols,),
            )
            target_ids = {symbol: symbol_id for symbol_id, symbol in cursor.fetchall()}

            daily_upserted = 0
            for batch in batched(daily_rows):
                cursor.executemany(
                    """
                    INSERT INTO strategy_daily_prices (
                        strategy_key, symbol_id, trade_date, open, high, low, close,
                        adjusted_close, volume, source
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (strategy_key, symbol_id, trade_date) DO UPDATE
                    SET open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        adjusted_close = EXCLUDED.adjusted_close,
                        volume = EXCLUDED.volume,
                        source = EXCLUDED.source
                    """,
                    [
                        (
                            strategy_key, target_ids[source_to_symbol[row["symbol_id"]]],
                            row["trade_date"], row["open"], row["high"], row["low"],
                            row["close"], row["adjusted_close"], row["volume"],
                            row["source"] or "strategy_cache",
                        )
                        for row in batch
                    ],
                )
                daily_upserted += max(0, cursor.rowcount)

            window_upserted = 0
            for batch in batched(window_rows):
                cursor.executemany(
                    """
                    INSERT INTO strategy_pattern_windows (
                        strategy_key, symbol_id, timeframe, window_size, start_date, end_date,
                        return_pct, avg_return, max_drawdown, volatility, probability_score,
                        ma_slope, ema_slope, macd_trend, rsi_avg, rsi_min, rsi_max,
                        volume_change_ratio, feature_vector
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
                    )
                    ON CONFLICT (strategy_key, symbol_id, timeframe, window_size, end_date)
                    DO UPDATE SET start_date = EXCLUDED.start_date,
                                  return_pct = EXCLUDED.return_pct,
                                  avg_return = EXCLUDED.avg_return,
                                  max_drawdown = EXCLUDED.max_drawdown,
                                  volatility = EXCLUDED.volatility,
                                  probability_score = EXCLUDED.probability_score,
                                  ma_slope = EXCLUDED.ma_slope,
                                  ema_slope = EXCLUDED.ema_slope,
                                  macd_trend = EXCLUDED.macd_trend,
                                  rsi_avg = EXCLUDED.rsi_avg,
                                  rsi_min = EXCLUDED.rsi_min,
                                  rsi_max = EXCLUDED.rsi_max,
                                  volume_change_ratio = EXCLUDED.volume_change_ratio,
                                  feature_vector = EXCLUDED.feature_vector
                    """,
                    [
                        (
                            strategy_key, target_ids[source_to_symbol[row["symbol_id"]]],
                            row["timeframe"], row["window_size"], row["start_date"], row["end_date"],
                            row["return_pct"], row["avg_return"], row["max_drawdown"],
                            row["volatility"], row["probability_score"], row["ma_slope"],
                            row["ema_slope"], row["macd_trend"], row["rsi_avg"],
                            row["rsi_min"], row["rsi_max"], row["volume_change_ratio"],
                            json.dumps(json.loads(row["feature_vector"] or "{}")),
                        )
                        for row in batch
                    ],
                )
                window_upserted += max(0, cursor.rowcount)

            metadata = {
                "universeHash": universe_hash,
                "symbolCount": len(universe_symbols),
                "dailyRowCount": len(daily_rows),
                "windowRowCount": len(window_rows),
                "timeframe": "daily",
                "windowSize": 30,
            }
            cursor.execute(
                """
                INSERT INTO strategy_datasets (
                    strategy_key, dataset_name, source_label, universe_symbols,
                    source_max_date, metadata
                ) VALUES (%s, %s, %s, %s::jsonb, %s, %s::jsonb)
                ON CONFLICT (strategy_key) DO UPDATE
                SET dataset_name = EXCLUDED.dataset_name,
                    source_label = EXCLUDED.source_label,
                    universe_symbols = EXCLUDED.universe_symbols,
                    source_max_date = EXCLUDED.source_max_date,
                    metadata = EXCLUDED.metadata,
                    updated_at = now()
                """,
                (
                    strategy_key,
                    dataset_name,
                    source_label,
                    json.dumps(universe_symbols),
                    source_max_date,
                    json.dumps(metadata),
                ),
            )

        return {
            "symbolsAvailable": len(target_ids),
            "dailyRowsUpserted": daily_upserted,
            "windowRowsUpserted": window_upserted,
            "universeHash": universe_hash,
        }


def main():
    args = parse_args()
    strategy_key = normalize_strategy_key(args.strategy_key)
    price_start = date.fromisoformat(args.price_start).isoformat()
    symbols = load_universe(args.universe_csv, args.symbols)
    symbol_rows, daily_rows, window_rows = read_source(
        args.sqlite,
        symbols,
        price_start,
        args.recent_window_limit,
    )
    preview = {
        "mode": "apply" if args.apply else "preview",
        "strategyKey": strategy_key,
        "symbols": len(symbol_rows),
        "dailyRows": len(daily_rows),
        "windowRows": len(window_rows),
        "priceStart": price_start,
        "sourceMaxDate": max((row["trade_date"] for row in daily_rows), default=None),
    }
    if not args.apply:
        print(json.dumps(preview, indent=2))
        return
    if not args.database_url:
        raise RuntimeError("DATABASE_URL or --database-url is required with --apply.")
    dataset_name = args.dataset_name or strategy_key.upper()
    if args.local_cache:
        preview["localCache"] = str(args.local_cache.resolve())
        preview["localCacheSha256"] = write_local_cache(
            args.local_cache.resolve(),
            strategy_key,
            dataset_name,
            args.source_label,
            symbol_rows,
            daily_rows,
            window_rows,
        )
    preview.update(
        sync_cache(
            args.database_url,
            strategy_key,
            dataset_name,
            args.source_label,
            symbol_rows,
            daily_rows,
            window_rows,
        )
    )
    print(json.dumps(preview, indent=2))


if __name__ == "__main__":
    main()
