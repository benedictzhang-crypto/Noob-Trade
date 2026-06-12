from datetime import date, datetime, timedelta

VISIBLE_INTERVAL_BARS = {
    "1min": 390,
    "5min": 390,
    "15min": 260,
    "30min": 220,
    "1hour": 220,
    "daily": 3200,
    "5day": 700,
    "weekly": 700,
    "2week": 400,
    "monthly": 240,
}


def parse_indicators(raw_indicators, default_indicators):
    """Turn a comma-separated indicator string into a clean list."""
    alias_map = {"PBV": "OBV"}

    if not raw_indicators:
        return [alias_map.get(indicator, indicator) for indicator in default_indicators]

    indicators = [item.strip().upper() for item in raw_indicators.split(",")]
    cleaned_indicators = [alias_map.get(indicator, indicator) for indicator in indicators if indicator]

    return cleaned_indicators or [alias_map.get(indicator, indicator) for indicator in default_indicators]


def build_mock_daily_candles(symbol):
    """Return a deterministic set of mock daily candles."""
    del symbol

    candles = []
    current_day = date(2025, 9, 15)
    close_price = 154.0
    session_index = 0

    while len(candles) < 3200:
        if current_day.weekday() >= 5:
            current_day += timedelta(days=1)
            continue

        drift = ((session_index % 9) - 4) * 0.35
        momentum = 0.42 if session_index % 17 in (4, 5, 6) else -0.18 if session_index % 13 == 0 else 0.11
        open_price = close_price + ((session_index % 5) - 2) * 0.27
        close_price = max(118.0, open_price + drift + momentum)
        high_price = max(open_price, close_price) + 1.2 + (session_index % 4) * 0.21
        low_price = min(open_price, close_price) - 1.05 - (session_index % 3) * 0.18
        volume = 840000 + ((session_index * 17391) % 520000)

        candles.append(
            {
                "date": current_day.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": int(volume),
            }
        )

        current_day += timedelta(days=1)
        session_index += 1

    return candles


def group_candles_by_size(candles, group_size):
    grouped = []

    for index in range(0, len(candles), group_size):
        chunk = candles[index:index + group_size]

        if not chunk:
            continue

        grouped.append(
            {
                "date": chunk[-1]["date"],
                "open": chunk[0]["open"],
                "high": max(item["high"] for item in chunk),
                "low": min(item["low"] for item in chunk),
                "close": chunk[-1]["close"],
                "volume": sum(item["volume"] for item in chunk),
            }
        )

    return grouped


def build_mock_monthly_candles_from_daily(daily_candles):
    grouped = {}

    for item in daily_candles:
        month_key = item["date"][:7]

        if month_key not in grouped:
            grouped[month_key] = {
                "date": month_key,
                "open": item["open"],
                "high": item["high"],
                "low": item["low"],
                "close": item["close"],
                "volume": item["volume"],
            }
            continue

        month = grouped[month_key]
        month["high"] = max(month["high"], item["high"])
        month["low"] = min(month["low"], item["low"])
        month["close"] = item["close"]
        month["volume"] += item["volume"]

    return list(grouped.values())


def build_mock_monthly_candles():
    """Return a simple set of mock monthly candles."""
    return build_mock_monthly_candles_from_daily(build_mock_daily_candles("MOCK"))[-24:]


def build_mock_intraday_candles(symbol, interval_minutes, bars):
    """Return deterministic intraday candles for demo chart intervals."""
    daily_candles = build_mock_daily_candles(symbol)
    anchor = daily_candles[-1]
    session_start = datetime.combine(date(2026, 5, 22), datetime.strptime("09:30", "%H:%M").time())
    close_price = anchor["close"] * 0.985
    candles = []

    for index in range(bars):
        timestamp = session_start + timedelta(minutes=index * interval_minutes)
        wave = ((index % 11) - 5) * 0.018
        trend = (index / max(bars, 1)) * (anchor["close"] * 0.018)
        open_price = close_price
        close_price = max(1, open_price + wave + trend / max(bars, 1))
        high_price = max(open_price, close_price) + 0.04 + (index % 3) * 0.012
        low_price = min(open_price, close_price) - 0.04 - (index % 2) * 0.01

        candles.append(
            {
                "date": timestamp.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": int(12000 + ((index * 947) % 33000)),
            }
        )

    return candles


def build_mock_interval_series():
    """Return chart series for several trading intervals."""
    daily_candles = build_mock_daily_candles("MOCK")
    weekly_like = group_candles_by_size(daily_candles, 5)
    biweekly = group_candles_by_size(daily_candles, 10)
    monthly = build_mock_monthly_candles()

    return {
        "1min": build_mock_intraday_candles("MOCK", 1, VISIBLE_INTERVAL_BARS["1min"]),
        "5min": build_mock_intraday_candles("MOCK", 5, VISIBLE_INTERVAL_BARS["5min"]),
        "15min": build_mock_intraday_candles("MOCK", 15, VISIBLE_INTERVAL_BARS["15min"]),
        "30min": build_mock_intraday_candles("MOCK", 30, VISIBLE_INTERVAL_BARS["30min"]),
        "1hour": build_mock_intraday_candles("MOCK", 60, VISIBLE_INTERVAL_BARS["1hour"]),
        "daily": daily_candles[-VISIBLE_INTERVAL_BARS["daily"]:],
        "5day": weekly_like[-VISIBLE_INTERVAL_BARS["5day"]:],
        "weekly": weekly_like[-VISIBLE_INTERVAL_BARS["weekly"]:],
        "2week": biweekly[-VISIBLE_INTERVAL_BARS["2week"]:],
        "monthly": monthly[-VISIBLE_INTERVAL_BARS["monthly"]:]
    }


