import argparse
import json
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from models.market_data import DailyIndicator, DailyPrice, PatternWindow, Symbol
from services.market_data_service import MarketDataService
from services.persistence_service import PersistenceService
from services.quant_scoring_service import QuantScoringService

REPORTS_DIR = BACKEND_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

TIMEFRAME = "daily"
WINDOW_SIZE = 30
FORWARD_DAYS = 5
DEFAULT_TARGET_UP_PCT = 1.0
DEFAULT_BUY_THRESHOLD_PCT = 80.0
POSITION_SIZE_PCT = 0.05
DEFAULT_COMMISSION_PCT = 0.0
DEFAULT_SLIPPAGE_PCT = 0.0
FULL_INDICATORS = ["MA", "EMA", "MACD", "BOLL", "RSI", "VOL", "KDJ", "OI", "OBV"]
DEFAULT_SELECTED_INDICATORS = ["MACD", "BOLL", "RSI", "VOL", "KDJ", "OI", "OBV"]

BASE_TIER_MIN_NOTIONAL = 50_000.0
MID_TIER_MIN_NOTIONAL = 70_000.0
HIGH_TIER_MIN_NOTIONAL = 100_000.0
MID_TIER_PCT = 0.07
HIGH_TIER_PCT = 0.10


@dataclass
class DailyPriceRow:
    trade_date: object
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class DailyIndicatorRow:
    trade_date: object
    boll_lower: float
    macd_hist: float


def _to_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _tiered_position_notional(current_equity, available_cash, probability_of_increase):
    probability_of_increase = _to_float(probability_of_increase, 0.0)

    if probability_of_increase >= 90.0:
        min_notional = HIGH_TIER_MIN_NOTIONAL
        pct_notional = current_equity * HIGH_TIER_PCT if current_equity > 1_000_000 else min_notional
    elif probability_of_increase >= 85.0:
        min_notional = MID_TIER_MIN_NOTIONAL
        pct_notional = current_equity * MID_TIER_PCT if current_equity > 1_000_000 else min_notional
    else:
        min_notional = BASE_TIER_MIN_NOTIONAL
        pct_notional = current_equity * POSITION_SIZE_PCT if current_equity > 1_000_000 else min_notional

    return min(available_cash, max(min_notional, pct_notional) if current_equity > 1_000_000 else min_notional)


def _load_symbol_universe():
    preferred_order = MarketDataService.TOP_50_SYMBOLS
    symbols = Symbol.query.filter(Symbol.symbol.in_(preferred_order)).all()
    lookup = {symbol.symbol: symbol for symbol in symbols}
    ordered_symbols = [lookup[symbol] for symbol in preferred_order if symbol in lookup]
    return ordered_symbols


def _load_price_history(symbol_ids):
    records = (
        DailyPrice.query
        .filter(DailyPrice.symbol_id.in_(symbol_ids))
        .order_by(DailyPrice.symbol_id.asc(), DailyPrice.trade_date.asc())
        .all()
    )

    price_history = {}
    date_index = {}

    for record in records:
        symbol_prices = price_history.setdefault(record.symbol_id, [])
        symbol_date_index = date_index.setdefault(record.symbol_id, {})
        symbol_date_index[record.trade_date] = len(symbol_prices)
        symbol_prices.append(
            DailyPriceRow(
                trade_date=record.trade_date,
                open=_to_float(record.open),
                high=_to_float(record.high),
                low=_to_float(record.low),
                close=_to_float(record.close),
                volume=_to_float(record.volume),
            )
        )

    return price_history, date_index


def _load_daily_windows(symbol_ids):
    return (
        PatternWindow.query
        .filter(
            PatternWindow.symbol_id.in_(symbol_ids),
            PatternWindow.timeframe == TIMEFRAME,
            PatternWindow.window_size == WINDOW_SIZE,
        )
        .order_by(PatternWindow.end_date.asc(), PatternWindow.id.asc())
        .all()
    )


def _load_indicator_history(symbol_ids):
    records = (
        DailyIndicator.query
        .filter(DailyIndicator.symbol_id.in_(symbol_ids))
        .order_by(DailyIndicator.symbol_id.asc(), DailyIndicator.trade_date.asc())
        .all()
    )

    indicator_history = {}
    indicator_index = {}

    for record in records:
        symbol_indicators = indicator_history.setdefault(record.symbol_id, [])
        symbol_date_index = indicator_index.setdefault(record.symbol_id, {})
        symbol_date_index[record.trade_date] = len(symbol_indicators)
        symbol_indicators.append(
            DailyIndicatorRow(
                trade_date=record.trade_date,
                boll_lower=_to_float(record.boll_lower, None),
                macd_hist=_to_float(record.macd_hist, None),
            )
        )

    return indicator_history, indicator_index


def _passes_boll_lower_touch_filter(symbol_id, anchor_date, price_history, price_date_index, indicator_history, indicator_date_index):
    price_lookup = price_date_index.get(symbol_id, {})
    indicator_lookup = indicator_date_index.get(symbol_id, {})
    anchor_price_index = price_lookup.get(anchor_date)
    anchor_indicator_index = indicator_lookup.get(anchor_date)

    if anchor_price_index is None or anchor_indicator_index is None:
        return False

    price_row = price_history.get(symbol_id, [])[anchor_price_index]
    indicator_row = indicator_history.get(symbol_id, [])[anchor_indicator_index]

    if indicator_row.boll_lower is None:
        return False

    return (
        price_row.low <= indicator_row.boll_lower
        or price_row.close <= indicator_row.boll_lower
    )


def _passes_macd_histogram_strength_filter(symbol_id, anchor_date, price_history, price_date_index, indicator_history, indicator_date_index, required_bars):
    required_bars = max(1, int(required_bars or 0))
    price_lookup = price_date_index.get(symbol_id, {})
    indicator_lookup = indicator_date_index.get(symbol_id, {})
    anchor_price_index = price_lookup.get(anchor_date)

    if anchor_price_index is None or anchor_price_index < required_bars - 1:
        return False

    hist_values = []

    for offset in range(required_bars - 1, -1, -1):
        row = price_history.get(symbol_id, [])[anchor_price_index - offset]
        indicator_idx = indicator_lookup.get(row.trade_date)
        if indicator_idx is None:
            return False
        indicator_row = indicator_history.get(symbol_id, [])[indicator_idx]
        if indicator_row.macd_hist is None or indicator_row.macd_hist <= 0:
            return False
        hist_values.append(indicator_row.macd_hist)

    return all(current > previous for previous, current in zip(hist_values, hist_values[1:]))


