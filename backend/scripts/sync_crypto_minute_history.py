#!/usr/bin/env python3
"""Build a separate minute-level crypto history store for NoobTrade.

The script uses Binance public spot kline archives. It intentionally writes
crypto data into dedicated tables (`crypto_*`) so it never mixes with the stock
history tables used by NoobTrade/ProTrade.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import time
import zipfile
from collections import deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from sqlalchemy import create_engine, text


BINANCE_ARCHIVE_BASE_URL = "https://data.binance.vision/data/spot"
DEFAULT_OUTPUT_DIR = Path("/Users/benedict/Desktop/Crypto History Data")
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT")
DEFAULT_INTERVAL = "1m"
DERIVED_INTERVAL_SECONDS = {
    "5m": 5 * 60,
    "15m": 15 * 60,
    "30m": 30 * 60,
    "1h": 60 * 60,
    "2h": 2 * 60 * 60,
    "4h": 4 * 60 * 60,
    "6h": 6 * 60 * 60,
    "12h": 12 * 60 * 60,
    "1d": 24 * 60 * 60,
    "5d": 5 * 24 * 60 * 60,
}
INSERT_BATCH_SIZE = 5000
DOWNLOAD_TIMEOUT = 45


def _normalize_database_url(raw_url: str) -> str:
    normalized = str(raw_url or "").strip()
    if normalized.startswith("postgres://"):
        return normalized.replace("postgres://", "postgresql+psycopg://", 1)
    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", "postgresql+psycopg://", 1)
    return normalized


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _add_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _month_range(start_date: date, end_date: date):
    cursor = _month_start(start_date)
    end_month = _month_start(end_date)
    while cursor <= end_month:
        yield cursor
        cursor = _add_month(cursor)


def _date_range(start_date: date, end_date: date):
    cursor = start_date
    while cursor <= end_date:
        yield cursor
        cursor += timedelta(days=1)


def _decimal_or_none(value):
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return f"{numeric:.10f}"


def _float_or_none(value):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _timestamp_to_datetime(raw_timestamp):
    timestamp = int(raw_timestamp)
    if timestamp > 10**17:
        seconds = timestamp / 1_000_000_000.0
    elif timestamp > 10**14:
        seconds = timestamp / 1_000_000.0
    else:
        seconds = timestamp / 1_000.0
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def _venue_to_asset(venue_symbol: str):
    venue = venue_symbol.upper()
    if venue.endswith("USDT"):
        return venue[:-4], "USDT"
    if venue.endswith("USD"):
        return venue[:-3], "USD"
    return venue, ""


class IndicatorState:
    def __init__(self):
        self.close_windows = {size: deque(maxlen=size) for size in (5, 10, 20, 60)}
        self.volume_windows = {size: deque(maxlen=size) for size in (5, 20)}
        self.high_9 = deque(maxlen=9)
        self.low_9 = deque(maxlen=9)
        self.prev_close = None
        self.ema_values = {}
        self.macd_signal = None
        self.delta_count = 0
        self.seed_gain = 0.0
        self.seed_loss = 0.0
        self.avg_gain = None
        self.avg_loss = None
        self.kdj_k = 50.0
        self.kdj_d = 50.0
        self.obv = 0.0

    @staticmethod
    def _average(values):
        return sum(values) / len(values) if values else None

    @staticmethod
    def _ema(previous, value, period):
        alpha = 2.0 / (period + 1.0)
        if previous is None:
            return value
        return (value * alpha) + (previous * (1.0 - alpha))

    def update(self, close, high, low, volume):
        for window in self.close_windows.values():
            window.append(close)
        for window in self.volume_windows.values():
            window.append(volume)
        self.high_9.append(high)
        self.low_9.append(low)

        for period in (5, 10, 12, 20, 26, 60):
            self.ema_values[period] = self._ema(self.ema_values.get(period), close, period)

        macd = None
        macd_signal = None
        macd_hist = None
        if self.ema_values.get(12) is not None and self.ema_values.get(26) is not None:
            macd = self.ema_values[12] - self.ema_values[26]
            self.macd_signal = self._ema(self.macd_signal, macd, 9)
            macd_signal = self.macd_signal
            macd_hist = macd - macd_signal if macd_signal is not None else None

        rsi_14 = None
        if self.prev_close is not None:
            delta = close - self.prev_close
            gain = max(delta, 0.0)
            loss = max(-delta, 0.0)
            if self.delta_count < 14:
                self.seed_gain += gain
                self.seed_loss += loss
                self.delta_count += 1
                if self.delta_count == 14:
                    self.avg_gain = self.seed_gain / 14.0
                    self.avg_loss = self.seed_loss / 14.0
            else:
                self.avg_gain = ((self.avg_gain or 0.0) * 13.0 + gain) / 14.0
                self.avg_loss = ((self.avg_loss or 0.0) * 13.0 + loss) / 14.0

            if self.avg_gain is not None and self.avg_loss is not None:
                if self.avg_loss == 0:
                    rsi_14 = 100.0
                else:
                    relative_strength = self.avg_gain / self.avg_loss
                    rsi_14 = 100.0 - (100.0 / (1.0 + relative_strength))

            if close > self.prev_close:
                self.obv += volume
            elif close < self.prev_close:
                self.obv -= volume

        boll_mid = None
        boll_upper = None
        boll_lower = None
        close_20 = self.close_windows[20]
        if len(close_20) >= 20:
            boll_mid = self._average(close_20)
            variance = sum((item - boll_mid) ** 2 for item in close_20) / len(close_20)
            stddev = math.sqrt(variance)
            boll_upper = boll_mid + (2.0 * stddev)
            boll_lower = boll_mid - (2.0 * stddev)

        kdj_k = None
        kdj_d = None
        kdj_j = None
        if len(self.high_9) >= 9 and len(self.low_9) >= 9:
            highest_high = max(self.high_9)
            lowest_low = min(self.low_9)
            rsv = 50.0 if highest_high == lowest_low else ((close - lowest_low) / (highest_high - lowest_low)) * 100.0
            self.kdj_k = (2.0 / 3.0) * self.kdj_k + (1.0 / 3.0) * rsv
            self.kdj_d = (2.0 / 3.0) * self.kdj_d + (1.0 / 3.0) * self.kdj_k
            kdj_k = self.kdj_k
            kdj_d = self.kdj_d
            kdj_j = (3.0 * kdj_k) - (2.0 * kdj_d)

        self.prev_close = close

        return {
            "ma_5": self._average(self.close_windows[5]) if len(self.close_windows[5]) >= 5 else None,
            "ma_10": self._average(self.close_windows[10]) if len(self.close_windows[10]) >= 10 else None,
            "ma_20": self._average(self.close_windows[20]) if len(self.close_windows[20]) >= 20 else None,
            "ma_60": self._average(self.close_windows[60]) if len(self.close_windows[60]) >= 60 else None,
            "ema_5": self.ema_values.get(5),
            "ema_10": self.ema_values.get(10),
            "ema_12": self.ema_values.get(12),
            "ema_20": self.ema_values.get(20),
            "ema_26": self.ema_values.get(26),
            "ema_60": self.ema_values.get(60),
            "macd": macd,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
            "boll_mid": boll_mid,
            "boll_upper": boll_upper,
            "boll_lower": boll_lower,
            "rsi_14": rsi_14,
            "kdj_k": kdj_k,
            "kdj_d": kdj_d,
            "kdj_j": kdj_j,
            "vol_ma_5": self._average(self.volume_windows[5]) if len(self.volume_windows[5]) >= 5 else None,
            "vol_ma_20": self._average(self.volume_windows[20]) if len(self.volume_windows[20]) >= 20 else None,
            "obv": self.obv,
            "oi": None,
        }


class BarAggregator:
    def __init__(self, interval: str, seconds: int):
        self.interval = interval
        self.seconds = seconds
        self.current_bucket = None
        self.current_bar = None

    def _bucket_start(self, bar_time):
        timestamp = int(bar_time.timestamp())
        bucket_timestamp = (timestamp // self.seconds) * self.seconds
        return datetime.fromtimestamp(bucket_timestamp, tz=timezone.utc)

    def add(self, bar):
        bucket_start = self._bucket_start(bar["bar_time"])
        completed_bar = None

        if self.current_bucket is None:
            self.current_bucket = bucket_start
            self.current_bar = self._new_bar(bucket_start, bar)
            return None

        if bucket_start != self.current_bucket:
            completed_bar = self.current_bar
            self.current_bucket = bucket_start
            self.current_bar = self._new_bar(bucket_start, bar)
            return completed_bar

        self.current_bar["high"] = max(self.current_bar["high"], bar["high"])
        self.current_bar["low"] = min(self.current_bar["low"], bar["low"])
        self.current_bar["close"] = bar["close"]
        self.current_bar["volume"] += bar["volume"]
        self.current_bar["quote_volume"] += bar["quote_volume"]
        self.current_bar["trade_count"] += bar["trade_count"]
        self.current_bar["taker_buy_base_volume"] += bar["taker_buy_base_volume"]
        self.current_bar["taker_buy_quote_volume"] += bar["taker_buy_quote_volume"]
        self.current_bar["source_file"] = bar["source_file"]
        return None

    def flush(self):
        completed_bar = self.current_bar
        self.current_bar = None
        self.current_bucket = None
        return completed_bar

    @staticmethod
    def _new_bar(bucket_start, bar):
        return {
            "bar_time": bucket_start,
            "open": bar["open"],
            "high": bar["high"],
            "low": bar["low"],
            "close": bar["close"],
            "volume": bar["volume"],
            "quote_volume": bar["quote_volume"],
            "trade_count": bar["trade_count"],
            "taker_buy_base_volume": bar["taker_buy_base_volume"],
            "taker_buy_quote_volume": bar["taker_buy_quote_volume"],
            "source_file": bar["source_file"],
        }


class CryptoHistoryStore:
    def __init__(self, database_url: str):
        self.database_url = _normalize_database_url(database_url)
        self.engine = create_engine(self.database_url, future=True)
        self.dialect = self.engine.dialect.name

    def create_schema(self):
        id_type = "BIGSERIAL PRIMARY KEY" if self.dialect == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        timestamp_type = "TIMESTAMPTZ" if self.dialect == "postgresql" else "DATETIME"
        numeric_type = "NUMERIC"
        now_expr = "CURRENT_TIMESTAMP"
        with self.engine.begin() as connection:
            connection.execute(text(f"""
                CREATE TABLE IF NOT EXISTS crypto_assets (
                    id {id_type},
                    symbol VARCHAR(16) NOT NULL UNIQUE,
                    base_asset VARCHAR(16) NOT NULL,
                    quote_asset VARCHAR(16) NOT NULL DEFAULT 'USDT',
                    venue_symbol VARCHAR(32) NOT NULL UNIQUE,
                    exchange VARCHAR(32) NOT NULL DEFAULT 'binance',
                    source VARCHAR(80) NOT NULL DEFAULT 'binance_public_klines',
                    first_bar_time {timestamp_type},
                    last_bar_time {timestamp_type},
                    row_count BIGINT NOT NULL DEFAULT 0,
                    created_at {timestamp_type} NOT NULL DEFAULT {now_expr},
                    updated_at {timestamp_type} NOT NULL DEFAULT {now_expr}
                )
            """))
            connection.execute(text(f"""
                CREATE TABLE IF NOT EXISTS crypto_minute_prices (
                    id {id_type},
                    asset_id BIGINT NOT NULL REFERENCES crypto_assets(id) ON DELETE CASCADE,
                    exchange VARCHAR(32) NOT NULL DEFAULT 'binance',
                    venue_symbol VARCHAR(32) NOT NULL,
                    bar_time {timestamp_type} NOT NULL,
                    open {numeric_type}(24, 10) NOT NULL,
                    high {numeric_type}(24, 10) NOT NULL,
                    low {numeric_type}(24, 10) NOT NULL,
                    close {numeric_type}(24, 10) NOT NULL,
                    volume {numeric_type}(28, 10),
                    quote_volume {numeric_type}(28, 10),
                    trade_count INTEGER,
                    taker_buy_base_volume {numeric_type}(28, 10),
                    taker_buy_quote_volume {numeric_type}(28, 10),
                    source_file VARCHAR(180) NOT NULL,
                    created_at {timestamp_type} NOT NULL DEFAULT {now_expr},
                    UNIQUE(asset_id, exchange, venue_symbol, bar_time)
                )
            """))
            connection.execute(text(f"""
                CREATE TABLE IF NOT EXISTS crypto_minute_indicators (
                    id {id_type},
                    asset_id BIGINT NOT NULL REFERENCES crypto_assets(id) ON DELETE CASCADE,
                    exchange VARCHAR(32) NOT NULL DEFAULT 'binance',
                    venue_symbol VARCHAR(32) NOT NULL,
                    bar_time {timestamp_type} NOT NULL,
                    ma_5 {numeric_type}(24, 10),
                    ma_10 {numeric_type}(24, 10),
                    ma_20 {numeric_type}(24, 10),
                    ma_60 {numeric_type}(24, 10),
                    ema_5 {numeric_type}(24, 10),
                    ema_10 {numeric_type}(24, 10),
                    ema_12 {numeric_type}(24, 10),
                    ema_20 {numeric_type}(24, 10),
                    ema_26 {numeric_type}(24, 10),
                    ema_60 {numeric_type}(24, 10),
                    macd {numeric_type}(24, 10),
                    macd_signal {numeric_type}(24, 10),
                    macd_hist {numeric_type}(24, 10),
                    boll_mid {numeric_type}(24, 10),
                    boll_upper {numeric_type}(24, 10),
                    boll_lower {numeric_type}(24, 10),
                    rsi_14 {numeric_type}(12, 6),
                    kdj_k {numeric_type}(12, 6),
                    kdj_d {numeric_type}(12, 6),
                    kdj_j {numeric_type}(12, 6),
                    vol_ma_5 {numeric_type}(28, 10),
                    vol_ma_20 {numeric_type}(28, 10),
                    obv {numeric_type}(32, 10),
                    oi {numeric_type}(28, 10),
                    created_at {timestamp_type} NOT NULL DEFAULT {now_expr},
                    UNIQUE(asset_id, exchange, venue_symbol, bar_time)
                )
            """))
            connection.execute(text(f"""
                CREATE TABLE IF NOT EXISTS crypto_interval_prices (
                    id {id_type},
                    asset_id BIGINT NOT NULL REFERENCES crypto_assets(id) ON DELETE CASCADE,
                    interval VARCHAR(16) NOT NULL,
                    exchange VARCHAR(32) NOT NULL DEFAULT 'binance',
                    venue_symbol VARCHAR(32) NOT NULL,
                    bar_time {timestamp_type} NOT NULL,
                    open {numeric_type}(24, 10) NOT NULL,
                    high {numeric_type}(24, 10) NOT NULL,
                    low {numeric_type}(24, 10) NOT NULL,
                    close {numeric_type}(24, 10) NOT NULL,
                    volume {numeric_type}(28, 10),
                    quote_volume {numeric_type}(28, 10),
                    trade_count INTEGER,
                    taker_buy_base_volume {numeric_type}(28, 10),
                    taker_buy_quote_volume {numeric_type}(28, 10),
                    source_interval VARCHAR(16) NOT NULL DEFAULT '1m',
                    source VARCHAR(80) NOT NULL DEFAULT 'binance_public_klines_derived',
                    created_at {timestamp_type} NOT NULL DEFAULT {now_expr},
                    UNIQUE(asset_id, interval, exchange, venue_symbol, bar_time)
                )
            """))
            connection.execute(text(f"""
                CREATE TABLE IF NOT EXISTS crypto_interval_indicators (
                    id {id_type},
                    asset_id BIGINT NOT NULL REFERENCES crypto_assets(id) ON DELETE CASCADE,
                    interval VARCHAR(16) NOT NULL,
                    exchange VARCHAR(32) NOT NULL DEFAULT 'binance',
                    venue_symbol VARCHAR(32) NOT NULL,
                    bar_time {timestamp_type} NOT NULL,
                    ma_5 {numeric_type}(24, 10),
                    ma_10 {numeric_type}(24, 10),
                    ma_20 {numeric_type}(24, 10),
                    ma_60 {numeric_type}(24, 10),
                    ema_5 {numeric_type}(24, 10),
                    ema_10 {numeric_type}(24, 10),
                    ema_12 {numeric_type}(24, 10),
                    ema_20 {numeric_type}(24, 10),
                    ema_26 {numeric_type}(24, 10),
                    ema_60 {numeric_type}(24, 10),
                    macd {numeric_type}(24, 10),
                    macd_signal {numeric_type}(24, 10),
                    macd_hist {numeric_type}(24, 10),
                    boll_mid {numeric_type}(24, 10),
                    boll_upper {numeric_type}(24, 10),
                    boll_lower {numeric_type}(24, 10),
                    rsi_14 {numeric_type}(12, 6),
                    kdj_k {numeric_type}(12, 6),
                    kdj_d {numeric_type}(12, 6),
                    kdj_j {numeric_type}(12, 6),
                    vol_ma_5 {numeric_type}(28, 10),
                    vol_ma_20 {numeric_type}(28, 10),
                    obv {numeric_type}(32, 10),
                    oi {numeric_type}(28, 10),
                    source_interval VARCHAR(16) NOT NULL DEFAULT '1m',
                    created_at {timestamp_type} NOT NULL DEFAULT {now_expr},
                    UNIQUE(asset_id, interval, exchange, venue_symbol, bar_time)
                )
            """))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_crypto_minute_prices_asset_time ON crypto_minute_prices(asset_id, bar_time)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_crypto_minute_indicators_asset_time ON crypto_minute_indicators(asset_id, bar_time)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_crypto_interval_prices_asset_interval_time ON crypto_interval_prices(asset_id, interval, bar_time)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_crypto_interval_indicators_asset_interval_time ON crypto_interval_indicators(asset_id, interval, bar_time)"))

    def reset_symbols(self, venue_symbols):
        with self.engine.begin() as connection:
            for venue_symbol in venue_symbols:
                asset_id = connection.execute(
                    text("SELECT id FROM crypto_assets WHERE venue_symbol = :venue_symbol"),
                    {"venue_symbol": venue_symbol},
                ).scalar()
                if not asset_id:
                    continue
                connection.execute(text("DELETE FROM crypto_interval_indicators WHERE asset_id = :asset_id"), {"asset_id": asset_id})
                connection.execute(text("DELETE FROM crypto_interval_prices WHERE asset_id = :asset_id"), {"asset_id": asset_id})
                connection.execute(text("DELETE FROM crypto_minute_indicators WHERE asset_id = :asset_id"), {"asset_id": asset_id})
                connection.execute(text("DELETE FROM crypto_minute_prices WHERE asset_id = :asset_id"), {"asset_id": asset_id})
                connection.execute(text("DELETE FROM crypto_assets WHERE id = :asset_id"), {"asset_id": asset_id})

    def upsert_asset(self, venue_symbol):
        base_asset, quote_asset = _venue_to_asset(venue_symbol)
        symbol = base_asset
        if self.dialect == "postgresql":
            statement = text("""
                INSERT INTO crypto_assets (symbol, base_asset, quote_asset, venue_symbol, exchange, source)
                VALUES (:symbol, :base_asset, :quote_asset, :venue_symbol, 'binance', 'binance_public_klines')
                ON CONFLICT (venue_symbol) DO UPDATE SET
                    symbol = EXCLUDED.symbol,
                    base_asset = EXCLUDED.base_asset,
                    quote_asset = EXCLUDED.quote_asset,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """)
        else:
            statement = text("""
                INSERT INTO crypto_assets (symbol, base_asset, quote_asset, venue_symbol, exchange, source)
                VALUES (:symbol, :base_asset, :quote_asset, :venue_symbol, 'binance', 'binance_public_klines')
                ON CONFLICT(venue_symbol) DO UPDATE SET
                    symbol = excluded.symbol,
                    base_asset = excluded.base_asset,
                    quote_asset = excluded.quote_asset,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """)
        with self.engine.begin() as connection:
            return connection.execute(
                statement,
                {
                    "symbol": symbol,
                    "base_asset": base_asset,
                    "quote_asset": quote_asset,
                    "venue_symbol": venue_symbol,
                },
            ).scalar_one()

    def _insert_statement(self, table_name, columns, conflict_columns):
        placeholders = ", ".join(f":{column}" for column in columns)
        column_names = ", ".join(columns)
        update_columns = [column for column in columns if column not in conflict_columns and column != "asset_id"]
        if self.dialect == "postgresql":
            assignments = ", ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
            return text(f"""
                INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})
                ON CONFLICT ({", ".join(conflict_columns)}) DO UPDATE SET {assignments}
            """)
        assignments = ", ".join(f"{column} = excluded.{column}" for column in update_columns)
        return text(f"""
            INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})
            ON CONFLICT ({", ".join(conflict_columns)}) DO UPDATE SET {assignments}
        """)

    def insert_batches(self, price_rows, indicator_rows):
        if not price_rows:
            return
        price_columns = list(price_rows[0].keys())
        indicator_columns = list(indicator_rows[0].keys())
        price_statement = self._insert_statement(
            "crypto_minute_prices",
            price_columns,
            ["asset_id", "exchange", "venue_symbol", "bar_time"],
        )
        indicator_statement = self._insert_statement(
            "crypto_minute_indicators",
            indicator_columns,
            ["asset_id", "exchange", "venue_symbol", "bar_time"],
        )
        with self.engine.begin() as connection:
            connection.execute(price_statement, price_rows)
            connection.execute(indicator_statement, indicator_rows)

    def insert_interval_batches(self, price_rows, indicator_rows):
        if not price_rows:
            return
        price_columns = list(price_rows[0].keys())
        indicator_columns = list(indicator_rows[0].keys())
        price_statement = self._insert_statement(
            "crypto_interval_prices",
            price_columns,
            ["asset_id", "interval", "exchange", "venue_symbol", "bar_time"],
        )
        indicator_statement = self._insert_statement(
            "crypto_interval_indicators",
            indicator_columns,
            ["asset_id", "interval", "exchange", "venue_symbol", "bar_time"],
        )
        with self.engine.begin() as connection:
            connection.execute(price_statement, price_rows)
            connection.execute(indicator_statement, indicator_rows)

    def refresh_asset_stats(self, asset_id):
        with self.engine.begin() as connection:
            stats = connection.execute(
                text("""
                    SELECT COUNT(*) AS row_count, MIN(bar_time) AS first_bar_time, MAX(bar_time) AS last_bar_time
                    FROM crypto_minute_prices
                    WHERE asset_id = :asset_id
                """),
                {"asset_id": asset_id},
            ).mappings().one()
            connection.execute(
                text("""
                    UPDATE crypto_assets
                    SET row_count = :row_count,
                        first_bar_time = :first_bar_time,
                        last_bar_time = :last_bar_time,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :asset_id
                """),
                {
                    "asset_id": asset_id,
                    "row_count": stats["row_count"] or 0,
                    "first_bar_time": stats["first_bar_time"],
                    "last_bar_time": stats["last_bar_time"],
                },
            )
            return dict(stats)


def _download_file(url: str, output_path: Path, retries: int = 3):
    if output_path.exists() and output_path.stat().st_size > 0:
        return {"status": "cached", "path": str(output_path)}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
                if response.status_code == 404:
                    return {"status": "missing", "path": str(output_path)}
                response.raise_for_status()
                temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
                with temporary_path.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 512):
                        if chunk:
                            handle.write(chunk)
                temporary_path.replace(output_path)
                return {"status": "downloaded", "path": str(output_path)}
        except Exception as error:
            last_error = str(error)
            time.sleep(1.5 * attempt)

    return {"status": "failed", "path": str(output_path), "message": last_error[:240]}


def _archive_targets(symbol: str, interval: str, start_date: date, end_date: date):
    current_month = _month_start(datetime.now(timezone.utc).date())
    targets = []

    for month in _month_range(start_date, end_date):
        if month < current_month:
            file_name = f"{symbol}-{interval}-{month:%Y-%m}.zip"
            url = f"{BINANCE_ARCHIVE_BASE_URL}/monthly/klines/{symbol}/{interval}/{file_name}"
            targets.append({"kind": "monthly", "period": month.isoformat(), "file_name": file_name, "url": url})
        else:
            first_day = max(month, start_date)
            last_day = min(end_date, datetime.now(timezone.utc).date())
            for day in _date_range(first_day, last_day):
                file_name = f"{symbol}-{interval}-{day:%Y-%m-%d}.zip"
                url = f"{BINANCE_ARCHIVE_BASE_URL}/daily/klines/{symbol}/{interval}/{file_name}"
                targets.append({"kind": "daily", "period": day.isoformat(), "file_name": file_name, "url": url})

    return targets


def _iter_zip_rows(zip_path: Path):
    with zipfile.ZipFile(zip_path) as archive:
        csv_members = [name for name in archive.namelist() if name.endswith(".csv")]
        for member_name in sorted(csv_members):
            with archive.open(member_name) as raw_file:
                text_file = io.TextIOWrapper(raw_file, encoding="utf-8")
                reader = csv.reader(text_file)
                for row in reader:
                    if len(row) < 11:
                        continue
                    try:
                        open_time = int(row[0])
                    except ValueError:
                        continue
                    yield {
                        "open_time": open_time,
                        "open": row[1],
                        "high": row[2],
                        "low": row[3],
                        "close": row[4],
                        "volume": row[5],
                        "quote_volume": row[7],
                        "trade_count": int(float(row[8])) if row[8] else None,
                        "taker_buy_base_volume": row[9],
                        "taker_buy_quote_volume": row[10],
                    }


def _flush(store, price_rows, indicator_rows):
    if price_rows:
        store.insert_batches(price_rows, indicator_rows)
        price_rows.clear()
        indicator_rows.clear()


def _flush_intervals(store, price_rows, indicator_rows):
    if price_rows:
        store.insert_interval_batches(price_rows, indicator_rows)
        price_rows.clear()
        indicator_rows.clear()


def _append_interval_rows(asset_id, symbol, interval_name, aggregate_bar, indicator_state, price_rows, indicator_rows):
    indicators = indicator_state.update(
        close=aggregate_bar["close"],
        high=aggregate_bar["high"],
        low=aggregate_bar["low"],
        volume=aggregate_bar["volume"],
    )
    price_rows.append(
        {
            "asset_id": asset_id,
            "interval": interval_name,
            "exchange": "binance",
            "venue_symbol": symbol,
            "bar_time": aggregate_bar["bar_time"],
            "open": _decimal_or_none(aggregate_bar["open"]),
            "high": _decimal_or_none(aggregate_bar["high"]),
            "low": _decimal_or_none(aggregate_bar["low"]),
            "close": _decimal_or_none(aggregate_bar["close"]),
            "volume": _decimal_or_none(aggregate_bar["volume"]),
            "quote_volume": _decimal_or_none(aggregate_bar["quote_volume"]),
            "trade_count": aggregate_bar["trade_count"],
            "taker_buy_base_volume": _decimal_or_none(aggregate_bar["taker_buy_base_volume"]),
            "taker_buy_quote_volume": _decimal_or_none(aggregate_bar["taker_buy_quote_volume"]),
            "source_interval": "1m",
            "source": "binance_public_klines_derived",
        }
    )
    indicator_rows.append(
        {
            "asset_id": asset_id,
            "interval": interval_name,
            "exchange": "binance",
            "venue_symbol": symbol,
            "bar_time": aggregate_bar["bar_time"],
            "source_interval": "1m",
            **{key: _decimal_or_none(value) for key, value in indicators.items()},
        }
    )


def _process_symbol(store, output_dir: Path, symbol: str, interval: str, start_date: date, end_date: date):
    asset_id = store.upsert_asset(symbol)
    raw_dir = output_dir / "raw" / "binance" / "spot" / "klines" / symbol / interval
    targets = _archive_targets(symbol, interval, start_date, end_date)
    state = IndicatorState()
    interval_aggregators = {
        interval_name: BarAggregator(interval_name, seconds)
        for interval_name, seconds in DERIVED_INTERVAL_SECONDS.items()
    }
    interval_indicator_states = {
        interval_name: IndicatorState()
        for interval_name in DERIVED_INTERVAL_SECONDS
    }
    price_rows = []
    indicator_rows = []
    interval_price_rows = []
    interval_indicator_rows = []
    interval_row_counts = {interval_name: 0 for interval_name in DERIVED_INTERVAL_SECONDS}
    downloaded = 0
    cached = 0
    missing = 0
    failed = 0
    processed_files = 0
    processed_rows = 0
    first_bar_time = None
    last_bar_time = None

    for target in targets:
        zip_path = raw_dir / target["file_name"]
        download_result = _download_file(target["url"], zip_path)
        status = download_result["status"]
        if status == "downloaded":
            downloaded += 1
        elif status == "cached":
            cached += 1
        elif status == "missing":
            missing += 1
            continue
        else:
            failed += 1
            print({"symbol": symbol, "file": target["file_name"], "status": status, "message": download_result.get("message", "")}, flush=True)
            continue

        processed_files += 1
        for row in _iter_zip_rows(zip_path):
            bar_time = _timestamp_to_datetime(row["open_time"])
            bar_day = bar_time.date()
            if bar_day < start_date or bar_day > end_date:
                continue

            close = _float_or_none(row["close"])
            high = _float_or_none(row["high"])
            low = _float_or_none(row["low"])
            volume = _float_or_none(row["volume"]) or 0.0
            if close is None or high is None or low is None:
                continue

            open_value = _float_or_none(row["open"])
            quote_volume = _float_or_none(row["quote_volume"]) or 0.0
            taker_buy_base_volume = _float_or_none(row["taker_buy_base_volume"]) or 0.0
            taker_buy_quote_volume = _float_or_none(row["taker_buy_quote_volume"]) or 0.0
            if open_value is None:
                continue

            indicators = state.update(close=close, high=high, low=low, volume=volume)
            price_rows.append(
                {
                    "asset_id": asset_id,
                    "exchange": "binance",
                    "venue_symbol": symbol,
                    "bar_time": bar_time,
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"],
                    "quote_volume": row["quote_volume"],
                    "trade_count": row["trade_count"],
                    "taker_buy_base_volume": row["taker_buy_base_volume"],
                    "taker_buy_quote_volume": row["taker_buy_quote_volume"],
                    "source_file": target["file_name"],
                }
            )
            indicator_rows.append(
                {
                    "asset_id": asset_id,
                    "exchange": "binance",
                    "venue_symbol": symbol,
                    "bar_time": bar_time,
                    **{key: _decimal_or_none(value) for key, value in indicators.items()},
                }
            )
            processed_rows += 1
            first_bar_time = first_bar_time or bar_time
            last_bar_time = bar_time

            minute_bar = {
                "bar_time": bar_time,
                "open": open_value,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "quote_volume": quote_volume,
                "trade_count": row["trade_count"] or 0,
                "taker_buy_base_volume": taker_buy_base_volume,
                "taker_buy_quote_volume": taker_buy_quote_volume,
                "source_file": target["file_name"],
            }
            for interval_name, aggregator in interval_aggregators.items():
                completed_bar = aggregator.add(minute_bar)
                if completed_bar is None:
                    continue
                _append_interval_rows(
                    asset_id,
                    symbol,
                    interval_name,
                    completed_bar,
                    interval_indicator_states[interval_name],
                    interval_price_rows,
                    interval_indicator_rows,
                )
                interval_row_counts[interval_name] += 1

            if len(price_rows) >= INSERT_BATCH_SIZE:
                _flush(store, price_rows, indicator_rows)
            if len(interval_price_rows) >= INSERT_BATCH_SIZE:
                _flush_intervals(store, interval_price_rows, interval_indicator_rows)

        _flush(store, price_rows, indicator_rows)
        _flush_intervals(store, interval_price_rows, interval_indicator_rows)
        if processed_files % 12 == 0:
            print({"symbol": symbol, "processedFiles": processed_files, "processedRows": processed_rows, "lastFile": target["file_name"]}, flush=True)

    _flush(store, price_rows, indicator_rows)
    for interval_name, aggregator in interval_aggregators.items():
        completed_bar = aggregator.flush()
        if completed_bar is None:
            continue
        _append_interval_rows(
            asset_id,
            symbol,
            interval_name,
            completed_bar,
            interval_indicator_states[interval_name],
            interval_price_rows,
            interval_indicator_rows,
        )
        interval_row_counts[interval_name] += 1
    _flush_intervals(store, interval_price_rows, interval_indicator_rows)
    stats = store.refresh_asset_stats(asset_id)
    return {
        "symbol": symbol,
        "assetId": asset_id,
        "interval": interval,
        "source": "binance_public_spot_klines",
        "requestedStartDate": start_date.isoformat(),
        "requestedEndDate": end_date.isoformat(),
        "processedFiles": processed_files,
        "downloadedFiles": downloaded,
        "cachedFiles": cached,
        "missingFiles": missing,
        "failedFiles": failed,
        "processedRowsThisRun": processed_rows,
        "firstBarThisRun": first_bar_time.isoformat() if first_bar_time else None,
        "lastBarThisRun": last_bar_time.isoformat() if last_bar_time else None,
        "storedRows": stats.get("row_count", 0),
        "storedFirstBar": str(stats.get("first_bar_time")) if stats.get("first_bar_time") else None,
        "storedLastBar": str(stats.get("last_bar_time")) if stats.get("last_bar_time") else None,
        "derivedIntervals": interval_row_counts,
    }


def _parse_args():
    parser = argparse.ArgumentParser(description="Sync BTC/ETH minute-level crypto history into independent NoobTrade crypto tables.")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS), help="Comma-separated venue symbols, e.g. BTCUSDT,ETHUSDT.")
    parser.add_argument("--interval", default=DEFAULT_INTERVAL, choices=("1m",), help="Only 1m is supported for this research store.")
    parser.add_argument("--start-date", default=(datetime.now(timezone.utc).date() - timedelta(days=365 * 10)).isoformat())
    parser.add_argument("--end-date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--database-url", default="", help="SQLite or Postgres URL. Defaults to Desktop crypto SQLite.")
    parser.add_argument("--reset", action="store_true", help="Delete existing rows for the selected crypto symbols before syncing.")
    return parser.parse_args()


def main():
    args = _parse_args()
    output_dir = Path(args.output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    database_url = args.database_url or f"sqlite:///{output_dir / 'noobtrade_crypto_history.sqlite'}"
    database_url = _normalize_database_url(database_url)
    if database_url.startswith("sqlite:///"):
        Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

    symbols = [item.strip().upper() for item in args.symbols.split(",") if item.strip()]
    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    store = CryptoHistoryStore(database_url)
    store.create_schema()

    if args.reset:
        store.reset_symbols(symbols)

    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "databaseUrl": database_url if not database_url.startswith("postgresql") else "postgresql://<redacted>",
        "outputDir": str(output_dir),
        "source": "Binance public spot klines archive",
        "sourceUrl": BINANCE_ARCHIVE_BASE_URL,
        "note": "Only real available Binance spot 1m candles are stored. Missing pre-listing years are not backfilled.",
        "symbols": [],
    }

    for symbol in symbols:
        result = _process_symbol(store, output_dir, symbol, args.interval, start_date, end_date)
        manifest["symbols"].append(result)
        print(result, flush=True)

    manifest_path = output_dir / "crypto_minute_history_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print({"status": "complete", "manifest": str(manifest_path)}, flush=True)


if __name__ == "__main__":
    main()
