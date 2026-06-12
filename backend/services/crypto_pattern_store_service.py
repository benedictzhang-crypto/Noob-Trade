import copy
import hashlib
import heapq
import json
import math
import sqlite3
import threading
import time
from datetime import date, datetime
from pathlib import Path
from statistics import mean
from types import SimpleNamespace
from urllib.parse import quote

from sqlalchemy import create_engine, text

from services.persistence_service import PersistenceService

try:
    import numpy as np
except Exception:  # pragma: no cover - optional speed path
    np = None


class CryptoPatternStoreService:
    """Read-only SQLite pattern-store for fast NoobTrade crypto Generate/Scan."""

    DAILY_GENERATE_STRATEGY = {
        "id": "crypto9-1d-moderate-smooth13",
        "name": "Crypto Daily Moderate",
        "timeframe": "daily",
        "indicatorFitWeight": 0.75,
        "pathWeight": 0.25,
        "buyThreshold": 88.0,
        "indicators": ("MA", "EMA", "MACD", "BOLL", "RSI", "VOL", "KDJ", "OI", "OBV"),
        "weights": {
            "BOLL": 1.1,
            "EMA": 1.0,
            "KDJ": 1.1,
            "MA": 1.1,
            "MACD": 1.1,
            "OBV": 30.3,
            "OI": 1.1,
            "RSI": 1.1,
            "VOL": 1.1,
        },
    }

    MATCH_TARGET = 20
    SCORE_INDICATOR_NAMES = ("MA", "EMA", "MACD", "BOLL", "RSI", "VOL", "KDJ", "OI", "OBV")
    _snapshot_lock = threading.RLock()
    _snapshot_cache = {}
    _response_cache = {}
    _response_cache_limit = 256
    _postgres_engine_cache = {}
    _postgres_availability_cache = {}
    _postgres_availability_ttl_seconds = 60

    def __init__(self, config):
        self.config = config
        self.store_path = Path(str(config.get("CRYPTO_PATTERN_STORE_PATH") or "")).expanduser()
        self.store_backend = str(config.get("CRYPTO_PATTERN_STORE_BACKEND") or "auto").strip().lower()
        self.database_url = self._normalize_database_url(
            config.get("CRYPTO_PATTERN_STORE_DATABASE_URL")
            or config.get("SQLALCHEMY_DATABASE_URI")
            or ""
        )
        self.persistence_service = PersistenceService()
        self.quant_scoring_service = self.persistence_service.quant_scoring_service

    def is_available(self):
        backend = self._resolve_backend()
        if backend == "postgres":
            return True
        if backend == "sqlite":
            return self._sqlite_is_available()
        return False

    def warm_cache(self, symbols=None):
        if not self.is_available():
            return {"available": False, "warmedSymbols": 0}
        snapshot = self._get_snapshot()
        warmed_symbols = []
        for symbol in symbols or ():
            symbol_code = self._normalize_symbol(symbol)
            if symbol_code not in snapshot["assets"]:
                continue
            self.get_crypto_pattern_analysis(symbol_code, compact_response=True)
            warmed_symbols.append(symbol_code)
        return {
            "available": True,
            "backend": snapshot.get("backend"),
            "assets": len(snapshot.get("assets") or {}),
            "windows": sum(len(rows) for rows in (snapshot.get("windows") or {}).values()),
            "warmedSymbols": len(warmed_symbols),
        }

    def get_crypto_pattern_analysis(
        self,
        symbol,
        interval="daily",
        lookback_window=30,
        compact_response=False,
        analysis_mode="full",
    ):
        del analysis_mode
        symbol_code = self._normalize_symbol(symbol)
        normalized_interval = self._normalize_interval(interval)
        if normalized_interval != "daily":
            raise ValueError("Crypto pattern store currently supports daily windows.")

        snapshot = self._get_snapshot()
        cache_key = (
            snapshot["fingerprint"],
            symbol_code,
            normalized_interval,
            int(lookback_window),
            bool(compact_response),
        )
        cached_response = self._get_cached_response(cache_key)
        if cached_response is not None:
            return cached_response

        asset = snapshot["assets"].get(symbol_code)
        if asset is None:
            raise ValueError(f"{symbol_code} is not in the crypto pattern store.")

        candles = snapshot["candles"].get((symbol_code, normalized_interval), [])
        if len(candles) < lookback_window:
            raise ValueError(f"Not enough stored candles for {symbol_code}.")

        current_candles = candles[-lookback_window:]
        current_window = self._build_window_record(current_candles, normalized_interval, lookback_window)
        matches = self._rank_matches(snapshot, current_window, normalized_interval, lookback_window, compact_response)
        current_price = self._to_float(candles[-1].get("close"))
        analysis = self._build_analysis(matches, current_price, candles[-1].get("trade_date"), compact_response)

        response = {
            "dataSource": "crypto-pattern-store",
            "marketDataProvider": "NoobTrade Crypto Pattern Store",
            "request": {
                "symbol": symbol_code,
                "interval": normalized_interval,
                "lookback": lookback_window,
                "indicators": list(self.DAILY_GENERATE_STRATEGY["indicators"]),
            },
            "stock": {
                "symbol": symbol_code,
                "companyName": asset["name"] or f"{symbol_code} Crypto",
                "sector": "Crypto",
                "industry": asset["category"] or "Pattern Store",
                "exchange": "OKX",
                "currentPrice": current_price,
                "previousClose": self._to_float(candles[-2].get("close")) if len(candles) > 1 else current_price,
                "open": self._to_float(candles[-1].get("open")),
                "volume": self._to_float(candles[-1].get("volume"), 0.0),
                "week52High": round(max(self._to_float(item.get("high"), 0.0) for item in candles[-365:]), 8),
                "week52Low": round(min(self._to_float(item.get("low"), current_price) for item in candles[-365:]), 8),
                "marketCapRank": asset["market_cap_rank"],
            },
            "patternAnalysis": analysis,
        }
        if not compact_response:
            response["chartData"] = {
                "series": {"daily": self._serialize_chart_candles(candles[-240:])},
                "history": {"daily": self._serialize_chart_candles(candles[-240:])},
            }
        self._set_cached_response(cache_key, response)
        return response

    def _connect(self):
        database_uri = f"file:{quote(str(self.store_path), safe='/')}?mode=ro&immutable=1"
        connection = sqlite3.connect(database_uri, uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def _sqlite_is_available(self):
        return self.store_path.exists() and self.store_path.is_file() and self.store_path.stat().st_size > 0

    def _database_is_postgres(self):
        return self.database_url.startswith("postgresql+psycopg://")

    def _normalize_database_url(self, raw_url):
        normalized = str(raw_url or "").strip()
        if normalized.startswith("postgres://"):
            return normalized.replace("postgres://", "postgresql+psycopg://", 1)
        if normalized.startswith("postgresql://"):
            return normalized.replace("postgresql://", "postgresql+psycopg://", 1)
        return normalized

    def _resolve_backend(self):
        if self.store_backend == "sqlite":
            return "sqlite" if self._sqlite_is_available() else None
        if self.store_backend == "postgres":
            return "postgres" if self._postgres_is_available() else None
        if self._database_is_postgres() and self._postgres_is_available():
            return "postgres"
        if self._sqlite_is_available():
            return "sqlite"
        return None

    def _postgres_url_fingerprint(self):
        return hashlib.sha256(self.database_url.encode("utf-8")).hexdigest()

    def _postgres_engine(self):
        if not self._database_is_postgres():
            return None
        fingerprint = self._postgres_url_fingerprint()
        with self._snapshot_lock:
            engine = type(self)._postgres_engine_cache.get(fingerprint)
            if engine is None:
                engine = create_engine(self.database_url, pool_pre_ping=True)
                type(self)._postgres_engine_cache[fingerprint] = engine
            return engine

    def _postgres_is_available(self):
        engine = self._postgres_engine()
        if engine is None:
            return False
        fingerprint = self._postgres_url_fingerprint()
        now = time.monotonic()
        cached = type(self)._postgres_availability_cache.get(fingerprint)
        if cached and now - cached["checked_at"] < self._postgres_availability_ttl_seconds:
            return cached["available"]
        available = False
        try:
            with engine.connect() as connection:
                row = connection.execute(
                    text(
                        """
                        SELECT
                            to_regclass('public.crypto_pattern_assets') IS NOT NULL AS has_assets,
                            to_regclass('public.crypto_pattern_candles') IS NOT NULL AS has_candles,
                            to_regclass('public.crypto_pattern_windows') IS NOT NULL AS has_windows
                        """
                    )
                ).mappings().one()
                if row["has_assets"] and row["has_candles"] and row["has_windows"]:
                    count = connection.execute(text("SELECT COUNT(*) FROM crypto_pattern_windows")).scalar_one()
                    available = int(count or 0) > 0
        except Exception:
            available = False
        type(self)._postgres_availability_cache[fingerprint] = {
            "checked_at": now,
            "available": available,
        }
        return available

    def _get_snapshot(self):
        backend = self._resolve_backend()
        if backend == "postgres":
            return self._get_postgres_snapshot()
        if backend == "sqlite":
            return self._get_sqlite_snapshot()
        raise ValueError("Crypto pattern store is not available.")

    def _get_sqlite_snapshot(self):
        stat = self.store_path.stat()
        fingerprint = ("sqlite", str(self.store_path), stat.st_mtime_ns, stat.st_size)
        with self._snapshot_lock:
            cached = type(self)._snapshot_cache.get(fingerprint[1])
            if cached and cached.get("fingerprint") == fingerprint:
                return cached
            snapshot = self._load_sqlite_snapshot(fingerprint)
            type(self)._snapshot_cache[fingerprint[1]] = snapshot
            type(self)._response_cache = {
                key: value
                for key, value in type(self)._response_cache.items()
                if key[0] == fingerprint
            }
            return snapshot

    def _get_postgres_snapshot(self):
        engine = self._postgres_engine()
        if engine is None:
            raise ValueError("Crypto pattern store database is not configured.")
        metadata = self._postgres_metadata(engine)
        fingerprint = (
            "postgres",
            self._postgres_url_fingerprint(),
            metadata.get("generatedAt"),
            metadata.get("assetCount"),
            metadata.get("windowCount"),
        )
        cache_key = f"postgres:{fingerprint[1]}"
        with self._snapshot_lock:
            cached = type(self)._snapshot_cache.get(cache_key)
            if cached and cached.get("fingerprint") == fingerprint:
                return cached
            snapshot = self._load_postgres_snapshot(engine, fingerprint)
            type(self)._snapshot_cache[cache_key] = snapshot
            type(self)._response_cache = {
                key: value
                for key, value in type(self)._response_cache.items()
                if key[0] == fingerprint
            }
            return snapshot

    def _postgres_metadata(self, engine):
        with engine.connect() as connection:
            manifest = {
                row["key"]: row["value"]
                for row in connection.execute(
                    text("SELECT key, value FROM crypto_pattern_build_manifest")
                ).mappings().fetchall()
            }
            asset_count = connection.execute(text("SELECT COUNT(*) FROM crypto_pattern_assets")).scalar_one()
            window_count = connection.execute(text("SELECT COUNT(*) FROM crypto_pattern_windows")).scalar_one()
        return {
            "generatedAt": manifest.get("generatedAt"),
            "assetCount": int(asset_count or 0),
            "windowCount": int(window_count or 0),
        }

    def _load_sqlite_snapshot(self, fingerprint):
        with self._connect() as connection:
            assets = {
                row["symbol"]: dict(row)
                for row in connection.execute("SELECT * FROM assets").fetchall()
            }
            candles = {}
            for row in connection.execute(
                """
                SELECT symbol, interval, bar_time, open, high, low, close, volume
                FROM candles
                ORDER BY symbol ASC, interval ASC, bar_time ASC
                """
            ).fetchall():
                key = (row["symbol"], row["interval"])
                candles.setdefault(key, []).append({
                    "trade_date": self._parse_date(row["bar_time"]),
                    "open": self._to_float(row["open"]),
                    "high": self._to_float(row["high"]),
                    "low": self._to_float(row["low"]),
                    "close": self._to_float(row["close"]),
                    "volume": self._to_float(row["volume"], 0.0),
                })
            windows = {}
            for row in connection.execute(
                """
                SELECT *
                FROM pattern_windows
                ORDER BY interval ASC, window_size ASC, id ASC
                """
            ).fetchall():
                row_data = dict(row)
                feature_vector = self._decode_json(row_data.get("feature_vector_json"), {})
                row_data["_future_stats"] = self._decode_json(row_data.get("future_stats_json"), {})
                row_data["_candidate_window"] = SimpleNamespace(
                    feature_vector=feature_vector,
                    return_pct=row_data["return_pct"],
                    avg_return=row_data["avg_return"],
                    max_drawdown=row_data["max_drawdown"],
                    timeframe=row_data["interval"],
                    window_size=row_data["window_size"],
                    end_date=self._parse_date(row_data["end_time"]),
                    id=row_data["id"],
                )
                row_data["_score_profile"] = self._score_profile_from_feature_vector(feature_vector)
                key = (row_data["interval"], row_data["window_size"])
                windows.setdefault(key, []).append(row_data)
        return {
            "fingerprint": fingerprint,
            "backend": "sqlite",
            "assets": assets,
            "candles": candles,
            "windows": windows,
            "window_vectors": self._build_window_vectors(windows),
        }

    def _load_postgres_snapshot(self, engine, fingerprint):
        with engine.connect() as connection:
            assets = {
                row["symbol"]: dict(row)
                for row in connection.execute(text("SELECT * FROM crypto_pattern_assets")).mappings().fetchall()
            }
            candles = {}
            for row in connection.execute(
                text(
                    """
                    SELECT symbol, interval, bar_time, open, high, low, close, volume
                    FROM crypto_pattern_candles
                    ORDER BY symbol ASC, interval ASC, bar_time ASC
                    """
                )
            ).mappings().fetchall():
                key = (row["symbol"], row["interval"])
                candles.setdefault(key, []).append({
                    "trade_date": self._parse_date(row["bar_time"]),
                    "open": self._to_float(row["open"]),
                    "high": self._to_float(row["high"]),
                    "low": self._to_float(row["low"]),
                    "close": self._to_float(row["close"]),
                    "volume": self._to_float(row["volume"], 0.0),
                })
            windows = {}
            for row in connection.execute(
                text(
                    """
                    SELECT id, symbol, interval, window_size, start_time, end_time, regime, diversity_key,
                           return_pct, avg_return, max_drawdown, volatility, probability_score,
                           ma_slope, ema_slope, macd_trend, rsi_avg, rsi_min, rsi_max, volume_change_ratio,
                           future_max_up_pct, future_max_down_pct, feature_vector_json, future_stats_json, source
                    FROM crypto_pattern_windows
                    ORDER BY interval ASC, window_size ASC, id ASC
                    """
                )
            ).mappings().fetchall():
                row_data = dict(row)
                feature_vector = self._decode_json(row_data.get("feature_vector_json"), {})
                row_data["_future_stats"] = self._decode_json(row_data.get("future_stats_json"), {})
                row_data["_candidate_window"] = SimpleNamespace(
                    feature_vector=feature_vector,
                    return_pct=row_data["return_pct"],
                    avg_return=row_data["avg_return"],
                    max_drawdown=row_data["max_drawdown"],
                    timeframe=row_data["interval"],
                    window_size=row_data["window_size"],
                    end_date=self._parse_date(row_data["end_time"]),
                    id=row_data["id"],
                )
                row_data["_score_profile"] = self._score_profile_from_feature_vector(feature_vector)
                key = (row_data["interval"], row_data["window_size"])
                windows.setdefault(key, []).append(row_data)
        return {
            "fingerprint": fingerprint,
            "backend": "postgres",
            "assets": assets,
            "candles": candles,
            "windows": windows,
            "window_vectors": self._build_window_vectors(windows),
        }

    def _get_cached_response(self, cache_key):
        with self._snapshot_lock:
            cached = type(self)._response_cache.get(cache_key)
            return copy.deepcopy(cached) if cached is not None else None

    def _set_cached_response(self, cache_key, response):
        with self._snapshot_lock:
            if len(type(self)._response_cache) >= self._response_cache_limit:
                type(self)._response_cache.pop(next(iter(type(self)._response_cache)))
            type(self)._response_cache[cache_key] = copy.deepcopy(response)

    def _normalize_symbol(self, symbol):
        normalized = str(symbol or "").strip().upper().replace(" ", "")
        for separator in ("/", "-", "_"):
            if separator in normalized:
                normalized = normalized.split(separator, 1)[0]
                break
        for suffix in ("USDT", "USDC", "BUSD", "USD"):
            if normalized.endswith(suffix) and len(normalized) > len(suffix) + 1:
                normalized = normalized[: -len(suffix)]
                break
        return normalized

    def _normalize_interval(self, interval):
        normalized = str(interval or "daily").strip().lower()
        if normalized in {"1d", "1day", "day"}:
            return "daily"
        return normalized

    def _load_candles(self, connection, symbol, interval):
        rows = connection.execute(
            """
            SELECT bar_time, open, high, low, close, volume
            FROM candles
            WHERE symbol = ? AND interval = ?
            ORDER BY bar_time ASC
            """,
            (symbol, interval),
        ).fetchall()
        return [
            {
                "trade_date": self._parse_date(row["bar_time"]),
                "open": self._to_float(row["open"]),
                "high": self._to_float(row["high"]),
                "low": self._to_float(row["low"]),
                "close": self._to_float(row["close"]),
                "volume": self._to_float(row["volume"], 0.0),
            }
            for row in rows
        ]

    def _rank_matches(self, snapshot, current_window, interval, lookback_window, compact_response):
        vectorized_matches = self._rank_matches_vectorized(snapshot, current_window, interval, lookback_window, compact_response)
        if vectorized_matches is not None:
            return vectorized_matches

        current_profile = self._score_profile_from_feature_vector(current_window.feature_vector)
        ranked = []
        for row in snapshot["windows"].get((interval, lookback_window), []):
            score = self._fast_score_match(current_profile, row["_score_profile"])
            ranked.append((row, score))
        top_matches = heapq.nlargest(
            self.MATCH_TARGET,
            ranked,
            key=lambda item: item[1].get("selected_score_percent") or 0.0,
        )
        matches = []
        for index, (row, score) in enumerate(top_matches, start=1):
            future_stats = row["_future_stats"]
            candles = [] if compact_response else self._load_window_candles(snapshot, row["id"])
            matches.append({
                "patternName": f"CRYPTO DAILY 30-bar match #{index}",
                "matchScore": round(score.get("selected_score_percent") or 0.0, 2),
                "date": row["end_time"],
                "symbol": row["symbol"],
                "timeframe": interval,
                "windowSize": lookback_window,
                "returnPct": self._round(row["return_pct"]),
                "maxDrawdown": self._round(row["max_drawdown"]),
                "futureReturn5d": self._round(row["future_max_up_pct"]),
                "futureDrawdown5d": self._round(row["future_max_down_pct"]),
                "futureStats5d": future_stats,
                "quantSelectedPercent": round(score.get("selected_score_percent") or 0.0, 2),
                "historicalCandles": candles,
                "regime": row["regime"],
                "diversityKey": row["diversity_key"],
            })
        return matches

    def _build_window_vectors(self, windows):
        if np is None:
            return {}
        vectors = {}
        for key, rows in windows.items():
            if not rows:
                continue
            indicators = [
                [self._nan_float(value) for value in row["_score_profile"]["indicators"]]
                for row in rows
            ]
            max_path_length = max((len(row["_score_profile"]["path"]) for row in rows), default=0)
            paths = []
            for row in rows:
                path = [self._nan_float(value) for value in row["_score_profile"]["path"]]
                if len(path) < max_path_length:
                    path.extend([math.nan] * (max_path_length - len(path)))
                paths.append(path)
            vectors[key] = {
                "indicator_matrix": np.array(indicators, dtype=float),
                "path_matrix": np.array(paths, dtype=float),
            }
        return vectors

    def _rank_matches_vectorized(self, snapshot, current_window, interval, lookback_window, compact_response):
        if np is None:
            return None
        rows = snapshot["windows"].get((interval, lookback_window), [])
        vector_bundle = snapshot.get("window_vectors", {}).get((interval, lookback_window))
        if not rows or not vector_bundle:
            return None

        current_profile = self._score_profile_from_feature_vector(current_window.feature_vector)
        current_indicators = np.array(
            [self._nan_float(value) for value in current_profile["indicators"]],
            dtype=float,
        )
        candidate_indicators = vector_bundle["indicator_matrix"]
        current_row = current_indicators.reshape(1, -1)
        valid = np.isfinite(candidate_indicators) & np.isfinite(current_row)
        sim_pct = np.full(candidate_indicators.shape, 999.0, dtype=float)

        absolute_indices = np.array([4, 6], dtype=int)
        relative_indices = np.array([0, 1, 2, 3, 5, 7, 8], dtype=int)
        sim_pct[:, absolute_indices] = np.abs(candidate_indicators[:, absolute_indices] - current_row[:, absolute_indices])
        floors = np.array([
            self.quant_scoring_service.RELATIVE_BASELINE_FLOORS.get(name, 1e-9)
            for name in ("MA", "EMA", "MACD", "BOLL", "VOL", "OI", "OBV")
        ], dtype=float)
        relative_candidate = candidate_indicators[:, relative_indices]
        relative_current = current_row[:, relative_indices]
        baseline = np.maximum(np.maximum(np.abs(relative_candidate), np.abs(relative_current)), floors)
        sim_pct[:, relative_indices] = np.abs(relative_candidate - relative_current) / baseline * 100.0
        sim_pct[~valid] = 999.0

        soft_windows = np.array([
            self.quant_scoring_service.SOFT_SIMILARITY_WINDOWS.get(name, 15)
            for name in self.SCORE_INDICATOR_NAMES
        ], dtype=float)
        weights = np.array([
            float(self.DAILY_GENERATE_STRATEGY["weights"].get(name, 0.0) or 0.0)
            for name in self.SCORE_INDICATOR_NAMES
        ], dtype=float)
        soft_similarity = 1.0 / (1.0 + (np.maximum(sim_pct, 0.0) / soft_windows))
        total_weight = float(np.sum(weights))
        indicator_fit = (soft_similarity * weights).sum(axis=1) / total_weight if total_weight else np.zeros(len(rows))

        path_similarity = self._vectorized_path_similarity(vector_bundle["path_matrix"], current_profile["path"])
        indicator_weight = float(self.DAILY_GENERATE_STRATEGY["indicatorFitWeight"])
        path_weight = float(self.DAILY_GENERATE_STRATEGY["pathWeight"])
        total_display_weight = indicator_weight + path_weight
        if total_display_weight <= 0:
            scores = np.zeros(len(rows))
        else:
            scores = (
                indicator_fit * (indicator_weight / total_display_weight)
                + path_similarity * (path_weight / total_display_weight)
            )
        scores = np.clip(scores, 0.0, 1.0) * 100.0

        target = min(self.MATCH_TARGET, len(rows))
        if target <= 0:
            return []
        candidate_indices = np.argpartition(scores, -target)[-target:]
        sorted_indices = candidate_indices[np.argsort(scores[candidate_indices])[::-1]]

        matches = []
        for index, row_index in enumerate(sorted_indices.tolist(), start=1):
            row = rows[row_index]
            score_percent = round(float(scores[row_index]), 4)
            future_stats = row["_future_stats"]
            candles = [] if compact_response else self._load_window_candles(snapshot, row["id"])
            matches.append({
                "patternName": f"CRYPTO DAILY 30-bar match #{index}",
                "matchScore": round(score_percent, 2),
                "date": row["end_time"],
                "symbol": row["symbol"],
                "timeframe": interval,
                "windowSize": lookback_window,
                "returnPct": self._round(row["return_pct"]),
                "maxDrawdown": self._round(row["max_drawdown"]),
                "futureReturn5d": self._round(row["future_max_up_pct"]),
                "futureDrawdown5d": self._round(row["future_max_down_pct"]),
                "futureStats5d": future_stats,
                "quantSelectedPercent": round(score_percent, 2),
                "historicalCandles": candles,
                "regime": row["regime"],
                "diversityKey": row["diversity_key"],
            })
        return matches

    def _load_window_candles(self, snapshot, window_id):
        if snapshot.get("backend") == "postgres":
            engine = self._postgres_engine()
            if engine is None:
                return []
            with engine.connect() as connection:
                raw_value = connection.execute(
                    text("SELECT candles_json FROM crypto_pattern_windows WHERE id = :window_id"),
                    {"window_id": window_id},
                ).scalar_one_or_none()
            return self._decode_json(raw_value, [])

        with self._connect() as connection:
            row = connection.execute(
                "SELECT candles_json FROM pattern_windows WHERE id = ?",
                (window_id,),
            ).fetchone()
        return self._decode_json(row["candles_json"], []) if row else []

    def _vectorized_path_similarity(self, candidate_paths, current_path):
        if candidate_paths.size == 0 or not current_path:
            return np.zeros(candidate_paths.shape[0], dtype=float)
        compare_length = min(candidate_paths.shape[1], len(current_path))
        if compare_length <= 0:
            return np.zeros(candidate_paths.shape[0], dtype=float)
        current = np.array([self._nan_float(value) for value in current_path[:compare_length]], dtype=float)
        candidates = candidate_paths[:, :compare_length]
        valid = np.isfinite(candidates) & np.isfinite(current.reshape(1, -1))
        diffs = np.where(valid, np.abs(candidates - current.reshape(1, -1)), 0.0)
        counts = valid.sum(axis=1)
        total_diff = diffs.sum(axis=1)
        mean_abs_diff = np.divide(total_diff, counts, out=np.full_like(total_diff, 999.0), where=counts > 0)
        similarity = 1.0 / (1.0 + (mean_abs_diff / 6.0))
        return np.clip(similarity, 0.0, 1.0)

    def _score_profile_from_feature_vector(self, feature_vector):
        indicators = (feature_vector or {}).get("indicators", {})
        path = (feature_vector or {}).get("normalized_close_path") or []
        return {
            "indicators": (
                indicators.get("ma"),
                indicators.get("ema"),
                indicators.get("macd"),
                indicators.get("boll_bandwidth"),
                indicators.get("rsi"),
                indicators.get("volume_ratio"),
                indicators.get("kdj_average"),
                indicators.get("oi"),
                indicators.get("obv"),
            ),
            "path": tuple(self._to_float(value, 0.0) for value in path),
        }

    def _fast_score_match(self, current_profile, candidate_profile):
        total_weight = 0.0
        total_soft_similarity = 0.0
        weights = self.DAILY_GENERATE_STRATEGY["weights"]
        current_values = current_profile.get("indicators") or ()
        candidate_values = candidate_profile.get("indicators") or ()

        for index, indicator_name in enumerate(self.SCORE_INDICATOR_NAMES):
            current_value = current_values[index] if index < len(current_values) else None
            candidate_value = candidate_values[index] if index < len(candidate_values) else None
            sim_pct = self._fast_similarity_percent(indicator_name, current_value, candidate_value)
            weight = float(weights.get(indicator_name, 0.0) or 0.0)
            soft_similarity = self._fast_soft_similarity(indicator_name, sim_pct)
            total_weight += weight
            total_soft_similarity += soft_similarity * weight

        indicator_fit_ratio = (total_soft_similarity / total_weight) if total_weight else 0.0
        path_similarity = self._fast_price_path_similarity(
            current_profile.get("path") or (),
            candidate_profile.get("path") or (),
        )
        indicator_weight = float(self.DAILY_GENERATE_STRATEGY["indicatorFitWeight"])
        path_weight = float(self.DAILY_GENERATE_STRATEGY["pathWeight"])
        total_display_weight = indicator_weight + path_weight
        display_fit_ratio = 0.0
        if total_display_weight > 0:
            display_fit_ratio = (
                (indicator_fit_ratio * (indicator_weight / total_display_weight))
                + (path_similarity * (path_weight / total_display_weight))
            )
        display_fit_ratio = max(0.0, min(1.0, display_fit_ratio))
        return {"selected_score_percent": round(display_fit_ratio * 100.0, 4)}

    def _fast_similarity_percent(self, indicator_name, current_value, candidate_value):
        if current_value is None or candidate_value is None:
            return 999.0
        try:
            current_number = float(current_value)
            candidate_number = float(candidate_value)
        except (TypeError, ValueError):
            return 999.0
        if not math.isfinite(current_number) or not math.isfinite(candidate_number):
            return 999.0
        if indicator_name in ("RSI", "KDJ"):
            return abs(current_number - candidate_number)
        baseline = max(
            abs(current_number),
            abs(candidate_number),
            self.quant_scoring_service.RELATIVE_BASELINE_FLOORS.get(indicator_name, 1e-9),
        )
        return abs(current_number - candidate_number) / baseline * 100.0

    def _fast_soft_similarity(self, indicator_name, sim_pct):
        soft_window = self.quant_scoring_service.SOFT_SIMILARITY_WINDOWS.get(indicator_name, 15)
        similarity = 1.0 / (1.0 + (max(sim_pct, 0.0) / soft_window))
        return max(0.0, min(1.0, similarity))

    def _fast_price_path_similarity(self, current_path, candidate_path):
        compare_length = min(len(current_path), len(candidate_path))
        if compare_length <= 0:
            return 0.0
        total_diff = 0.0
        for index in range(compare_length):
            total_diff += abs(float(current_path[index]) - float(candidate_path[index]))
        mean_abs_diff = total_diff / compare_length
        similarity = 1.0 / (1.0 + (mean_abs_diff / 6.0))
        return max(0.0, min(1.0, similarity))

    def _build_analysis(self, matches, current_price, last_date, compact_response):
        if not matches:
            return {
                "lookbackWindow": 30,
                "selectedIndicators": list(self.DAILY_GENERATE_STRATEGY["indicators"]),
                "probabilityOfIncrease": 0.0,
                "probabilityOfDecrease": 0.0,
                "avgReturn": None,
                "maxDrawdown": None,
                "matchedPatternsCount": 0,
                "matchedHistoricalPatterns": [],
                "quantConfidence": 0.0,
                "signalClassification": "Crypto Daily Neutral Bias",
                "futureFiveDayProbabilities": {
                    "up": [{"threshold": value, "probability": 0.0} for value in (1, 5, 10)],
                    "down": [{"threshold": value, "probability": 0.0} for value in (1, 5, 10)],
                },
                "recommendedSellPrice": round(current_price * 1.01, 8),
                "recommendedSellDate": str(last_date),
                "stopLossPrice": round(current_price * 0.99, 8),
                "highFitHistoricalPaths": [],
            }
        up_probabilities = self._threshold_probabilities(matches, "up")
        down_probabilities = self._threshold_probabilities(matches, "down")
        avg_up = round(mean(match["futureStats5d"]["maxUpPct"] for match in matches), 4)
        avg_down = round(mean(match["futureStats5d"]["maxDownPct"] for match in matches), 4)
        confidence = round(mean(match.get("matchScore", 0.0) for match in matches) / 100.0, 2)
        signal = self._signal_label(up_probabilities[0]["probability"], down_probabilities[0]["probability"], confidence)
        analysis = {
            "lookbackWindow": 30,
            "selectedIndicators": list(self.DAILY_GENERATE_STRATEGY["indicators"]),
            "probabilityOfIncrease": up_probabilities[0]["probability"],
            "probabilityOfDecrease": down_probabilities[0]["probability"],
            "avgReturn": avg_up,
            "maxDrawdown": avg_down,
            "matchedPatternsCount": len(matches),
            "matchedHistoricalPatterns": [] if compact_response else matches,
            "quantConfidence": confidence,
            "signalClassification": signal,
            "futureFiveDayProbabilities": {
                "up": up_probabilities,
                "down": down_probabilities,
            },
            "recommendedSellPrice": round(current_price * (1 + max(avg_up, 0.0) / 100.0), 8),
            "recommendedSellDate": str(last_date),
            "stopLossPrice": round(current_price * (1 + min(avg_down, 0.0) / 100.0), 8),
            "highFitHistoricalPaths": [] if compact_response else [
                {
                    "label": match["patternName"],
                    "fitScore": match["matchScore"],
                    "status": f"{match['symbol']} ended on {match['date']} | +5D hi {self._format_signed_percent(match['futureReturn5d'])} | -5D lo {self._format_signed_percent(match['futureDrawdown5d'])}",
                }
                for match in matches
            ],
        }
        return analysis

    def _threshold_probabilities(self, matches, direction):
        output = []
        field = "maxUpPct" if direction == "up" else "maxDownPct"
        thresholds = (1, 5, 10)
        for threshold in thresholds:
            if direction == "up":
                passed = [match for match in matches if self._to_float(match["futureStats5d"].get(field), -math.inf) >= threshold]
            else:
                passed = [match for match in matches if self._to_float(match["futureStats5d"].get(field), math.inf) <= -threshold]
            output.append({"threshold": threshold, "probability": round((len(passed) / len(matches)) * 100.0, 2) if matches else 0.0})
        return output

    def _signal_label(self, upside_probability, downside_probability, confidence):
        if upside_probability >= 60 and upside_probability >= downside_probability and confidence >= 0.45:
            return "Crypto Daily Moderate Bias"
        if downside_probability > upside_probability:
            return "Crypto Daily Risk Bias"
        return "Crypto Daily Neutral Bias"

    def _build_window_record(self, candles, interval, lookback_window):
        summary = self.persistence_service._build_window_summary(candles)
        return SimpleNamespace(
            feature_vector=summary["feature_vector"],
            return_pct=summary["return_pct"],
            avg_return=summary["avg_return"],
            max_drawdown=summary["max_drawdown"],
            timeframe=interval,
            window_size=lookback_window,
            end_date=candles[-1]["trade_date"],
            id=None,
        )

    def _serialize_chart_candles(self, candles):
        return [
            {
                "date": item["trade_date"].isoformat() if hasattr(item["trade_date"], "isoformat") else str(item["trade_date"]),
                "open": self._to_float(item["open"]),
                "high": self._to_float(item["high"]),
                "low": self._to_float(item["low"]),
                "close": self._to_float(item["close"]),
                "volume": self._to_float(item.get("volume"), 0.0),
            }
            for item in candles
        ]

    def _parse_date(self, raw_value):
        if isinstance(raw_value, date):
            return raw_value
        return datetime.fromisoformat(str(raw_value).split("T", 1)[0]).date()

    def _to_float(self, value, default=0.0):
        try:
            if value is None:
                return default
            numeric = float(value)
        except (TypeError, ValueError):
            return default
        return numeric if math.isfinite(numeric) else default

    def _nan_float(self, value):
        return self._to_float(value, math.nan)

    def _decode_json(self, value, default):
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return default

    def _round(self, value):
        if value is None:
            return None
        return round(self._to_float(value), 4)

    def _format_signed_percent(self, value):
        numeric = self._to_float(value)
        return f"{numeric:+.2f}%"