def _get_forward_stats_from_window(window_record):
    feature_vector = window_record.feature_vector or {}
    forward_extremes = feature_vector.get("forwardExtremes") or {}
    stats = forward_extremes.get("5d") or {}
    return {
        "maxUpPct": _to_float(stats.get("maxUpPct"), None),
        "maxDownPct": _to_float(stats.get("maxDownPct"), None),
        "targetPrice": _to_float(stats.get("targetPrice"), None),
        "riskPrice": _to_float(stats.get("riskPrice"), None),
    }


def _build_response_match(window_record, score, symbol_lookup):
    future_stats_5d = score.get("future_stats_5d") or {}
    return {
        "patternName": f"{window_record.timeframe.upper()} {window_record.window_size}-bar setup",
        "matchScore": round(score["selected_score_percent"], 2),
        "date": window_record.end_date.isoformat(),
        "symbol": symbol_lookup.get(window_record.symbol_id, "N/A"),
        "timeframe": window_record.timeframe,
        "windowSize": window_record.window_size,
        "returnPct": _to_float(window_record.return_pct, None),
        "maxDrawdown": _to_float(window_record.max_drawdown, None),
        "isBullishHistory": score["is_bullish"],
        "futureReturn5d": future_stats_5d.get("maxUpPct"),
        "futureDrawdown5d": future_stats_5d.get("maxDownPct"),
        "isFutureBullish": score["is_future_bullish"],
        "futureStats5d": future_stats_5d,
        "quantSelectedPercent": score["selected_score_percent"],
    }


def _rank_matches_for_anchor(anchor_window, candidate_windows, selected_indicators, quant_service, persistence_service, symbol_lookup):
    ranked_matches = []

    for candidate in candidate_windows:
        score = quant_service.score_match(anchor_window, candidate, selected_indicators)
        future_stats_5d = _get_forward_stats_from_window(candidate)
        score["future_stats_5d"] = future_stats_5d
        score["future_return_5d"] = future_stats_5d.get("maxUpPct")
        score["future_drawdown_5d"] = future_stats_5d.get("maxDownPct")
        score["is_future_bullish"] = (
            score["future_return_5d"] is not None and score["future_return_5d"] >= 0.5
        )
        ranked_matches.append((candidate, score))

    ranked_matches.sort(key=lambda item: item[1]["selected_score_percent"], reverse=True)
    selected_matches = persistence_service._select_match_bundles(ranked_matches)

    return [
        _build_response_match(window_record, score, symbol_lookup)
        for window_record, score in selected_matches
    ]


def _resolve_stop_price(entry_price, probability_summary, matched_patterns):
    stop_loss_price = probability_summary.get("historical_risk_line")
    fallback_drawdowns = [
        _to_float(match.get("futureStats5d", {}).get("maxDownPct"), None)
        for match in matched_patterns
        if match.get("futureStats5d", {}).get("maxDownPct") is not None
    ]

    if stop_loss_price is None or stop_loss_price <= 0 or stop_loss_price >= entry_price:
        average_drawdown = probability_summary.get("average_drawdown")
        if average_drawdown is not None and average_drawdown < 0:
            stop_loss_price = round(entry_price * (1 + (average_drawdown / 100)), 6)

    if (stop_loss_price is None or stop_loss_price <= 0 or stop_loss_price >= entry_price) and fallback_drawdowns:
        average_fallback_drawdown = mean(fallback_drawdowns)
        if average_fallback_drawdown < 0:
            stop_loss_price = round(entry_price * (1 + (average_fallback_drawdown / 100)), 6)

    if stop_loss_price is None or stop_loss_price <= 0 or stop_loss_price >= entry_price:
        stop_loss_price = round(entry_price * 0.99, 6)

    if stop_loss_price <= 0 or stop_loss_price >= entry_price:
        return None

    return round(stop_loss_price, 6)


def _summarize_match_strength(matched_patterns):
    max_up_values = [
        _to_float(match.get("futureStats5d", {}).get("maxUpPct"), None)
        for match in matched_patterns
        if match.get("futureStats5d", {}).get("maxUpPct") is not None
    ]
    if not max_up_values:
        return {
            "avgMaxUpPct": None,
            "fivePercentUpProbability": 0.0,
            "sampleSize": 0,
        }

    five_percent_hits = sum(1 for value in max_up_values if value >= 5.0)
    return {
        "avgMaxUpPct": mean(max_up_values),
        "fivePercentUpProbability": (five_percent_hits / len(max_up_values)) * 100,
        "sampleSize": len(max_up_values),
    }


def _build_trade_signal(
    anchor_window,
    probability_summary,
    future_prices,
    matched_patterns,
    symbol,
    target_up_pct,
    fixed_stop_pct=None,
    dynamic_target_from_matches=False,
):
    entry_row = future_prices[0]
    entry_price = _to_float(entry_row.open) or _to_float(anchor_window.feature_vector.get("close_end"))

    if entry_price <= 0:
        return None

    match_strength = _summarize_match_strength(matched_patterns)
    resolved_target_up_pct = target_up_pct

    if dynamic_target_from_matches and match_strength["avgMaxUpPct"] is not None:
        resolved_target_up_pct = max(0.1, match_strength["avgMaxUpPct"] - 1.0)

    if fixed_stop_pct is not None and fixed_stop_pct > 0:
        stop_loss_price = round(entry_price * (1 - (fixed_stop_pct / 100)), 6)
    else:
        stop_loss_price = _resolve_stop_price(entry_price, probability_summary, matched_patterns)

    if stop_loss_price is None:
        return None

    target_price = round(entry_price * (1 + (resolved_target_up_pct / 100)), 6)
    price_map = {row.trade_date: row for row in future_prices[:FORWARD_DAYS]}

    return {
        "symbol": symbol,
        "anchorDate": anchor_window.end_date.isoformat(),
        "probabilityOfIncrease": round(probability_summary["probability_percent"], 4),
        "probabilityOfDecrease": round(probability_summary["probability_of_decrease"], 4),
        "historicalConfidence": round(probability_summary["historical_confidence"], 4),
        "entryDate": entry_row.trade_date,
        "entryReferencePrice": round(entry_price, 6),
        "targetPrice": target_price,
        "stopLossPrice": stop_loss_price,
        "targetUpPct": round(resolved_target_up_pct, 6),
        "matchAvgMaxUpPct": round(match_strength["avgMaxUpPct"], 6) if match_strength["avgMaxUpPct"] is not None else None,
        "matchFivePercentUpProbability": round(match_strength["fivePercentUpProbability"], 6),
        "expiryDate": future_prices[min(FORWARD_DAYS, len(future_prices)) - 1].trade_date,
        "futurePrices": future_prices[:FORWARD_DAYS],
        "priceMap": price_map,
        "matchedPatterns": matched_patterns,
    }


