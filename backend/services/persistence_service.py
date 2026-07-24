from copy import deepcopy
from bisect import bisect_right
from datetime import date, datetime, timedelta
import heapq
from statistics import mean, pstdev
import threading
import time
from types import SimpleNamespace

from sqlalchemy import and_, literal, or_

from config import Config
from extensions import db
from models.analysis import AnalysisRun, PatternMatch
from models.market_data import DailyIndicator, DailyPrice, PatternWindow, Symbol
from services.quant_scoring_service import QuantScoringService


class PersistenceService:
    """Handle database writes for symbols, prices, indicators, pattern windows, matches, and analysis history."""

    SUPPORTED_WINDOW_SIZES = (20, 30, 60)
    TIMEFRAME_GROUP_SIZES = {
        "daily": 1,
        "5day": 5,
        "weekly": 5,
        "2week": 10,
        "monthly": 21,
    }
    MATCH_TARGET = 20
    MATCH_CANDIDATE_POOL_SIZE = 4000
    MATCH_SCORING_SYMBOLS = tuple(Config.MATCH_SCORING_SYMBOLS)
    MATCH_CANDIDATE_SNAPSHOT = {}
    MATCH_CANDIDATE_SNAPSHOT_LOCK = threading.RLock()
    MATCH_PREVIEW_CACHE = {}
    MATCH_PREVIEW_CACHE_LOCK = threading.RLock()
    MATCH_PREVIEW_CACHE_MAX_ENTRIES = 512
    MATCH_PREVIEW_CACHE_TTL_SECONDS = Config.MATCH_PREVIEW_CACHE_TTL_SECONDS
    HIGH_FIT_THRESHOLD = 70.0
    SUPPORTED_TIMEFRAMES = ("daily", "5day", "weekly", "2week", "monthly")

    def __init__(self):
        self.quant_scoring_service = QuantScoringService()

    def save_analysis_run(self, response_data):
        """Persist symbol data, computed summaries, and the current analysis run."""
        try:
            original_pattern_analysis = dict(response_data.get("patternAnalysis", {}))
            current_window_override = self._hydrate_current_window(response_data.pop("_currentWindow", None))
            skip_cache_write = bool(response_data.pop("_skipCacheWrite", False))
            symbol_record = self._upsert_symbol(response_data["stock"])
            daily_candles = self._extract_daily_candles(response_data.get("chartData", {}))
            prepared_candles = self._prepare_candles(daily_candles)
            data_source = response_data.get("dataSource", "mock")
            timeframe = response_data["request"]["interval"]
            window_size = response_data["request"]["lookback"]

            cache_ready = skip_cache_write or self._is_cache_ready(
                symbol_record.id,
                prepared_candles,
                timeframe,
                window_size,
            )

            if not cache_ready:
                self._upsert_daily_prices(symbol_record.id, daily_candles, data_source)
                self._upsert_daily_indicators(symbol_record.id, prepared_candles)
                self._upsert_pattern_windows(
                    symbol_record.id,
                    prepared_candles,
                    timeframe,
                    window_size,
                )

            analysis_run = AnalysisRun(
                symbol_id=symbol_record.id,
                timeframe=response_data["request"]["interval"],
                lookback_window=response_data["request"]["lookback"],
                indicators=response_data["request"]["indicators"],
                probability_of_increase=response_data["patternAnalysis"]["probabilityOfIncrease"],
                recommended_sell_price=response_data["patternAnalysis"].get("recommendedSellPrice"),
                recommended_sell_date=self._parse_date(response_data["patternAnalysis"].get("recommendedSellDate")),
                stop_loss_price=response_data["patternAnalysis"].get("stopLossPrice"),
                avg_return=response_data["patternAnalysis"].get("avgReturn"),
                max_drawdown=response_data["patternAnalysis"].get("maxDrawdown"),
                request_payload=response_data["request"],
                response_payload=response_data,
            )

            db.session.add(analysis_run)
            db.session.flush()

            current_window = current_window_override or self._find_current_window(
                symbol_id=symbol_record.id,
                timeframe=response_data["request"]["interval"],
                lookback_window=response_data["request"]["lookback"],
            )
            matched_patterns = self._create_pattern_matches(
                analysis_run.id,
                current_window,
                response_data["request"]["indicators"],
            )

            # Keep the live-computed forecast when persistence has no usable matches yet.
            if matched_patterns:
                self._apply_match_results_to_response(response_data, matched_patterns)
            else:
                response_data["patternAnalysis"] = {
                    **response_data.get("patternAnalysis", {}),
                    **original_pattern_analysis,
                }

            analysis_run.response_payload = response_data

            analysis_run.probability_of_increase = response_data["patternAnalysis"]["probabilityOfIncrease"]
            analysis_run.response_payload = response_data
            db.session.commit()
            return response_data
        except Exception:
            db.session.rollback()
            raise

    def apply_cached_match_preview(self, response_data, include_historical_candles=True, scoring_profile=None):
        """Apply indicator-aware historical matches without persisting a new analysis run."""
        current_window = self._hydrate_current_window(response_data.get("_currentWindow"))

        if current_window is None:
            return response_data

        matched_patterns = self._create_pattern_matches(
            analysis_run_id=None,
            current_window=current_window,
            selected_indicators=response_data.get("request", {}).get("indicators", []),
            persist_matches=False,
            include_historical_candles=include_historical_candles,
            scoring_profile=scoring_profile,
        )

        if matched_patterns:
            self._apply_match_results_to_response(response_data, matched_patterns, scoring_profile=scoring_profile)

        return response_data

    def _hydrate_current_window(self, current_window_payload):
        if not current_window_payload:
            return None

        end_date = self._parse_date(current_window_payload.get("endDate"))

        return SimpleNamespace(
            feature_vector=current_window_payload.get("featureVector") or {},
            return_pct=current_window_payload.get("returnPct"),
            avg_return=current_window_payload.get("avgReturn"),
            max_drawdown=current_window_payload.get("maxDrawdown"),
            volatility=current_window_payload.get("volatility"),
            probability_score=current_window_payload.get("probabilityScore"),
            ma_slope=current_window_payload.get("maSlope"),
            ema_slope=current_window_payload.get("emaSlope"),
            macd_trend=current_window_payload.get("macdTrend"),
            rsi_avg=current_window_payload.get("rsiAvg"),
            rsi_min=current_window_payload.get("rsiMin"),
            rsi_max=current_window_payload.get("rsiMax"),
            volume_change_ratio=current_window_payload.get("volumeChangeRatio"),
            timeframe=current_window_payload.get("timeframe"),
            window_size=current_window_payload.get("windowSize"),
            end_date=end_date,
            id=None,
        )

    def warm_symbol_cache(self, response_data, timeframes=None, window_sizes=None):
        """Precompute prices, indicators, and factor windows for a symbol."""
        try:
            symbol_record = self._upsert_symbol(response_data["stock"])
            daily_candles = self._extract_daily_candles(response_data.get("chartData", {}))
            prepared_candles = self._prepare_candles(daily_candles)
            data_source = response_data.get("dataSource", "mock")

            if not prepared_candles:
                return {
                    "symbol": symbol_record.symbol,
                    "dailyPriceRows": 0,
                    "indicatorRows": 0,
                    "patternWindows": 0,
                }

            self._upsert_daily_prices(symbol_record.id, daily_candles, data_source)
            self._upsert_daily_indicators(symbol_record.id, prepared_candles)

            timeframes_to_build = tuple(timeframes or self.SUPPORTED_TIMEFRAMES)
            window_sizes_to_build = tuple(window_sizes or self.SUPPORTED_WINDOW_SIZES)
            built_windows = 0

            for timeframe in timeframes_to_build:
                for window_size in window_sizes_to_build:
                    built_windows += self._upsert_pattern_windows(
                        symbol_record.id,
                        prepared_candles,
                        timeframe,
                        window_size,
                    )

            db.session.commit()
            return {
                "symbol": symbol_record.symbol,
                "dailyPriceRows": len(prepared_candles),
                "indicatorRows": len(prepared_candles),
                "patternWindows": built_windows,
            }
        except Exception:
            db.session.rollback()
            raise

    def _upsert_symbol(self, stock_data):
        symbol_record = Symbol.query.filter_by(symbol=stock_data["symbol"]).first()

        if symbol_record is None:
            symbol_record = Symbol(symbol=stock_data["symbol"])
            db.session.add(symbol_record)

        symbol_record.company_name = stock_data.get("companyName")
        symbol_record.sector = stock_data.get("sector")
        symbol_record.industry = stock_data.get("industry")
        symbol_record.exchange = stock_data.get("exchange")
        symbol_record.market_cap = stock_data.get("marketCap")
        db.session.flush()
        return symbol_record

    def _extract_daily_candles(self, chart_data):
        history = chart_data.get("history", {})

        if history.get("daily"):
            return history["daily"]

        series = chart_data.get("series", {})
        return series.get("daily", [])

    def _upsert_daily_prices(self, symbol_id, daily_candles, data_source):
        candle_rows = [
            (candle, self._parse_date(candle.get("date")))
            for candle in daily_candles
        ]
        trade_dates = [trade_date for _, trade_date in candle_rows if trade_date is not None]
        existing_records = {
            record.trade_date: record
            for record in DailyPrice.query.filter(
                DailyPrice.symbol_id == symbol_id,
                DailyPrice.trade_date.in_(trade_dates),
            ).all()
        } if trade_dates else {}

        for candle, trade_date in candle_rows:
            if trade_date is None:
                continue

            price_record = existing_records.get(trade_date)

            if price_record is None:
                price_record = DailyPrice(symbol_id=symbol_id, trade_date=trade_date)
                db.session.add(price_record)
                existing_records[trade_date] = price_record

            price_record.open = candle.get("open")
            price_record.high = candle.get("high")
            price_record.low = candle.get("low")
            price_record.close = candle.get("close")
            price_record.adjusted_close = candle.get("close")
            price_record.volume = candle.get("volume")
            price_record.source = data_source

    def _upsert_daily_indicators(self, symbol_id, prepared_candles):
        trade_dates = [candle["trade_date"] for candle in prepared_candles]
        existing_records = {
            record.trade_date: record
            for record in DailyIndicator.query.filter(
                DailyIndicator.symbol_id == symbol_id,
                DailyIndicator.trade_date.in_(trade_dates),
            ).all()
        } if trade_dates else {}

        for index, candle in enumerate(prepared_candles):
            trade_date = candle["trade_date"]
            closes = [item["close"] for item in prepared_candles[: index + 1]]
            highs = [item["high"] for item in prepared_candles[: index + 1]]
            lows = [item["low"] for item in prepared_candles[: index + 1]]
            volumes = [item["volume"] for item in prepared_candles[: index + 1]]

            indicator_record = existing_records.get(trade_date)

            if indicator_record is None:
                indicator_record = DailyIndicator(symbol_id=symbol_id, trade_date=trade_date)
                db.session.add(indicator_record)
                existing_records[trade_date] = indicator_record

            indicator_record.ma_5 = self._simple_moving_average(closes, 5)
            indicator_record.ma_10 = self._simple_moving_average(closes, 10)
            indicator_record.ma_20 = self._simple_moving_average(closes, 20)
            indicator_record.ma_60 = self._simple_moving_average(closes, 60)

            indicator_record.ema_5 = self._exponential_moving_average(closes, 5)
            indicator_record.ema_10 = self._exponential_moving_average(closes, 10)
            indicator_record.ema_12 = self._exponential_moving_average(closes, 12)
            indicator_record.ema_20 = self._exponential_moving_average(closes, 20)
            indicator_record.ema_26 = self._exponential_moving_average(closes, 26)
            indicator_record.ema_60 = self._exponential_moving_average(closes, 60)

            macd_line = self._macd_line(closes)
            macd_signal = self._macd_signal(closes)

            indicator_record.macd = macd_line
            indicator_record.macd_signal = macd_signal
            indicator_record.macd_hist = self._subtract_or_none(macd_line, macd_signal)

            indicator_record.rsi_14 = self._relative_strength_index(closes, 14)

            boll_values = self._bollinger_bands(closes, 20)
            indicator_record.boll_mid = boll_values["mid"]
            indicator_record.boll_upper = boll_values["upper"]
            indicator_record.boll_lower = boll_values["lower"]

            kdj_values = self._kdj(highs, lows, closes, period=9)
            indicator_record.kdj_k = kdj_values["k"]
            indicator_record.kdj_d = kdj_values["d"]
            indicator_record.kdj_j = kdj_values["j"]

            indicator_record.vol_ma_5 = self._simple_moving_average(volumes, 5)
            indicator_record.vol_ma_20 = self._simple_moving_average(volumes, 20)
            indicator_record.oi = self._open_interest_proxy(closes, volumes)
            indicator_record.pbv = self._on_balance_volume(closes, volumes)

    def _upsert_pattern_windows(self, symbol_id, prepared_candles, timeframe, window_size):
        group_size = self.TIMEFRAME_GROUP_SIZES.get(timeframe)
    
        if group_size is None:
            return 0
    
        grouped_candles = self._group_prepared_candles(prepared_candles, group_size)
    
        if len(grouped_candles) < window_size:
            return 0
    
        existing_records = {
            record.end_date: record
            for record in PatternWindow.query.filter_by(
                symbol_id=symbol_id,
                timeframe=timeframe,
                window_size=window_size,
            ).all()
        }
        forward_stats_lookup = self._build_forward_stats_lookup(prepared_candles)
        upserted_count = 0
    
        for window_end_index in range(window_size, len(grouped_candles) + 1):
            window_candles = grouped_candles[window_end_index - window_size:window_end_index]
            summary = self._build_window_summary(window_candles)
            end_date = window_candles[-1]["trade_date"]
            start_date = window_candles[0]["trade_date"]
            forward_stats = forward_stats_lookup.get(
                end_date,
                {
                    "5d": self._empty_forward_stat(),
                    "10d": self._empty_forward_stat(),
                    "20d": self._empty_forward_stat(),
                },
            )
            summary["feature_vector"]["forwardReturns"] = {
                horizon: stats.get("maxUpPct")
                for horizon, stats in forward_stats.items()
            }
            summary["feature_vector"]["forwardExtremes"] = forward_stats
    
            pattern_window = existing_records.get(end_date)
    
            if pattern_window is None:
                pattern_window = PatternWindow(
                    symbol_id=symbol_id,
                    timeframe=timeframe,
                    window_size=window_size,
                    end_date=end_date,
                )
                db.session.add(pattern_window)
                existing_records[end_date] = pattern_window
    
            pattern_window.start_date = start_date
            pattern_window.return_pct = summary["return_pct"]
            pattern_window.avg_return = summary["avg_return"]
            pattern_window.max_drawdown = summary["max_drawdown"]
            pattern_window.volatility = summary["volatility"]
            pattern_window.probability_score = summary["probability_score"]
            pattern_window.ma_slope = summary["ma_slope"]
            pattern_window.ema_slope = summary["ema_slope"]
            pattern_window.macd_trend = summary["macd_trend"]
            pattern_window.rsi_avg = summary["rsi_avg"]
            pattern_window.rsi_min = summary["rsi_min"]
            pattern_window.rsi_max = summary["rsi_max"]
            pattern_window.volume_change_ratio = summary["volume_change_ratio"]
            pattern_window.feature_vector = summary["feature_vector"]
            upserted_count += 1
    
        return upserted_count
    
    def _find_current_window(self, symbol_id, timeframe, lookback_window):
        return PatternWindow.query.filter_by(
            symbol_id=symbol_id,
            timeframe=timeframe,
            window_size=lookback_window,
        ).order_by(PatternWindow.end_date.desc()).first()
    
    def _create_pattern_matches(self, analysis_run_id, current_window, selected_indicators, persist_matches=True, include_historical_candles=True, scoring_profile=None):
        if current_window is None:
            return []

        preview_cache_key = None
        if not persist_matches:
            preview_cache_key = self._match_preview_cache_key(current_window, selected_indicators, scoring_profile=scoring_profile)
            cached_preview = self._get_cached_match_preview(preview_cache_key)
            if cached_preview is not None:
                return self._hydrate_cached_match_preview(cached_preview, include_historical_candles)

        candidate_windows = self._candidate_windows_from_snapshot(current_window, selected_indicators)
        if candidate_windows is None:
            candidate_window_ids = self._candidate_window_ids(current_window, selected_indicators)

            if not candidate_window_ids:
                return []

            candidate_windows = PatternWindow.query.filter(
                PatternWindow.id.in_(candidate_window_ids),
            ).all()
        elif not candidate_windows:
            return []
    
        ranked_matches = []
    
        for candidate in candidate_windows:
            score = self.quant_scoring_service.score_match(
                current_window,
                candidate,
                selected_indicators,
                include_breakdown=False,
                scoring_profile=scoring_profile,
            )
            future_stats_5d = self._cached_forward_extremes(candidate, trading_days=5)
            score["future_stats_5d"] = future_stats_5d
            score["future_return_5d"] = future_stats_5d.get("maxUpPct")
            score["future_drawdown_5d"] = future_stats_5d.get("maxDownPct")
            score["is_future_bullish"] = (
                score["future_return_5d"] is not None and score["future_return_5d"] >= 0.5
            )
            ranked_matches.append((candidate, score))
    
        ranked_matches.sort(key=lambda item: item[1]["selected_score_percent"], reverse=True)
        top_matches = self._select_match_bundles(ranked_matches)
        matched_window_ids = [matched_window.id for matched_window, _ in top_matches]
        matched_symbol_ids = [matched_window.symbol_id for matched_window, _ in top_matches]
        symbol_lookup = {
            symbol.id: symbol.symbol
            for symbol in Symbol.query.filter(Symbol.id.in_(matched_symbol_ids)).all()
        } if matched_symbol_ids else {}
        historical_candle_lookup = {}
        if include_historical_candles:
            historical_candle_lookup = self._build_match_candles_map(
                [matched_window for matched_window, _ in top_matches]
            )
    
        response_matches = []
    
        for rank_no, (matched_window, score) in enumerate(top_matches, start=1):
            historical_candles = historical_candle_lookup.get(matched_window.id, [])
            match_future_stats_5d = score.get("future_stats_5d") or self._empty_forward_stat()
            if persist_matches and analysis_run_id is not None:
                pattern_match = PatternMatch(
                    analysis_run_id=analysis_run_id,
                    matched_window_id=matched_window.id,
                    rank_no=rank_no,
                    similarity_score=score["score_percent"],
                    pattern_label=self._build_pattern_label(matched_window),
                    forward_return_5d=None,
                    forward_return_10d=None,
                    forward_return_20d=None,
                )
                db.session.add(pattern_match)
    
            response_matches.append(
                {
                    "patternName": self._build_pattern_label(matched_window),
                    "matchScore": round(score["selected_score_percent"], 2),
                    "date": matched_window.end_date.isoformat(),
                    "symbol": symbol_lookup.get(matched_window.symbol_id, "N/A"),
                    "timeframe": matched_window.timeframe,
                    "windowSize": matched_window.window_size,
                    "returnPct": self._to_response_number(matched_window.return_pct),
                    "maxDrawdown": self._to_response_number(matched_window.max_drawdown),
                    "isBullishHistory": score["is_bullish"],
                    "futureReturn5d": self._to_response_number(score["future_return_5d"]),
                    "futureDrawdown5d": self._to_response_number(score["future_drawdown_5d"]),
                    "isFutureBullish": score["is_future_bullish"],
                    "futureStats5d": match_future_stats_5d,
                    "quantScore": score["total_score"],
                    "quantMaxScore": score["max_score"],
                    "quantFullMaxScore": score["full_scale_max_score"],
                    "quantSelectedPercent": score["selected_score_percent"],
                    "scoreBreakdown": score.get("breakdown", []),
                    "historicalCandles": historical_candles,
                }
            )

        if preview_cache_key:
            self._store_match_preview_cache(preview_cache_key, matched_window_ids, response_matches)

        return response_matches

    def warm_match_candidate_snapshot(self, timeframes=None, window_sizes=None):
        """Load stock match candidates from noobtrade-db into a crypto-style in-memory snapshot."""
        warmed = []
        for timeframe in (timeframes or ("daily",)):
            for window_size in (window_sizes or (30,)):
                snapshot = self._get_match_candidate_snapshot(timeframe, window_size)
                warmed.append({
                    "timeframe": timeframe,
                    "windowSize": window_size,
                    "windows": len(snapshot or []),
                })
        return warmed

    def _candidate_windows_from_snapshot(self, current_window, selected_indicators):
        snapshot = self._get_match_candidate_snapshot(
            getattr(current_window, "timeframe", None),
            getattr(current_window, "window_size", None),
        )

        if snapshot is None:
            return None

        end_date = getattr(current_window, "end_date", None)
        current_id = getattr(current_window, "id", None)
        candidates = [
            window for window in snapshot
            if (
                (current_id is None or window.id != current_id)
                and (end_date is None or window.end_date < end_date)
            )
        ]

        if len(candidates) <= self.MATCH_CANDIDATE_POOL_SIZE:
            return candidates

        return heapq.nsmallest(
            self.MATCH_CANDIDATE_POOL_SIZE,
            candidates,
            key=lambda window: self._candidate_distance_value(current_window, window, selected_indicators),
        )

    def _get_match_candidate_snapshot(self, timeframe, window_size):
        if not timeframe or not window_size:
            return None

        cache_key = (
            str(timeframe),
            int(window_size),
            tuple(self.MATCH_SCORING_SYMBOLS or ()),
        )
        with self.MATCH_CANDIDATE_SNAPSHOT_LOCK:
            cached = self.MATCH_CANDIDATE_SNAPSHOT.get(cache_key)
            if cached is not None:
                return cached

            query = db.session.query(
                PatternWindow.id,
                PatternWindow.symbol_id,
                PatternWindow.timeframe,
                PatternWindow.window_size,
                PatternWindow.start_date,
                PatternWindow.end_date,
                PatternWindow.return_pct,
                PatternWindow.avg_return,
                PatternWindow.max_drawdown,
                PatternWindow.volatility,
                PatternWindow.probability_score,
                PatternWindow.ma_slope,
                PatternWindow.ema_slope,
                PatternWindow.macd_trend,
                PatternWindow.rsi_avg,
                PatternWindow.rsi_min,
                PatternWindow.rsi_max,
                PatternWindow.volume_change_ratio,
                PatternWindow.feature_vector,
            ).filter(
                PatternWindow.timeframe == timeframe,
                PatternWindow.window_size == int(window_size),
            )

            if self.MATCH_SCORING_SYMBOLS:
                query = query.join(
                    Symbol,
                    Symbol.id == PatternWindow.symbol_id,
                ).filter(Symbol.symbol.in_(self.MATCH_SCORING_SYMBOLS))

            rows = query.order_by(
                PatternWindow.end_date.desc(),
                PatternWindow.id.desc(),
            ).limit(self.MATCH_CANDIDATE_POOL_SIZE).all()

            snapshot = [
                SimpleNamespace(
                    id=row.id,
                    symbol_id=row.symbol_id,
                    timeframe=row.timeframe,
                    window_size=row.window_size,
                    start_date=row.start_date,
                    end_date=row.end_date,
                    return_pct=row.return_pct,
                    avg_return=row.avg_return,
                    max_drawdown=row.max_drawdown,
                    volatility=row.volatility,
                    probability_score=row.probability_score,
                    ma_slope=row.ma_slope,
                    ema_slope=row.ema_slope,
                    macd_trend=row.macd_trend,
                    rsi_avg=row.rsi_avg,
                    rsi_min=row.rsi_min,
                    rsi_max=row.rsi_max,
                    volume_change_ratio=row.volume_change_ratio,
                    feature_vector=row.feature_vector or {},
                )
                for row in rows
            ]
            self._hydrate_snapshot_forward_extremes(snapshot)

            self.MATCH_CANDIDATE_SNAPSHOT[cache_key] = snapshot
            return snapshot

    def _hydrate_snapshot_forward_extremes(self, snapshot):
        """Bulk-fill missing 5-day outcomes so scoring never falls into per-window queries."""
        missing = [
            window for window in (snapshot or [])
            if not self._has_cached_forward_extremes(window, trading_days=5)
        ]
        if not missing:
            return

        symbol_ids = sorted({window.symbol_id for window in missing if window.symbol_id is not None})
        end_dates = [window.end_date for window in missing if window.end_date is not None]
        if not symbol_ids or not end_dates:
            return

        price_rows = db.session.query(
            DailyPrice.symbol_id,
            DailyPrice.trade_date,
            DailyPrice.close,
            DailyPrice.high,
            DailyPrice.low,
        ).filter(
            DailyPrice.symbol_id.in_(symbol_ids),
            DailyPrice.trade_date >= min(end_dates),
            DailyPrice.trade_date <= max(end_dates) + timedelta(days=21),
        ).order_by(
            DailyPrice.symbol_id.asc(),
            DailyPrice.trade_date.asc(),
        ).all()

        rows_by_symbol = {}
        for row in price_rows:
            rows_by_symbol.setdefault(row.symbol_id, []).append(row)

        dates_by_symbol = {
            symbol_id: [row.trade_date for row in rows]
            for symbol_id, rows in rows_by_symbol.items()
        }
        rows_by_symbol_date = {
            symbol_id: {row.trade_date: row for row in rows}
            for symbol_id, rows in rows_by_symbol.items()
        }

        for window in missing:
            symbol_rows = rows_by_symbol.get(window.symbol_id) or []
            symbol_dates = dates_by_symbol.get(window.symbol_id) or []
            end_row = (rows_by_symbol_date.get(window.symbol_id) or {}).get(window.end_date)
            if end_row is None or end_row.close in (None, 0):
                continue

            future_start = bisect_right(symbol_dates, window.end_date)
            future_rows = symbol_rows[future_start:future_start + 5]
            if len(future_rows) < 5:
                continue

            future_high = max((float(row.high) for row in future_rows if row.high is not None), default=None)
            future_low = min((float(row.low) for row in future_rows if row.low is not None), default=None)
            if future_high is None or future_low is None:
                continue

            base_close = float(end_row.close)
            feature_vector = deepcopy(window.feature_vector or {})
            forward_extremes = dict(feature_vector.get("forwardExtremes") or {})
            forward_extremes["5d"] = {
                "maxUpPct": round(((future_high - base_close) / base_close) * 100, 6),
                "maxDownPct": round(((future_low - base_close) / base_close) * 100, 6),
                "targetPrice": round(future_high, 6),
                "riskPrice": round(future_low, 6),
            }
            feature_vector["forwardExtremes"] = forward_extremes
            window.feature_vector = feature_vector

    def _has_cached_forward_extremes(self, window_record, trading_days=5):
        feature_vector = getattr(window_record, "feature_vector", None) or {}
        cached_value = (feature_vector.get("forwardExtremes") or {}).get(f"{trading_days}d")
        return isinstance(cached_value, dict) and any(value is not None for value in cached_value.values())

    def _candidate_distance_value(self, current_window, candidate_window, selected_indicators):
        selected = set(self.quant_scoring_service.normalize_indicator_names(selected_indicators))

        def diff(attribute_name, current_value, weight=1.0):
            current_number = self._to_float(current_value)
            candidate_number = self._to_float(getattr(candidate_window, attribute_name, None))
            if current_number is None:
                current_number = 0.0
            if candidate_number is None:
                candidate_number = 0.0
            return abs(candidate_number - current_number) * weight

        distance = (
            diff("return_pct", getattr(current_window, "return_pct", None), 0.35)
            + diff("max_drawdown", getattr(current_window, "max_drawdown", None), 0.35)
            + diff("volatility", getattr(current_window, "volatility", None), 0.2)
            + diff("probability_score", getattr(current_window, "probability_score", None), 0.15)
        )

        if "MA" in selected:
            distance += diff("ma_slope", getattr(current_window, "ma_slope", None), 2.5)
        if "EMA" in selected:
            distance += diff("ema_slope", getattr(current_window, "ema_slope", None), 2.5)
        if "MACD" in selected:
            distance += diff("macd_trend", getattr(current_window, "macd_trend", None), 4.0)
        if "BOLL" in selected:
            distance += diff("volatility", getattr(current_window, "volatility", None), 2.0)
        if "RSI" in selected:
            distance += diff("rsi_avg", getattr(current_window, "rsi_avg", None), 1.8)
            distance += diff("rsi_min", getattr(current_window, "rsi_min", None), 0.8)
            distance += diff("rsi_max", getattr(current_window, "rsi_max", None), 0.8)
        if "VOL" in selected:
            distance += diff("volume_change_ratio", getattr(current_window, "volume_change_ratio", None), 2.0)

        return distance

    def _match_preview_cache_key(self, current_window, selected_indicators, scoring_profile=None):
        feature_vector = getattr(current_window, "feature_vector", {}) or {}
        normalized_indicators = tuple(self.quant_scoring_service.normalize_indicator_names(selected_indicators))

        def normalize_number(value):
            parsed = self._to_float(value)
            if parsed is None:
                return None
            return round(parsed, 6)

        feature_items = tuple(
            sorted(
                (str(key), normalize_number(value))
                for key, value in feature_vector.items()
                if normalize_number(value) is not None
            )
        )
        end_date = getattr(current_window, "end_date", None)
        if hasattr(end_date, "isoformat"):
            end_date = end_date.isoformat()

        return repr(
            (
                getattr(current_window, "timeframe", None),
                getattr(current_window, "window_size", None),
                end_date,
                normalize_number(getattr(current_window, "return_pct", None)),
                normalized_indicators,
                str(scoring_profile or "default"),
                feature_items,
            )
        )

    def _get_cached_match_preview(self, cache_key):
        if not cache_key:
            return None

        with self.MATCH_PREVIEW_CACHE_LOCK:
            cached = self.MATCH_PREVIEW_CACHE.get(cache_key)
            if cached and cached.get("expires_at", 0) > time.time():
                return deepcopy(cached)
            if cached:
                self.MATCH_PREVIEW_CACHE.pop(cache_key, None)
        return None

    def _store_match_preview_cache(self, cache_key, window_ids, matches):
        if not cache_key:
            return

        with self.MATCH_PREVIEW_CACHE_LOCK:
            if len(self.MATCH_PREVIEW_CACHE) >= self.MATCH_PREVIEW_CACHE_MAX_ENTRIES:
                oldest_key = min(
                    self.MATCH_PREVIEW_CACHE,
                    key=lambda key: self.MATCH_PREVIEW_CACHE[key].get("stored_at", 0),
                )
                self.MATCH_PREVIEW_CACHE.pop(oldest_key, None)

            now = time.time()
            self.MATCH_PREVIEW_CACHE[cache_key] = {
                "stored_at": now,
                "expires_at": now + self.MATCH_PREVIEW_CACHE_TTL_SECONDS,
                "window_ids": list(window_ids or []),
                "matches": deepcopy(matches or []),
            }

    def _hydrate_cached_match_preview(self, cached_preview, include_historical_candles):
        matches = deepcopy(cached_preview.get("matches") or [])
        if not include_historical_candles:
            for match in matches:
                match["historicalCandles"] = []
            return matches

        needs_candles = any(not match.get("historicalCandles") for match in matches)
        window_ids = cached_preview.get("window_ids") or []
        if not needs_candles or not window_ids:
            return matches

        window_records = PatternWindow.query.filter(PatternWindow.id.in_(window_ids)).all()
        window_lookup = {window.id: window for window in window_records}
        ordered_windows = [window_lookup[window_id] for window_id in window_ids if window_id in window_lookup]
        candle_lookup = self._build_match_candles_map(ordered_windows)

        for match, window_id in zip(matches, window_ids):
            match["historicalCandles"] = candle_lookup.get(window_id, [])

        return matches

    def _build_match_candles_map(self, window_records):
        if not window_records:
            return {}

        valid_windows = [
            window for window in window_records
            if window.symbol_id is not None and window.start_date is not None and window.end_date is not None
        ]

        if not valid_windows:
            return {}

        window_filters = [
            and_(
                DailyPrice.symbol_id == window.symbol_id,
                DailyPrice.trade_date >= window.start_date,
                DailyPrice.trade_date <= window.end_date,
            )
            for window in valid_windows
        ]

        price_records = DailyPrice.query.filter(
            or_(*window_filters),
        ).order_by(
            DailyPrice.symbol_id.asc(),
            DailyPrice.trade_date.asc(),
        ).all()

        records_by_symbol = {}
        for record in price_records:
            records_by_symbol.setdefault(record.symbol_id, []).append(record)

        candle_lookup = {}
        for window in valid_windows:
            candle_lookup[window.id] = self._serialize_match_candles(
                window,
                records_by_symbol.get(window.symbol_id, []),
            )

        return candle_lookup

    def _candidate_window_ids(self, current_window, selected_indicators):
        base_query = PatternWindow.query.with_entities(PatternWindow.id).filter(
            PatternWindow.timeframe == current_window.timeframe,
            PatternWindow.window_size == current_window.window_size,
        )

        if self.MATCH_SCORING_SYMBOLS:
            base_query = base_query.join(
                Symbol,
                Symbol.id == PatternWindow.symbol_id,
            ).filter(Symbol.symbol.in_(self.MATCH_SCORING_SYMBOLS))

        if getattr(current_window, "id", None) is not None:
            base_query = base_query.filter(PatternWindow.id != current_window.id)

        if getattr(current_window, "end_date", None) is not None:
            base_query = base_query.filter(PatternWindow.end_date < current_window.end_date)

        rough_distance = self._build_candidate_distance_expression(current_window, selected_indicators)

        rows = base_query.order_by(
            rough_distance.asc(),
            PatternWindow.end_date.desc(),
        ).limit(self.MATCH_CANDIDATE_POOL_SIZE).all()

        return [row.id for row in rows]

    def _build_candidate_distance_expression(self, current_window, selected_indicators):
        selected = set(self.quant_scoring_service.normalize_indicator_names(selected_indicators))
        zero = literal(0.0)

        def diff(column_name, current_value, weight=1.0):
            numeric_value = self._to_float(current_value)
            if numeric_value is None:
                numeric_value = 0.0
            return db.func.abs(db.func.coalesce(getattr(PatternWindow, column_name), 0.0) - numeric_value) * weight

        distance_terms = [
            diff("return_pct", getattr(current_window, "return_pct", None), 0.35),
            diff("max_drawdown", getattr(current_window, "max_drawdown", None), 0.35),
            diff("volatility", getattr(current_window, "volatility", None), 0.2),
            diff("probability_score", getattr(current_window, "probability_score", None), 0.15),
        ]

        if "MA" in selected:
            distance_terms.append(diff("ma_slope", getattr(current_window, "ma_slope", None), 2.5))
        if "EMA" in selected:
            distance_terms.append(diff("ema_slope", getattr(current_window, "ema_slope", None), 2.5))
        if "MACD" in selected:
            distance_terms.append(diff("macd_trend", getattr(current_window, "macd_trend", None), 4.0))
        if "BOLL" in selected:
            distance_terms.append(diff("volatility", getattr(current_window, "volatility", None), 2.0))
        if "RSI" in selected:
            distance_terms.append(diff("rsi_avg", getattr(current_window, "rsi_avg", None), 1.8))
            distance_terms.append(diff("rsi_min", getattr(current_window, "rsi_min", None), 0.8))
            distance_terms.append(diff("rsi_max", getattr(current_window, "rsi_max", None), 0.8))
        if "VOL" in selected:
            distance_terms.append(diff("volume_change_ratio", getattr(current_window, "volume_change_ratio", None), 2.0))

        rough_distance = zero
        for term in distance_terms:
            rough_distance = rough_distance + term

        return rough_distance
    
    def _apply_match_results_to_response(self, response_data, matched_patterns, scoring_profile=None):
        pattern_analysis = response_data["patternAnalysis"]
        pattern_analysis["matchedHistoricalPatterns"] = matched_patterns
        pattern_analysis["matchedPatternsCount"] = len(matched_patterns)
        selected_indicators = response_data.get("request", {}).get("indicators", [])
        probability_summary = self._build_future_probability_summary(
            matched_patterns,
            selected_indicators,
            scoring_profile=scoring_profile,
        )
    
        pattern_analysis["probabilityOfIncrease"] = probability_summary["probability_percent"]
        pattern_analysis["probabilityOfDecrease"] = probability_summary["probability_of_decrease"]
        pattern_analysis["quantConfidence"] = probability_summary["historical_confidence"]
        pattern_analysis["signalClassification"] = probability_summary["signal"]
        pattern_analysis["baseHistoricalProbability"] = probability_summary["base_prob"]
        pattern_analysis["weightPenalty"] = probability_summary["weight_penalty"]
        pattern_analysis["fitRatio"] = probability_summary["fit_ratio"]
        pattern_analysis["futureFiveDayProbabilities"] = probability_summary["future_five_day_probabilities"]
        pattern_analysis["recommendedSellDate"] = probability_summary["historical_target_date"]
        pattern_analysis["recommendedSellPrice"] = probability_summary["historical_target_price"]
        pattern_analysis["stopLossPrice"] = probability_summary["historical_risk_line"]
    
        if probability_summary["average_return"] is not None:
            pattern_analysis["avgReturn"] = probability_summary["average_return"]
        if probability_summary["average_drawdown"] is not None:
            pattern_analysis["maxDrawdown"] = probability_summary["average_drawdown"]
    
        pattern_analysis["highFitHistoricalPaths"] = [
            {
                "label": match["patternName"],
                "fitScore": match["matchScore"],
                "status": f"{match['symbol']} ended on {match['date']} | +5D hi {self._format_percent(match.get('futureReturn5d'))} | -5D lo {self._format_percent(match.get('futureDrawdown5d'))}",
            }
            for match in matched_patterns
        ]
    
    def _build_future_probability_summary(self, matched_patterns, selected_indicators, scoring_profile=None):
        usable_matches = [
            match for match in matched_patterns
            if isinstance(match.get("futureStats5d"), dict)
        ]
    
        if not usable_matches:
            return {
                "probability_percent": 0.0,
                "probability_of_decrease": 0.0,
                "fit_ratio": 0.0,
                "base_prob": 0.0,
                "weight_penalty": 1.0,
                "signal": "Bullish Bias",
                "average_return": None,
                "average_drawdown": None,
                "historical_confidence": 0.0,
                "historical_target_price": None,
                "historical_risk_line": None,
                "historical_target_date": "Within 5 trading days",
                "future_five_day_probabilities": {"up": [], "down": []},
            }
    
        sample_count = len(usable_matches)
        thresholds = (1, 5, 10)
        normalized_matches = []

        for match in usable_matches:
            future_stats = dict(match.get("futureStats5d") or {})
            max_up_pct = future_stats.get("maxUpPct")
            max_down_pct = future_stats.get("maxDownPct")
            target_price = future_stats.get("targetPrice")
            risk_price = future_stats.get("riskPrice")

            if max_up_pct is None:
                max_up_pct = match.get("futureReturn5d")
            if max_down_pct is None:
                max_down_pct = match.get("futureDrawdown5d")

            normalized_matches.append(
                {
                    **match,
                    "futureStats5d": {
                        "maxUpPct": max_up_pct,
                        "maxDownPct": max_down_pct,
                        "targetPrice": target_price,
                        "riskPrice": risk_price,
                    },
                }
            )

        usable_matches = normalized_matches
        upside_actionable = [
            match for match in usable_matches
            if (match.get("futureStats5d", {}).get("maxUpPct") or 0) >= 0.5
        ]
        downside_actionable = [
            match for match in usable_matches
            if (match.get("futureStats5d", {}).get("maxDownPct") or 0) <= -0.5
        ]
    
        up_probabilities = [
            {
                "threshold": threshold,
                "probability": round(
                    sum(1 for match in usable_matches if (match.get("futureStats5d", {}).get("maxUpPct") or 0) >= threshold) / sample_count * 100,
                    2,
                ),
            }
            for threshold in thresholds
        ]
        down_probabilities = [
            {
                "threshold": threshold,
                "probability": round(
                    sum(1 for match in usable_matches if (match.get("futureStats5d", {}).get("maxDownPct") or 0) <= -threshold) / sample_count * 100,
                    2,
                ),
            }
            for threshold in thresholds
        ]
    
        fit_ratio = round(
            mean(match.get("quantSelectedPercent", 0) or 0 for match in usable_matches) / 100,
            4,
        )
        total_weight = self.quant_scoring_service.selection_weight_for_profile(
            selected_indicators,
            scoring_profile=scoring_profile,
        )
        full_weight_sum = self.quant_scoring_service.full_weight_sum_for_profile(scoring_profile=scoring_profile)
        weight_ratio = (total_weight / full_weight_sum) if full_weight_sum else 0.0
        weight_penalty = self._light_probability_penalty(weight_ratio)
        up_probabilities = [
            {
                **item,
                "probability": round(item["probability"] * weight_penalty, 2),
            }
            for item in up_probabilities
        ]
        down_probabilities = [
            {
                **item,
                "probability": round(item["probability"] * weight_penalty, 2),
            }
            for item in down_probabilities
        ]
        primary_up_probability = up_probabilities[0]["probability"] if up_probabilities else 0.0
        primary_down_probability = down_probabilities[0]["probability"] if down_probabilities else 0.0
    
        signal = "Bullish Bias" if primary_up_probability >= primary_down_probability else "Bearish Bias"
        average_return = round(
            mean(match.get("futureStats5d", {}).get("maxUpPct") or 0 for match in upside_actionable),
            4,
        ) if upside_actionable else None
        average_drawdown = round(
            mean(match.get("futureStats5d", {}).get("maxDownPct") or 0 for match in downside_actionable),
            4,
        ) if downside_actionable else None
        historical_target_price = round(
            mean(match.get("futureStats5d", {}).get("targetPrice") or 0 for match in upside_actionable),
            4,
        ) if upside_actionable else None
        historical_risk_line = round(
            mean(match.get("futureStats5d", {}).get("riskPrice") or 0 for match in downside_actionable),
            4,
        ) if downside_actionable else None
    
        return {
            "probability_percent": primary_up_probability,
            "probability_of_decrease": primary_down_probability,
            "fit_ratio": fit_ratio,
            "base_prob": round(sum(1 for match in usable_matches if match.get("isFutureBullish")) / sample_count, 4),
            "weight_penalty": round(weight_penalty, 4),
            "signal": signal,
            "average_return": average_return,
            "average_drawdown": average_drawdown,
            "historical_confidence": round(fit_ratio, 2),
            "historical_target_price": historical_target_price,
            "historical_risk_line": historical_risk_line,
            "historical_target_date": "Within 5 trading days",
            "future_five_day_probabilities": {
                "up": up_probabilities,
                "down": down_probabilities,
            },
        }

    def _light_probability_penalty(self, weight_ratio):
        if weight_ratio <= 0:
            return 0.88

        # Keep high-weight bundles close to the raw history stats while still
        # softly discounting very light selections.
        return min(1.0, round(0.88 + (0.12 * (weight_ratio ** 0.5)), 6))
    
    def _select_match_bundles(self, ranked_matches):
        if not ranked_matches:
            return []
    
        high_fit_matches = [
            item for item in ranked_matches
            if item[1]["selected_score_percent"] >= self.HIGH_FIT_THRESHOLD
        ]
    
        selected_matches = high_fit_matches[: self.MATCH_TARGET]
    
        if len(selected_matches) >= self.MATCH_TARGET:
            return selected_matches
    
        selected_ids = {candidate.id for candidate, _ in selected_matches}
    
        for candidate, score in ranked_matches:
            if candidate.id in selected_ids:
                continue
    
            selected_matches.append((candidate, score))
    
            if len(selected_matches) >= self.MATCH_TARGET:
                break
    
        return selected_matches
    
    def _is_cache_ready(self, symbol_id, prepared_candles, timeframe, window_size):
        if not prepared_candles:
            return False
    
        latest_trade_date = prepared_candles[-1]["trade_date"]
        group_size = self.TIMEFRAME_GROUP_SIZES.get(timeframe, 1)
        grouped_candles = self._group_prepared_candles(prepared_candles, group_size)
    
        if len(grouped_candles) < window_size:
            return False
    
        expected_window_end_date = grouped_candles[-1]["trade_date"]
        latest_cached_price_date = db.session.query(
            db.func.max(DailyPrice.trade_date)
        ).filter(
            DailyPrice.symbol_id == symbol_id,
        ).scalar()
    
        if latest_cached_price_date != latest_trade_date:
            return False
    
        latest_indicator_date = db.session.query(
            db.func.max(DailyIndicator.trade_date)
        ).filter(
            DailyIndicator.symbol_id == symbol_id,
        ).scalar()
    
        if latest_indicator_date != latest_trade_date:
            return False
    
        current_window = self._find_current_window(symbol_id, timeframe, window_size)
    
        if current_window is None or current_window.end_date != expected_window_end_date:
            return False
    
        cached_candidate_count = PatternWindow.query.filter(
            PatternWindow.symbol_id == symbol_id,
            PatternWindow.timeframe == timeframe,
            PatternWindow.window_size == window_size,
            PatternWindow.end_date < expected_window_end_date,
        ).count()
    
        return cached_candidate_count > 0
    
    def _empty_forward_stat(self):
        return {
            "maxUpPct": None,
            "maxDownPct": None,
            "targetPrice": None,
            "riskPrice": None,
        }
    
    def _build_forward_stats_lookup(self, prepared_candles):
        trade_dates = [candle["trade_date"] for candle in prepared_candles]
        lookup = {}
    
        for index, trade_date in enumerate(trade_dates):
            base_close = prepared_candles[index]["close"]
    
            if base_close in (None, 0):
                lookup[trade_date] = {
                    "5d": self._empty_forward_stat(),
                    "10d": self._empty_forward_stat(),
                    "20d": self._empty_forward_stat(),
                }
                continue
    
            forward_stats = {}
    
            for trading_days in (5, 10, 20):
                target_index = index + trading_days
    
                if target_index >= len(trade_dates):
                    forward_stats[f"{trading_days}d"] = self._empty_forward_stat()
                    continue
    
                future_window = prepared_candles[index + 1: target_index + 1]
                future_high = max(
                    (candle["high"] for candle in future_window if candle.get("high") is not None),
                    default=None,
                )
                future_low = min(
                    (candle["low"] for candle in future_window if candle.get("low") is not None),
                    default=None,
                )
    
                if future_high is None or future_low is None:
                    forward_stats[f"{trading_days}d"] = self._empty_forward_stat()
                    continue
    
                forward_stats[f"{trading_days}d"] = {
                    "maxUpPct": round(((future_high - base_close) / base_close) * 100, 6),
                    "maxDownPct": round(((future_low - base_close) / base_close) * 100, 6),
                    "targetPrice": round(float(future_high), 6),
                    "riskPrice": round(float(future_low), 6),
                }
    
            lookup[trade_date] = forward_stats
    
        return lookup
    
    def _cached_forward_return(self, window_record, trading_days=5):
        return self._cached_forward_extremes(window_record, trading_days=trading_days).get("maxUpPct")
    
    def _cached_forward_extremes(self, window_record, trading_days=5):
        feature_vector = window_record.feature_vector or {}
        forward_extremes = feature_vector.get("forwardExtremes", {})
        cached_value = forward_extremes.get(f"{trading_days}d")
    
        if isinstance(cached_value, dict) and any(value is not None for value in cached_value.values()):
            return {
                "maxUpPct": self._to_response_number(cached_value.get("maxUpPct")),
                "maxDownPct": self._to_response_number(cached_value.get("maxDownPct")),
                "targetPrice": self._to_response_number(cached_value.get("targetPrice")),
                "riskPrice": self._to_response_number(cached_value.get("riskPrice")),
            }
    
        return self._forward_extremes_for_window(window_record, trading_days=trading_days)
    
    def _build_match_candles(self, window_record):
        group_size = self.TIMEFRAME_GROUP_SIZES.get(window_record.timeframe, 1)
        price_records = DailyPrice.query.filter(
            DailyPrice.symbol_id == window_record.symbol_id,
            DailyPrice.trade_date >= window_record.start_date,
            DailyPrice.trade_date <= window_record.end_date,
        ).order_by(DailyPrice.trade_date.asc()).all()

        return self._serialize_match_candles(window_record, price_records, group_size=group_size)

    def _serialize_match_candles(self, window_record, price_records, group_size=None):
        if not price_records:
            return []

        ordered_records = [
            record for record in price_records
            if (
                record.trade_date is not None
                and window_record.start_date is not None
                and window_record.end_date is not None
                and window_record.start_date <= record.trade_date <= window_record.end_date
            )
        ]

        if not ordered_records:
            return []

        group_size = group_size or self.TIMEFRAME_GROUP_SIZES.get(window_record.timeframe, 1)
        prepared_candles = [
            {
                "trade_date": record.trade_date,
                "open": self._to_float(record.open),
                "high": self._to_float(record.high),
                "low": self._to_float(record.low),
                "close": self._to_float(record.close),
                "volume": self._to_float(record.volume or 0),
            }
            for record in ordered_records
            if record.trade_date is not None
        ]
    
        grouped_candles = self._group_prepared_candles(prepared_candles, group_size)
        window_candles = grouped_candles[-window_record.window_size:]
    
        return [
            {
                "date": candle["trade_date"].isoformat(),
                "open": self._to_response_number(candle["open"]),
                "high": self._to_response_number(candle["high"]),
                "low": self._to_response_number(candle["low"]),
                "close": self._to_response_number(candle["close"]),
                "volume": int(candle["volume"] or 0),
            }
            for candle in window_candles
        ]
    
    def _forward_extremes_for_window(self, window_record, trading_days=5):
        end_price_record = DailyPrice.query.filter_by(
            symbol_id=window_record.symbol_id,
            trade_date=window_record.end_date,
        ).first()
    
        if end_price_record is None or end_price_record.close in (None, 0):
            return self._empty_forward_stat()
    
        future_prices = DailyPrice.query.filter(
            DailyPrice.symbol_id == window_record.symbol_id,
            DailyPrice.trade_date > window_record.end_date,
        ).order_by(DailyPrice.trade_date.asc()).limit(trading_days).all()
    
        if len(future_prices) < trading_days:
            return self._empty_forward_stat()
    
        future_high = max((float(price.high) for price in future_prices if price.high is not None), default=None)
        future_low = min((float(price.low) for price in future_prices if price.low is not None), default=None)
        base_close = float(end_price_record.close)
    
        if base_close == 0 or future_high is None or future_low is None:
            return self._empty_forward_stat()
    
        return {
            "maxUpPct": round(((future_high - base_close) / base_close) * 100, 6),
            "maxDownPct": round(((future_low - base_close) / base_close) * 100, 6),
            "targetPrice": round(future_high, 6),
            "riskPrice": round(future_low, 6),
        }
    
    def _build_pattern_label(self, matched_window):
        del matched_window
        return "Historical setup"

    def _build_window_summary(self, candles):
        closes = [item["close"] for item in candles]
        highs = [item["high"] for item in candles]
        lows = [item["low"] for item in candles]
        volumes = [item["volume"] for item in candles]
        returns = self._percent_returns(closes)
        ma_short = self._simple_moving_average(closes, min(5, len(closes)))
        ma_long = self._simple_moving_average(closes, min(20, len(closes)))
        ema_short = self._exponential_moving_average(closes, min(5, len(closes)))
        ema_long = self._exponential_moving_average(closes, min(20, len(closes)))
        macd_line = self._macd_line(closes)
        macd_signal = self._macd_signal(closes)
        rsi_values = self._rolling_rsi_values(closes, 14)
        boll_values = self._bollinger_bands(closes, min(20, len(closes)))
        kdj_values = self._kdj(highs, lows, closes, period=min(9, len(closes)))
        obv_value = self._on_balance_volume(closes, volumes)
        oi_value = self._open_interest_proxy(closes, volumes)

        return {
            "return_pct": self._window_return_pct(closes),
            "avg_return": round(mean(returns), 6) if returns else None,
            "max_drawdown": self._max_drawdown_from_closes(closes),
            "volatility": round(pstdev(returns), 6) if len(returns) > 1 else None,
            "probability_score": round((len([value for value in returns if value > 0]) / len(returns)) * 100, 6) if returns else None,
            "ma_slope": self._subtract_or_none(ma_short, ma_long),
            "ema_slope": self._subtract_or_none(ema_short, ema_long),
            "macd_trend": self._subtract_or_none(macd_line, macd_signal),
            "rsi_avg": round(mean(rsi_values), 6) if rsi_values else None,
            "rsi_min": round(min(rsi_values), 6) if rsi_values else None,
            "rsi_max": round(max(rsi_values), 6) if rsi_values else None,
            "volume_change_ratio": self._volume_change_ratio(volumes),
            "feature_vector": {
                "close_start": closes[0],
                "close_end": closes[-1],
                "close_high": max(highs),
                "close_low": min(lows),
                "normalized_close_path": self._normalized_close_path(closes),
                "volume_avg": round(mean(volumes), 6) if volumes else None,
                "returns_tail": returns[-5:],
                "selectedIndicators": ["MA", "EMA", "MACD", "BOLL", "RSI", "VOL", "KDJ", "OI", "OBV"],
                "indicators": {
                    "ma": ma_long,
                    "ema": self._exponential_moving_average(closes, min(12, len(closes))),
                    "macd": macd_line,
                    "boll_upper": boll_values["upper"],
                    "boll_lower": boll_values["lower"],
                    "boll_bandwidth": self._boll_bandwidth(boll_values),
                    "rsi": self._relative_strength_index(closes, min(14, max(len(closes) - 1, 1))),
                    "volume_ratio": self._volume_change_ratio(volumes),
                    "kdj_k": kdj_values["k"],
                    "kdj_d": kdj_values["d"],
                    "kdj_j": kdj_values["j"],
                    "kdj_average": self._average_defined([kdj_values["k"], kdj_values["d"], kdj_values["j"]]),
                    "oi": oi_value,
                    "obv": obv_value,
                },
            },
        }

    def _normalized_close_path(self, closes):
        if not closes:
            return []

        base_close = closes[0]
        if base_close in (None, 0):
            return []

        return [
            round(((close - base_close) / base_close) * 100, 6)
            for close in closes
            if close is not None
        ]

    def _group_prepared_candles(self, candles, group_size):
        if group_size == 1:
            return candles

        grouped = []

        for index in range(0, len(candles), group_size):
            chunk = candles[index:index + group_size]

            if len(chunk) < group_size:
                continue

            grouped.append(
                {
                    "trade_date": chunk[-1]["trade_date"],
                    "open": chunk[0]["open"],
                    "high": max(item["high"] for item in chunk),
                    "low": min(item["low"] for item in chunk),
                    "close": chunk[-1]["close"],
                    "volume": sum(item["volume"] for item in chunk),
                }
            )

        return grouped

    def _prepare_candles(self, daily_candles):
        prepared = []

        for candle in daily_candles:
            trade_date = self._parse_date(candle.get("date"))

            if trade_date is None:
                continue

            prepared.append(
                {
                    "trade_date": trade_date,
                    "open": self._to_float(candle.get("open")),
                    "high": self._to_float(candle.get("high")),
                    "low": self._to_float(candle.get("low")),
                    "close": self._to_float(candle.get("close")),
                    "volume": self._to_float(candle.get("volume", 0)),
                }
            )

        return prepared

    def _simple_moving_average(self, values, period):
        if len(values) < period or period <= 0:
            return None

        return round(mean(values[-period:]), 6)

    def _exponential_moving_average(self, values, period):
        if len(values) < period or period <= 1:
            return self._simple_moving_average(values, period)

        multiplier = 2 / (period + 1)
        ema = mean(values[:period])

        for value in values[period:]:
            ema = ((value - ema) * multiplier) + ema

        return round(ema, 6)

    def _macd_line(self, closes):
        ema_12 = self._exponential_moving_average(closes, min(12, len(closes)))
        ema_26 = self._exponential_moving_average(closes, min(26, len(closes)))
        return self._subtract_or_none(ema_12, ema_26)

    def _macd_signal(self, closes):
        if len(closes) < 9:
            return None

        macd_series = []

        for end_index in range(2, len(closes) + 1):
            subset = closes[:end_index]
            macd_value = self._macd_line(subset)

            if macd_value is not None:
                macd_series.append(macd_value)

        if len(macd_series) < 9:
            return None

        return self._exponential_moving_average(macd_series, 9)

    def _relative_strength_index(self, closes, period):
        if len(closes) <= period:
            return None

        gains = []
        losses = []

        for index in range(1, len(closes)):
            change = closes[index] - closes[index - 1]
            gains.append(max(change, 0))
            losses.append(abs(min(change, 0)))

        recent_gains = gains[-period:]
        recent_losses = losses[-period:]
        average_gain = mean(recent_gains)
        average_loss = mean(recent_losses)

        if average_loss == 0:
            return 100.0

        rs = average_gain / average_loss
        return round(100 - (100 / (1 + rs)), 4)

    def _rolling_rsi_values(self, closes, period):
        values = []

        for end_index in range(period + 1, len(closes) + 1):
            rsi_value = self._relative_strength_index(closes[:end_index], period)
            if rsi_value is not None:
                values.append(rsi_value)

        return values

    def _bollinger_bands(self, closes, period):
        if len(closes) < period:
            return {"mid": None, "upper": None, "lower": None}

        window = closes[-period:]
        mid = mean(window)
        deviation = pstdev(window)

        return {
            "mid": round(mid, 6),
            "upper": round(mid + (2 * deviation), 6),
            "lower": round(mid - (2 * deviation), 6),
        }

    def _kdj(self, highs, lows, closes, period):
        if len(closes) < period:
            return {"k": None, "d": None, "j": None}

        recent_high = max(highs[-period:])
        recent_low = min(lows[-period:])
        current_close = closes[-1]

        if recent_high == recent_low:
            rsv = 50.0
        else:
            rsv = ((current_close - recent_low) / (recent_high - recent_low)) * 100

        k_value = round((2 / 3) * 50 + (1 / 3) * rsv, 4)
        d_value = round((2 / 3) * 50 + (1 / 3) * k_value, 4)
        j_value = round((3 * k_value) - (2 * d_value), 4)

        return {"k": k_value, "d": d_value, "j": j_value}

    def _on_balance_volume(self, closes, volumes):
        if not closes or not volumes:
            return None

        obv = 0.0

        for index, close in enumerate(closes):
            current_volume = volumes[index] if index < len(volumes) else 0

            if index == 0:
                continue

            previous_close = closes[index - 1]

            if close > previous_close:
                obv += current_volume
            elif close < previous_close:
                obv -= current_volume

        return round(obv, 6)

    def _open_interest_proxy(self, closes, volumes):
        if not closes or not volumes:
            return None

        running_interest = 0.0

        for index, close in enumerate(closes):
            previous_close = closes[index - 1] if index > 0 else close
            signed_flow = volumes[index] if close >= previous_close else -volumes[index]
            running_interest += signed_flow * 0.35

        return round(running_interest, 6)

    def _average_defined(self, values):
        defined_values = [value for value in values if value is not None]

        if not defined_values:
            return None

        return round(mean(defined_values), 6)

    def _boll_bandwidth(self, boll_values):
        upper = boll_values.get("upper")
        lower = boll_values.get("lower")
        mid = boll_values.get("mid")

        if upper is None or lower is None or mid in (None, 0):
            return None

        return round((upper - lower) / mid, 6)

    def _percent_returns(self, closes):
        returns = []

        for index in range(1, len(closes)):
            previous_close = closes[index - 1]
            current_close = closes[index]

            if previous_close:
                returns.append(((current_close - previous_close) / previous_close) * 100)

        return returns

    def _window_return_pct(self, closes):
        if len(closes) < 2 or not closes[0]:
            return None

        return round(((closes[-1] - closes[0]) / closes[0]) * 100, 6)

    def _max_drawdown_from_closes(self, closes):
        if not closes:
            return None

        peak = closes[0]
        max_drawdown = 0.0

        for close in closes:
            if close > peak:
                peak = close

            if peak:
                drawdown = ((close - peak) / peak) * 100
                max_drawdown = min(max_drawdown, drawdown)

        return round(max_drawdown, 6)

    def _volume_change_ratio(self, volumes):
        if len(volumes) < 2:
            return None

        trailing_window = volumes[:-1]
        baseline = mean(trailing_window) if trailing_window else 0

        if baseline == 0:
            return None

        return round(volumes[-1] / baseline, 6)

    def _subtract_or_none(self, left_value, right_value):
        if left_value is None or right_value is None:
            return None

        return round(left_value - right_value, 6)

    def _to_float(self, value):
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_response_number(self, value):
        if value is None:
            return None

        return round(float(value), 6)

    def _format_percent(self, value):
        if value is None:
            return "TBD"

        numeric_value = float(value)
        return f"{numeric_value:+.2f}%"

    def _parse_date(self, value):
        if isinstance(value, date):
            return value

        if not value:
            return None

        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except ValueError:
            return None