def build_mock_stock_pattern_analysis(symbol, interval, lookback_window, indicators):
    """Return mock stock and pattern analysis data."""
    cleaned_symbol = symbol.upper()
    daily_candles = build_mock_daily_candles(cleaned_symbol)
    interval_series = build_mock_interval_series()
    matched_series = interval_series.get(interval, interval_series["daily"])
    matched_patterns = [
        {
            "patternName": "Historical setup #1",
            "matchScore": 91,
            "date": "2026-03-10",
            "symbol": cleaned_symbol,
            "timeframe": interval,
            "windowSize": 30,
            "returnPct": 1.84,
            "maxDrawdown": -0.92,
            "futureReturn5d": 4.6,
            "futureDrawdown5d": -1.2,
            "futureStats5d": {
                "maxUpPct": 4.6,
                "maxDownPct": -1.2,
                "targetPrice": 192.73,
                "riskPrice": 182.04,
            },
            "quantSelectedPercent": 91,
            "historicalCandles": matched_series[-30:],
        },
        {
            "patternName": "Historical setup #2",
            "matchScore": 87,
            "date": "2026-02-24",
            "symbol": cleaned_symbol,
            "timeframe": interval,
            "windowSize": 30,
            "returnPct": 0.94,
            "maxDrawdown": -1.14,
            "futureReturn5d": 3.2,
            "futureDrawdown5d": -2.1,
            "futureStats5d": {
                "maxUpPct": 3.2,
                "maxDownPct": -2.1,
                "targetPrice": 190.15,
                "riskPrice": 180.38,
            },
            "quantSelectedPercent": 87,
            "historicalCandles": matched_series[-60:-30],
        },
        {
            "patternName": "Historical setup #3",
            "matchScore": 82,
            "date": "2026-01-15",
            "symbol": cleaned_symbol,
            "timeframe": interval,
            "windowSize": 30,
            "returnPct": 0.41,
            "maxDrawdown": -1.68,
            "futureReturn5d": 1.9,
            "futureDrawdown5d": -2.8,
            "futureStats5d": {
                "maxUpPct": 1.9,
                "maxDownPct": -2.8,
                "targetPrice": 187.75,
                "riskPrice": 179.09,
            },
            "quantSelectedPercent": 82,
            "historicalCandles": matched_series[-90:-60],
        }
    ]

    return {
        "dataSource": "mock",
        "request": {
            "symbol": cleaned_symbol,
            "interval": interval,
            "lookback": lookback_window,
            "indicators": indicators
        },
        "stock": {
            "symbol": cleaned_symbol,
            "companyName": f"{cleaned_symbol} Holdings Inc.",
            "sector": "Technology",
            "industry": "Software",
            "currentPrice": 184.25,
            "previousClose": 181.9,
            "open": 182.4,
            "volume": 3245600,
            "week52High": 205.8,
            "week52Low": 121.35
        },
        "patternAnalysis": {
            "lookbackWindow": lookback_window,
            "selectedIndicators": indicators,
            "probabilityOfIncrease": 68.4,
            "probabilityOfDecrease": 100,
            "avgReturn": 3.2333,
            "maxDrawdown": -2.0333,
            "matchedPatternsCount": len(matched_patterns),
            "quantConfidence": 0.87,
            "signalClassification": "Bullish Bias",
            "futureFiveDayProbabilities": {
                "up": [
                    {"threshold": 1, "probability": 100},
                    {"threshold": 5, "probability": 0},
                    {"threshold": 10, "probability": 0},
                ],
                "down": [
                    {"threshold": 1, "probability": 100},
                    {"threshold": 5, "probability": 0},
                    {"threshold": 10, "probability": 0},
                ],
            },
            "matchedHistoricalPatterns": matched_patterns,
            "recommendedSellPrice": 198.4,
            "recommendedSellDate": "2026-04-16",
            "stopLossPrice": 178.8,
            "highFitHistoricalPaths": [
                {"label": "Bull Flag continuation", "fitScore": 91, "status": "Reserved for future path chart"},
                {"label": "Ascending Triangle breakout", "fitScore": 87, "status": "Reserved for future path chart"},
                {"label": "Momentum follow-through", "fitScore": 82, "status": "Reserved for future path chart"}
            ]
        },
        "chartData": {
            "series": interval_series,
            "history": {
                "daily": daily_candles
            }
        }
    }