def _write_svg(path, content):
    path.write_text(content)


def _normalize_series(values, width, height, padding):
    if not values:
        return []

    min_value = min(values)
    max_value = max(values)
    span = max(max_value - min_value, 1e-9)
    usable_width = max(width - (padding * 2), 1)
    usable_height = max(height - (padding * 2), 1)

    points = []
    for index, value in enumerate(values):
        x = padding + (usable_width * index / max(len(values) - 1, 1))
        normalized = (value - min_value) / span
        y = height - padding - (normalized * usable_height)
        points.append((round(x, 2), round(y, 2)))

    return points


def _build_equity_curve_svg(equity_curve, summary, metadata):
    width = 1040
    height = 420
    padding = 48
    points = _normalize_series(equity_curve, width, height, padding)
    polyline_points = " ".join(f"{x},{y}" for x, y in points)
    area_points = f"{padding},{height-padding} " + polyline_points + f" {width-padding},{height-padding}"
    start_value = equity_curve[0] if equity_curve else 0.0
    end_value = equity_curve[-1] if equity_curve else 0.0

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="equityFill" x1="0%" x2="0%" y1="0%" y2="100%">
      <stop offset="0%" stop-color="rgba(37,99,235,0.28)" />
      <stop offset="100%" stop-color="rgba(37,99,235,0.04)" />
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" rx="22" fill="#f8fbff" />
  <text x="{padding}" y="36" font-size="24" font-family="Arial, sans-serif" font-weight="700" fill="#0f172a">Equity Curve</text>
  <text x="{padding}" y="64" font-size="14" font-family="Arial, sans-serif" fill="#475569">Concurrent 5%-capital allocation from a ${metadata['initialCapital']:,.0f} starting balance across {metadata['sampleCount']} sampled anchors</text>
  <line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" stroke="#cbd5e1" stroke-width="1.5" />
  <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height-padding}" stroke="#cbd5e1" stroke-width="1.5" />
  <polygon points="{area_points}" fill="url(#equityFill)" />
  <polyline points="{polyline_points}" fill="none" stroke="#2563eb" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
  <text x="{padding}" y="{height-padding+26}" font-size="13" font-family="Arial, sans-serif" fill="#475569">Start: ${start_value:,.2f}</text>
  <text x="{width-padding-190}" y="{height-padding+26}" font-size="13" font-family="Arial, sans-serif" fill="#475569">End: ${end_value:,.2f}</text>
  <text x="{width-padding-210}" y="{padding+10}" font-size="14" font-family="Arial, sans-serif" fill="#0f172a">Max drawdown: {summary['maxDrawdownPct']:.2f}%</text>
</svg>"""


def _build_exit_reason_svg(summary):
    width = 700
    height = 360
    padding = 56
    data = [
        ("Take Profit", summary["hitTargetRate"], "#16a34a"),
        ("Stop Loss", summary["stopRate"], "#dc2626"),
        ("Time Exit", summary["timeExitRate"], "#f59e0b"),
    ]
    max_value = max((value for _, value, _ in data), default=1.0) or 1.0
    bar_width = 120
    gap = 70
    start_x = 110
    baseline = height - padding

    bars = []
    labels = []
    values = []
    for index, (label, value, color) in enumerate(data):
        x = start_x + (index * (bar_width + gap))
        bar_height = 0 if max_value == 0 else ((value / max_value) * (height - (padding * 2)))
        y = baseline - bar_height
        bars.append(f'<rect x="{x}" y="{y:.2f}" width="{bar_width}" height="{bar_height:.2f}" rx="16" fill="{color}" opacity="0.88" />')
        labels.append(f'<text x="{x + (bar_width / 2)}" y="{baseline + 28}" text-anchor="middle" font-size="14" font-family="Arial, sans-serif" fill="#334155">{label}</text>')
        values.append(f'<text x="{x + (bar_width / 2)}" y="{y - 10:.2f}" text-anchor="middle" font-size="14" font-family="Arial, sans-serif" font-weight="700" fill="#0f172a">{value:.2f}%</text>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" rx="22" fill="#fffaf5" />
  <text x="{padding}" y="36" font-size="24" font-family="Arial, sans-serif" font-weight="700" fill="#0f172a">Exit Breakdown</text>
  <text x="{padding}" y="64" font-size="14" font-family="Arial, sans-serif" fill="#475569">How the strategy closed executed trades over the 5-day holding window</text>
  <line x1="{padding}" y1="{baseline}" x2="{width-padding}" y2="{baseline}" stroke="#cbd5e1" stroke-width="1.5" />
  {''.join(bars)}
  {''.join(values)}
  {''.join(labels)}
</svg>"""


def _build_kpi_svg(summary, metadata):
    width = 1040
    height = 260
    card_width = 220
    card_height = 108
    start_x = 48
    start_y = 72
    gap = 22
    cards = [
        ("Final Capital", f"${summary['finalCapital']:,.0f}", "#0f172a"),
        ("Win Rate", f"{summary['winRate']:.2f}%", "#16a34a"),
        ("Max Drawdown", f"{summary['maxDrawdownPct']:.2f}%", "#dc2626"),
        ("Avg Trade Return", f"{summary['avgTradeReturnPct']:.2f}%", "#2563eb"),
    ]

    rendered_cards = []
    for index, (label, value, accent) in enumerate(cards):
        x = start_x + (index * (card_width + gap))
        rendered_cards.append(
            f"""
            <rect x="{x}" y="{start_y}" width="{card_width}" height="{card_height}" rx="20" fill="#ffffff" stroke="#e2e8f0" />
            <text x="{x + 18}" y="{start_y + 30}" font-size="14" font-family="Arial, sans-serif" fill="#64748b">{label}</text>
            <text x="{x + 18}" y="{start_y + 72}" font-size="30" font-family="Arial, sans-serif" font-weight="700" fill="{accent}">{value}</text>
            """
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" rx="24" fill="#f8fafc" />
  <text x="48" y="38" font-size="26" font-family="Arial, sans-serif" font-weight="700" fill="#0f172a">Backtest KPI Summary</text>
  <text x="48" y="62" font-size="14" font-family="Arial, sans-serif" fill="#475569">Top-50 daily 30-bar generate backtest with {metadata['sampleCount']:,} random historical anchors and 5% capital allocation</text>
  {''.join(rendered_cards)}
</svg>"""


def _mark_to_market_equity(cash, open_positions):
    return cash + sum(position["shares"] * position["lastMarkPrice"] for position in open_positions)


def _close_position(position, exit_price, exit_reason, holding_days, commission_pct=0.0, slippage_pct=0.0):
    effective_exit_price = exit_price * (1 - (slippage_pct / 100))
    exit_notional = position["shares"] * effective_exit_price
    exit_commission = exit_notional * (commission_pct / 100)
    net_exit_cash = exit_notional - exit_commission
    pnl = net_exit_cash - position["entryCashOutlay"]
    pnl_pct = (pnl / position["entryCashOutlay"]) * 100 if position["entryCashOutlay"] else 0.0
    return {
        "symbol": position["symbol"],
        "anchorDate": position["anchorDate"],
        "probabilityOfIncrease": position["probabilityOfIncrease"],
        "probabilityOfDecrease": position["probabilityOfDecrease"],
        "historicalConfidence": position["historicalConfidence"],
        "entryDate": position["entryDate"].isoformat(),
        "entryPrice": round(position["entryPrice"], 6),
        "entryReferencePrice": round(position["entryReferencePrice"], 6),
        "entryCommission": round(position["entryCommission"], 6),
        "entryCashOutlay": round(position["entryCashOutlay"], 6),
        "targetPrice": round(position["targetPrice"], 6),
        "stopLossPrice": round(position["stopLossPrice"], 6),
        "targetUpPct": round(position.get("targetUpPct", 0.0), 6),
        "matchAvgMaxUpPct": position.get("matchAvgMaxUpPct"),
        "matchFivePercentUpProbability": position.get("matchFivePercentUpProbability"),
        "exitDate": position["currentDate"].isoformat(),
        "exitPrice": round(effective_exit_price, 6),
        "exitReferencePrice": round(exit_price, 6),
        "exitCommission": round(exit_commission, 6),
        "netExitCash": round(net_exit_cash, 6),
        "exitReason": exit_reason,
        "holdingDays": holding_days,
        "positionNotional": round(position["positionNotional"], 6),
        "shares": round(position["shares"], 6),
        "pnl": round(pnl, 6),
        "pnlPct": round(pnl_pct, 6),
    }


def _build_report_markdown(summary, trades, metadata):
    hit_target_rate = summary["hitTargetRate"]
    stop_rate = summary["stopRate"]
    time_exit_rate = summary["timeExitRate"]

    lines = [
        "# NoobTrade Top-50 Quant Backtest",
        "",
        f"Generated at: {metadata['generatedAt']}",
        "",
        "## Test Objective",
        "Evaluate whether the current NoobTrade generate logic can produce a positive trading outcome under a simple, rule-based execution framework.",
        "",
        "## Backtest Setup",
        f"- Universe: top 50 seeded stocks currently stored in `backend/noobtrade_local.db`",
        f"- Timeframe: `{TIMEFRAME}`",
        f"- Window size: `{WINDOW_SIZE}` bars",
        f"- Indicator bundle: `{', '.join(FULL_INDICATORS)}`",
        f"- Random historical anchors sampled: `{metadata['sampleCount']}`",
        f"- Starting capital: `${metadata['initialCapital']:,.2f}`",
        "- Position sizing: probability-tiered rolling allocation",
        f"  80% to <85% signals: minimum ${BASE_TIER_MIN_NOTIONAL:,.0f}, or {POSITION_SIZE_PCT * 100:.0f}% of equity once total equity exceeds $1,000,000",
        f"  85% to <90% signals: minimum ${MID_TIER_MIN_NOTIONAL:,.0f}, or {MID_TIER_PCT * 100:.0f}% of equity once total equity exceeds $1,000,000",
        f"  >=90% signals: minimum ${HIGH_TIER_MIN_NOTIONAL:,.0f}, or {HIGH_TIER_PCT * 100:.0f}% of equity once total equity exceeds $1,000,000",
        f"- Buy rule: enter only when `P(+1% in 5D) > {metadata['buyThresholdPct']:.0f}%`",
        f"- Take-profit rule: exit at `+{metadata['targetUpPct']:.1f}%`",
        "- Stop-loss rule: exit at the model's suggested historical risk line",
        "- Time stop: if neither target nor stop is hit, exit at the close of day 5",
        "- Portfolio assumption: sampled anchors are sorted chronologically and can open concurrently across multiple stocks",
        "- Intraday assumption: if both target and stop are touched on the same day, the stop-loss is applied first (conservative assumption)",
        "",
        "## Charts",
        "",
        f"![KPI Summary]({metadata['kpiChartPath']})",
        "",
        f"![Equity Curve]({metadata['equityChartPath']})",
        "",
        f"![Exit Breakdown]({metadata['exitChartPath']})",
        "",
        "## Core Results",
        f"- Sampled anchors: `{summary['sampledAnchors']}`",
        f"- Eligible anchors with enough future data: `{summary['eligibleAnchors']}`",
        f"- Buy signals triggered: `{summary['buySignals']}`",
        f"- Trades executed: `{summary['executedTrades']}`",
        f"- Final capital: `${summary['finalCapital']:,.2f}`",
        f"- Net P&L: `${summary['netPnl']:,.2f}`",
        f"- Total return: `{summary['totalReturnPct']:.2f}%`",
        f"- Win rate: `{summary['winRate']:.2f}%`",
        f"- Average trade return: `{summary['avgTradeReturnPct']:.2f}%`",
        f"- Average holding days: `{summary['avgHoldingDays']:.2f}`",
        f"- Max drawdown: `{summary['maxDrawdownPct']:.2f}%`",
        f"- Simulated annualized return: `{summary['annualizedReturnPct']:.2f}%`",
        f"- Turnover: `{summary['turnoverPct']:.2f}%`",
        f"- Peak concurrent positions: `{summary['peakConcurrentPositions']}`",
        f"- Profit/loss ratio: `{summary['profitLossRatio']:.2f}`" if summary["profitLossRatio"] is not None else "- Profit/loss ratio: `N/A`",
        f"- Hit target rate: `{hit_target_rate:.2f}%`",
        f"- Stop-loss rate: `{stop_rate:.2f}%`",
        f"- Time-exit rate: `{time_exit_rate:.2f}%`",
        "",
        "## Interpretation",
        "This backtest is designed as a structured evaluation of the existing NoobTrade generate engine, not as a full institutional trading simulator. The test directly checks whether weighted indicator scoring, penalty logic, and historical pattern matching can support a simple actionable rule with positive capital growth under concurrent portfolio conditions.",
        "",
        "## First Five Executed Trades",
        "",
        "| Date | Symbol | P(+1% in 5D) | Entry | Exit | Reason | P&L |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: |",
    ]

    for trade in trades[:5]:
        lines.append(
            f"| {trade['anchorDate']} | {trade['symbol']} | {trade['probabilityOfIncrease']:.2f}% | "
            f"${trade['entryPrice']:.2f} | ${trade['exitPrice']:.2f} | {trade['exitReason']} | ${trade['pnl']:.2f} |"
        )

    lines.extend([
        "",
        "## Output Files",
        f"- JSON detail: `{metadata['jsonPath']}`",
        f"- Markdown report: `{metadata['reportPath']}`",
        f"- KPI chart: `{metadata['kpiChartPath']}`",
        f"- Equity curve chart: `{metadata['equityChartPath']}`",
        f"- Exit breakdown chart: `{metadata['exitChartPath']}`",
        "",
    ])

    return "\n".join(lines)


def _max_drawdown_pct(equity_curve):
    if not equity_curve:
        return 0.0

    peak = equity_curve[0]
    max_drawdown = 0.0

    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            drawdown = ((value - peak) / peak) * 100
            max_drawdown = min(max_drawdown, drawdown)

    return round(abs(max_drawdown), 4)


def _format_eta(seconds_remaining):
    if seconds_remaining <= 0:
        return "0m"
    minutes = int(seconds_remaining // 60)
    seconds = int(seconds_remaining % 60)
    if minutes >= 60:
        hours = minutes // 60
        rem_minutes = minutes % 60
        return f"{hours}h {rem_minutes}m"
    return f"{minutes}m {seconds}s"


def _print_signal_progress(processed, total, start_time, buy_signals):
    elapsed = max(time.monotonic() - start_time, 1e-9)
    anchors_per_second = processed / elapsed
    remaining = max(total - processed, 0)
    eta_seconds = remaining / anchors_per_second if anchors_per_second > 0 else 0.0
    print(
        f"[signal] {processed}/{total} anchors | buy signals: {buy_signals} | ETA: {_format_eta(eta_seconds)}",
        flush=True,
    )


def _print_portfolio_progress(processed, total, start_time, cash, open_positions, trade_rows):
    elapsed = max(time.monotonic() - start_time, 1e-9)
    dates_per_second = processed / elapsed
    remaining = max(total - processed, 0)
    eta_seconds = remaining / dates_per_second if dates_per_second > 0 else 0.0
    realized_win_rate = (
        (sum(1 for trade in trade_rows if trade["pnl"] > 0) / len(trade_rows)) * 100
        if trade_rows else 0.0
    )
    current_equity = _mark_to_market_equity(cash, open_positions)
    print(
        f"[portfolio] {processed}/{total} dates | win rate: {realized_win_rate:.2f}% | capital: ${current_equity:,.2f} | open: {len(open_positions)} | ETA: {_format_eta(eta_seconds)}",
        flush=True,
    )


def run_backtest(
    sample_count,
    initial_capital,
    seed,
    buy_threshold_pct,
    target_up_pct,
    progress_every,
    selected_indicators,
    require_five_up_probability=None,
    fixed_stop_pct=None,
    dynamic_target_from_matches=False,
    single_position=False,
    max_open_positions=None,
    no_new_entries_above_positions=None,
    use_all_anchors=False,
    candidate_limit=None,
    commission_pct=DEFAULT_COMMISSION_PCT,
    slippage_pct=DEFAULT_SLIPPAGE_PCT,
    test_last_trading_days=None,
    test_window_offset_trading_days=0,
    require_boll_lower_touch=False,
    require_macd_histogram_up_bars=0,
):
    app = create_app()
    rng = random.Random(seed)
    quant_service = QuantScoringService()
    persistence_service = PersistenceService()

    with app.app_context():
        symbols = _load_symbol_universe()
        symbol_ids = [symbol.id for symbol in symbols]
        symbol_lookup = {symbol.id: symbol.symbol for symbol in symbols}
        price_history, date_index = _load_price_history(symbol_ids)
        windows = _load_daily_windows(symbol_ids)
        indicator_history, indicator_date_index = _load_indicator_history(symbol_ids)

        eligible_anchors = []

        for window in windows:
            index_lookup = date_index.get(window.symbol_id, {})
            price_rows = price_history.get(window.symbol_id, [])
            anchor_index = index_lookup.get(window.end_date)

            if anchor_index is None:
                continue
            if anchor_index + FORWARD_DAYS >= len(price_rows):
                continue

            eligible_anchors.append(window)

        if not eligible_anchors:
            raise RuntimeError("No eligible daily 30-bar anchors were found for the current top-50 seed database.")

        if test_last_trading_days:
            eligible_anchor_dates = sorted({window.end_date for window in eligible_anchors})
            offset = max(0, int(test_window_offset_trading_days or 0))
            if offset >= len(eligible_anchor_dates):
                raise RuntimeError("Blind-test offset exceeds the number of eligible anchor dates.")
            window_end = len(eligible_anchor_dates) - offset
            window_start = max(0, window_end - test_last_trading_days)
            blind_test_dates = set(eligible_anchor_dates[window_start:window_end])
            eligible_anchors = [window for window in eligible_anchors if window.end_date in blind_test_dates]

        sampled_anchors = eligible_anchors if use_all_anchors else rng.sample(eligible_anchors, min(sample_count, len(eligible_anchors)))
        sampled_anchors.sort(key=lambda window: (window.end_date, window.symbol_id, window.id))

        signal_entries = []
        buy_signals = 0
        skippedInvalidSignal = 0
        candidate_index = 0
        available_candidates = []
        sorted_windows = sorted(windows, key=lambda window: (window.end_date, window.id))

        signal_phase_start = time.monotonic()
        for anchor_index_number, anchor in enumerate(sampled_anchors, start=1):
            if require_boll_lower_touch and not _passes_boll_lower_touch_filter(
                anchor.symbol_id,
                anchor.end_date,
                price_history,
                date_index,
                indicator_history,
                indicator_date_index,
            ):
                if progress_every and anchor_index_number % progress_every == 0:
                    _print_signal_progress(anchor_index_number, len(sampled_anchors), signal_phase_start, buy_signals)
                continue

            if require_macd_histogram_up_bars and not _passes_macd_histogram_strength_filter(
                anchor.symbol_id,
                anchor.end_date,
                price_history,
                date_index,
                indicator_history,
                indicator_date_index,
                require_macd_histogram_up_bars,
            ):
                if progress_every and anchor_index_number % progress_every == 0:
                    _print_signal_progress(anchor_index_number, len(sampled_anchors), signal_phase_start, buy_signals)
                continue

            while candidate_index < len(sorted_windows):
                candidate = sorted_windows[candidate_index]
                if candidate.end_date >= anchor.end_date:
                    break
                available_candidates.append(candidate)
                candidate_index += 1

            prior_candidates = [candidate for candidate in available_candidates if candidate.id != anchor.id]
            if candidate_limit is not None and len(prior_candidates) > candidate_limit:
                # Keep the most recent historical windows for fast walk-forward sweeps.
                # This preserves chronological causality while avoiding unbounded global scans.
                prior_candidates = prior_candidates[-candidate_limit:]

            if not prior_candidates:
                continue

            matched_patterns = _rank_matches_for_anchor(
                anchor_window=anchor,
                candidate_windows=prior_candidates,
                selected_indicators=selected_indicators,
                quant_service=quant_service,
                persistence_service=persistence_service,
                symbol_lookup=symbol_lookup,
            )

            probability_summary = persistence_service._build_future_probability_summary(
                matched_patterns,
                selected_indicators,
            )

            if probability_summary["probability_percent"] <= buy_threshold_pct:
                if progress_every and anchor_index_number % progress_every == 0:
                    _print_signal_progress(anchor_index_number, len(sampled_anchors), signal_phase_start, buy_signals)
                continue

            match_strength = _summarize_match_strength(matched_patterns)
            if (
                require_five_up_probability is not None
                and match_strength["fivePercentUpProbability"] < require_five_up_probability
            ):
                if progress_every and anchor_index_number % progress_every == 0:
                    _print_signal_progress(anchor_index_number, len(sampled_anchors), signal_phase_start, buy_signals)
                continue

            buy_signals += 1
            anchor_index = date_index[anchor.symbol_id][anchor.end_date]
            future_prices = price_history[anchor.symbol_id][anchor_index + 1: anchor_index + 1 + FORWARD_DAYS]
            trade_signal = _build_trade_signal(
                anchor_window=anchor,
                probability_summary=probability_summary,
                future_prices=future_prices,
                matched_patterns=matched_patterns,
                symbol=symbol_lookup.get(anchor.symbol_id, "N/A"),
                target_up_pct=target_up_pct,
                fixed_stop_pct=fixed_stop_pct,
                dynamic_target_from_matches=dynamic_target_from_matches,
            )

            if trade_signal is None:
                skippedInvalidSignal += 1
            else:
                signal_entries.append(trade_signal)

            if progress_every and anchor_index_number % progress_every == 0:
                _print_signal_progress(anchor_index_number, len(sampled_anchors), signal_phase_start, buy_signals)

    signal_entries.sort(key=lambda item: (item["entryDate"], item["symbol"], item["anchorDate"]))
    signals_by_date = {}

    for signal in signal_entries:
        signals_by_date.setdefault(signal["entryDate"], []).append(signal)

    relevant_dates = sorted({
        *signals_by_date.keys(),
        *{
            row.trade_date
            for signal in signal_entries
            for row in signal["futurePrices"]
        }
    })

    cash = float(initial_capital)
    open_positions = []
    equity_curve = [cash]
    trade_rows = []
    peak_open_positions = 0
    portfolio_phase_start = time.monotonic()

    for date_index_number, current_date in enumerate(relevant_dates, start=1):
        open_positions_at_day_open = len(open_positions)
        next_open_positions = []

        for position in open_positions:
            row = position["priceMap"].get(current_date)
            if row is None:
                next_open_positions.append(position)
                continue

            position["currentDate"] = current_date
            day_index = position["dayIndex"] + 1
            position["dayIndex"] = day_index
            exit_record = None

            if row.low <= position["stopLossPrice"] and row.high >= position["targetPrice"]:
                exit_record = _close_position(position, position["stopLossPrice"], "stop_loss_same_day_dual_touch", day_index, commission_pct, slippage_pct)
            elif row.low <= position["stopLossPrice"]:
                exit_record = _close_position(position, position["stopLossPrice"], "stop_loss", day_index, commission_pct, slippage_pct)
            elif row.high >= position["targetPrice"]:
                exit_record = _close_position(position, position["targetPrice"], "take_profit", day_index, commission_pct, slippage_pct)
            elif current_date >= position["expiryDate"]:
                exit_record = _close_position(position, row.close, "time_exit", day_index, commission_pct, slippage_pct)

            if exit_record is not None:
                cash += exit_record["netExitCash"]
                trade_rows.append(exit_record)
                continue

            position["lastMarkPrice"] = row.close
            next_open_positions.append(position)

        open_positions = next_open_positions
        opened_position_this_date = False
        opened_positions_this_date = 0
        current_date_peak_positions = open_positions_at_day_open

        for signal in signals_by_date.get(current_date, []):
            if single_position and (open_positions or opened_position_this_date):
                continue
            if (
                no_new_entries_above_positions is not None
                and open_positions_at_day_open >= no_new_entries_above_positions
            ):
                continue
            if (
                max_open_positions is not None
                and open_positions_at_day_open + opened_positions_this_date >= max_open_positions
            ):
                continue

            current_equity = _mark_to_market_equity(cash, open_positions)
            desired_notional = _tiered_position_notional(
                current_equity=current_equity,
                available_cash=cash,
                probability_of_increase=signal["probabilityOfIncrease"],
            )
            entry_price = signal["entryReferencePrice"] * (1 + (slippage_pct / 100))
            actual_notional = min(cash, desired_notional)

            if entry_price <= 0 or actual_notional <= 0:
                continue

            entry_commission = actual_notional * (commission_pct / 100)
            investable_notional = actual_notional - entry_commission
            if investable_notional <= 0:
                continue

            shares = investable_notional / entry_price
            if shares <= 0:
                continue

            cash -= actual_notional
            entry_row = signal["priceMap"][current_date]
            position = {
                **signal,
                "entryPrice": entry_price,
                "entryReferencePrice": signal["entryReferencePrice"],
                "positionNotional": actual_notional,
                "entryCommission": entry_commission,
                "entryCashOutlay": actual_notional,
                "shares": shares,
                "lastMarkPrice": entry_row.close,
                "dayIndex": 1,
                "currentDate": current_date,
            }

            exit_record = None
            if entry_row.low <= position["stopLossPrice"] and entry_row.high >= position["targetPrice"]:
                exit_record = _close_position(position, position["stopLossPrice"], "stop_loss_same_day_dual_touch", 1, commission_pct, slippage_pct)
            elif entry_row.low <= position["stopLossPrice"]:
                exit_record = _close_position(position, position["stopLossPrice"], "stop_loss", 1, commission_pct, slippage_pct)
            elif entry_row.high >= position["targetPrice"]:
                exit_record = _close_position(position, position["targetPrice"], "take_profit", 1, commission_pct, slippage_pct)
            elif current_date >= position["expiryDate"]:
                exit_record = _close_position(position, entry_row.close, "time_exit", 1, commission_pct, slippage_pct)

            if exit_record is not None:
                cash += exit_record["netExitCash"]
                trade_rows.append(exit_record)
            else:
                open_positions.append(position)
            opened_positions_this_date += 1
            current_date_peak_positions = max(
                current_date_peak_positions,
                open_positions_at_day_open + opened_positions_this_date,
            )
            opened_position_this_date = True

        peak_open_positions = max(peak_open_positions, current_date_peak_positions, len(open_positions))
        equity_curve.append(_mark_to_market_equity(cash, open_positions))
        if progress_every and date_index_number % progress_every == 0:
            _print_portfolio_progress(date_index_number, len(relevant_dates), portfolio_phase_start, cash, open_positions, trade_rows)

    executed_trades = len(trade_rows)
    winning_trades = [trade for trade in trade_rows if trade["pnl"] > 0]
    losing_trades = [trade for trade in trade_rows if trade["pnl"] < 0]
    time_exits = [trade for trade in trade_rows if trade["exitReason"] == "time_exit"]
    stop_exits = [trade for trade in trade_rows if "stop_loss" in trade["exitReason"]]
    target_exits = [trade for trade in trade_rows if trade["exitReason"] == "take_profit"]

    total_notional_traded = sum(trade["positionNotional"] for trade in trade_rows)
    turnover_pct = round((total_notional_traded / float(initial_capital)) * 100, 4) if initial_capital else 0.0
    simulated_trading_days = max(len(relevant_dates), 1)
    annualized_return_pct = (
        round((((cash / float(initial_capital)) ** (252 / simulated_trading_days)) - 1) * 100, 4)
        if initial_capital and cash > 0 and simulated_trading_days > 0
        else 0.0
    )

    summary = {
        "initialCapital": round(float(initial_capital), 2),
        "finalCapital": round(cash, 2),
        "netPnl": round(cash - float(initial_capital), 2),
        "totalReturnPct": round(((cash / float(initial_capital)) - 1) * 100, 4) if initial_capital else 0.0,
        "sampledAnchors": len(sampled_anchors),
        "eligibleAnchors": len(sampled_anchors),
        "buySignals": buy_signals,
        "executedTrades": executed_trades,
        "skippedInvalidSignal": skippedInvalidSignal,
        "winRate": round((len(winning_trades) / executed_trades) * 100, 4) if executed_trades else 0.0,
        "avgTradeReturnPct": round(mean(trade["pnlPct"] for trade in trade_rows), 4) if trade_rows else 0.0,
        "avgHoldingDays": round(mean(trade["holdingDays"] for trade in trade_rows), 4) if trade_rows else 0.0,
        "maxDrawdownPct": _max_drawdown_pct(equity_curve),
        "annualizedReturnPct": annualized_return_pct,
        "turnoverPct": turnover_pct,
        "hitTargetRate": round((len(target_exits) / executed_trades) * 100, 4) if executed_trades else 0.0,
        "stopRate": round((len(stop_exits) / executed_trades) * 100, 4) if executed_trades else 0.0,
        "timeExitRate": round((len(time_exits) / executed_trades) * 100, 4) if executed_trades else 0.0,
        "averageWinnerPnl": round(mean(trade["pnl"] for trade in winning_trades), 4) if winning_trades else 0.0,
        "averageLoserPnl": round(mean(trade["pnl"] for trade in losing_trades), 4) if losing_trades else 0.0,
        "profitLossRatio": round(
            abs(mean(trade["pnl"] for trade in winning_trades) / mean(trade["pnl"] for trade in losing_trades)),
            4,
        ) if winning_trades and losing_trades and mean(trade["pnl"] for trade in losing_trades) != 0 else None,
        "peakConcurrentPositions": peak_open_positions,
    }

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = REPORTS_DIR / f"top50_generate_backtest_{timestamp}.json"
    report_path = REPORTS_DIR / f"top50_generate_backtest_{timestamp}.md"

    payload = {
        "metadata": {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "sampleCount": sample_count,
            "initialCapital": float(initial_capital),
            "seed": seed,
            "positionSizePct": POSITION_SIZE_PCT,
            "positionSizingMode": "probability_tiered",
            "timeframe": TIMEFRAME,
            "windowSize": WINDOW_SIZE,
            "forwardDays": FORWARD_DAYS,
            "buyThresholdPct": buy_threshold_pct,
            "targetUpPct": target_up_pct,
            "requireFiveUpProbability": require_five_up_probability,
            "fixedStopPct": fixed_stop_pct,
            "dynamicTargetFromMatches": dynamic_target_from_matches,
            "singlePosition": single_position,
            "maxOpenPositions": max_open_positions,
            "noNewEntriesAbovePositions": no_new_entries_above_positions,
            "useAllAnchors": use_all_anchors,
            "candidateLimit": candidate_limit,
            "commissionPct": commission_pct,
            "slippagePct": slippage_pct,
            "testLastTradingDays": test_last_trading_days,
            "indicators": selected_indicators,
        },
        "summary": summary,
        "trades": trade_rows,
    }

    json_path.write_text(json.dumps(payload, indent=2))
    equity_chart_path = REPORTS_DIR / f"top50_generate_backtest_{timestamp}_equity.svg"
    exit_chart_path = REPORTS_DIR / f"top50_generate_backtest_{timestamp}_exit.svg"
    kpi_chart_path = REPORTS_DIR / f"top50_generate_backtest_{timestamp}_kpi.svg"
    _write_svg(equity_chart_path, _build_equity_curve_svg(equity_curve, summary, payload["metadata"]))
    _write_svg(exit_chart_path, _build_exit_reason_svg(summary))
    _write_svg(kpi_chart_path, _build_kpi_svg(summary, payload["metadata"]))

    report_metadata = {
        "generatedAt": payload["metadata"]["generatedAt"],
        "sampleCount": sample_count,
        "initialCapital": float(initial_capital),
        "buyThresholdPct": buy_threshold_pct,
        "targetUpPct": target_up_pct,
        "requireFiveUpProbability": require_five_up_probability,
        "fixedStopPct": fixed_stop_pct,
        "dynamicTargetFromMatches": dynamic_target_from_matches,
        "singlePosition": single_position,
        "maxOpenPositions": max_open_positions,
        "noNewEntriesAbovePositions": no_new_entries_above_positions,
        "useAllAnchors": use_all_anchors,
        "candidateLimit": candidate_limit,
        "commissionPct": commission_pct,
        "slippagePct": slippage_pct,
        "testLastTradingDays": test_last_trading_days,
        "jsonPath": str(json_path.relative_to(BACKEND_DIR)),
        "reportPath": str(report_path.relative_to(BACKEND_DIR)),
        "equityChartPath": str(equity_chart_path.relative_to(BACKEND_DIR)),
        "exitChartPath": str(exit_chart_path.relative_to(BACKEND_DIR)),
        "kpiChartPath": str(kpi_chart_path.relative_to(BACKEND_DIR)),
    }
    report_path.write_text(_build_report_markdown(summary, trade_rows, report_metadata))

    print(json.dumps({
        "jsonPath": str(json_path),
        "reportPath": str(report_path),
        "summary": summary,
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Backtest the NoobTrade generate strategy on the seeded top-50 universe.")
    parser.add_argument("--samples", type=int, default=5000, help="Number of random historical anchors to sample.")
    parser.add_argument("--initial-capital", type=float, default=1000000.0, help="Starting capital for the concurrent multi-position simulation.")
    parser.add_argument("--seed", type=int, default=20260406, help="Random seed for reproducible sampling.")
    parser.add_argument("--buy-threshold", type=float, default=95.0, help="Minimum probability of reaching +1%% in 5D required to trigger a trade.")
    parser.add_argument("--target-up-pct", type=float, default=1.2, help="Take-profit threshold in percent.")
    parser.add_argument("--progress-every", type=int, default=100, help="Print progress every N anchors / dates.")
    parser.add_argument("--require-five-up-prob", type=float, default=None, help="Require at least this percent of matched patterns to reach +5%% in 5D.")
    parser.add_argument("--fixed-stop-pct", type=float, default=None, help="Use a fixed percentage stop loss instead of the model risk line.")
    parser.add_argument("--dynamic-target-from-matches", action="store_true", help="Set take-profit to average top-match 5D high minus 1 percentage point.")
    parser.add_argument("--single-position", action="store_true", help="Allow only one open position at a time, similar to the first sequential backtest.")
    parser.add_argument("--max-open-positions", type=int, default=None, help="Maximum number of concurrent open positions.")
    parser.add_argument("--no-new-entries-above-positions", type=int, default=None, help="Do not open new trades when positions already open at the day start are at or above this count.")
    parser.add_argument("--all-anchors", action="store_true", help="Use every eligible anchor in chronological order instead of random sampling.")
    parser.add_argument("--test-last-trading-days", type=int, default=None, help="Restrict anchors to the last N eligible trading days so earlier history is used only as prior context.")
    parser.add_argument("--test-window-offset-trading-days", type=int, default=0, help="Offset the blind-test window backwards by N eligible trading days. For example, 252 uses the previous blind year instead of the most recent one.")
    parser.add_argument("--candidate-limit", type=int, default=None, help="Limit each anchor to the most recent N prior candidate windows before exact scoring.")
    parser.add_argument("--require-boll-lower-touch", action="store_true", help="Only allow buys when price touches or breaks the lower Bollinger band on the anchor day.")
    parser.add_argument("--require-macd-histogram-up-bars", type=int, default=0, help="Require at least N consecutive rising positive MACD histogram bars ending on the anchor day.")
    parser.add_argument("--commission-pct", type=float, default=DEFAULT_COMMISSION_PCT, help="Commission charged on entry and exit, as percent of notional.")
    parser.add_argument("--slippage-pct", type=float, default=DEFAULT_SLIPPAGE_PCT, help="Execution slippage applied against entry and exit prices, in percent.")
    parser.add_argument(
        "--indicators",
        type=str,
        default=",".join(DEFAULT_SELECTED_INDICATORS),
        help="Comma-separated indicator list to use for generate scoring.",
    )
    args = parser.parse_args()
    selected_indicators = [item.strip().upper() for item in args.indicators.split(",") if item.strip()]

    run_backtest(
        sample_count=max(1, args.samples),
        initial_capital=max(1.0, args.initial_capital),
        seed=args.seed,
        buy_threshold_pct=max(0.0, args.buy_threshold),
        target_up_pct=max(0.1, args.target_up_pct),
        progress_every=max(0, args.progress_every),
        selected_indicators=selected_indicators or DEFAULT_SELECTED_INDICATORS,
        require_five_up_probability=args.require_five_up_prob,
        fixed_stop_pct=args.fixed_stop_pct,
        dynamic_target_from_matches=args.dynamic_target_from_matches,
        single_position=args.single_position,
        max_open_positions=max(1, args.max_open_positions) if args.max_open_positions else None,
        no_new_entries_above_positions=max(1, args.no_new_entries_above_positions) if args.no_new_entries_above_positions else None,
        use_all_anchors=args.all_anchors,
        test_last_trading_days=max(1, args.test_last_trading_days) if args.test_last_trading_days else None,
        test_window_offset_trading_days=max(0, args.test_window_offset_trading_days),
        candidate_limit=max(20, args.candidate_limit) if args.candidate_limit else None,
        commission_pct=max(0.0, args.commission_pct),
        slippage_pct=max(0.0, args.slippage_pct),
        require_boll_lower_touch=args.require_boll_lower_touch,
        require_macd_histogram_up_bars=max(0, args.require_macd_histogram_up_bars),
    )


if __name__ == "__main__":
    main()
