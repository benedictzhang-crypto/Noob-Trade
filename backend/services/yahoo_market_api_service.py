from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter

from services.duke_market_api_service import DukeMarketApiUnavailable


class YahooMarketApiService:
    """No-key Yahoo Finance chart client for free Stock Trade candles."""

    _provider_disabled_until = None
    _provider_failure_count = 0
    SYMBOL_ALIASES = {
        "APL": "AAPL",
        "APPL": "AAPL",
        "BRK.B": "BRK-B",
        "BRK/A": "BRK-A",
        "BRK/B": "BRK-B",
        "BF.B": "BF-B",
        "BF/A": "BF-A",
        "BF/B": "BF-B",
    }
    DISPLAY_ALIASES = {
        "BRK-B": "BRK.B",
        "BRK-A": "BRK.A",
        "BF-B": "BF.B",
        "BF-A": "BF.A",
    }
    INTRADAY_INTERVALS = {
        "1min": ("1m", "5d"),
        "5min": ("5m", "1mo"),
        "15min": ("15m", "1mo"),
        "30min": ("30m", "1mo"),
        "1hour": ("60m", "3mo"),
        "hourly": ("60m", "3mo"),
    }

    def __init__(self, base_url="https://query1.finance.yahoo.com", timeout=3.0, cooldown_seconds=10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cooldown_seconds = cooldown_seconds
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 NoobTrade/1.0",
                "Accept": "application/json,text/plain,*/*",
                "Connection": "keep-alive",
            }
        )

    def is_configured(self):
        return True

    def is_available(self):
        disabled_until = self.__class__._provider_disabled_until
        return disabled_until is None or datetime.utcnow() >= disabled_until

    def get_daily_prices(self, symbol, limit):
        range_value = "10y" if int(limit or 0) <= 2600 else "max"
        return self._get_chart(symbol, interval="1d", range_value=range_value, limit=limit, include_time=False)

    def get_intraday_prices(self, symbol, interval, limit=390):
        mapped_interval, range_value = self.INTRADAY_INTERVALS.get(str(interval or "").lower(), ("5m", "1mo"))
        return self._get_chart(symbol, interval=mapped_interval, range_value=range_value, limit=limit, include_time=True)

    def get_company_overview(self, symbol):
        payload = self._get_chart(symbol, interval="1d", range_value="5d", limit=5, include_time=False)
        meta = payload.get("meta", {})
        symbol_code = self._display_symbol(self._normalize_symbol(symbol))
        return {
            "data": {
                "symbol": symbol_code,
                "companyName": meta.get("longName") or meta.get("shortName") or symbol_code,
                "sector": "Yahoo Finance",
                "industry": "No-key market data",
                "exchange": meta.get("exchangeName") or meta.get("fullExchangeName") or "US",
            }
        }

    def get_stock_news(self, symbol, limit=5):
        del symbol, limit
        return {"data": []}

    def mark_unavailable(self, cooldown_seconds=None):
        cooldown = self.cooldown_seconds if cooldown_seconds is None else cooldown_seconds
        self.__class__._provider_disabled_until = datetime.utcnow() + timedelta(seconds=cooldown)

    def mark_available(self):
        self.__class__._provider_disabled_until = None
        self.__class__._provider_failure_count = 0

    def _normalize_symbol(self, symbol):
        normalized = str(symbol or "").strip().upper()
        return self.SYMBOL_ALIASES.get(normalized, normalized)

    def _display_symbol(self, symbol):
        return self.DISPLAY_ALIASES.get(symbol, symbol)

    def _get_chart(self, symbol, interval, range_value, limit, include_time):
        if not self.is_available():
            raise DukeMarketApiUnavailable("Market data provider is temporarily disabled after a recent connection failure.")

        symbol_code = self._normalize_symbol(symbol)
        try:
            response = self.session.get(
                f"{self.base_url}/v8/finance/chart/{quote(symbol_code, safe='')}",
                params={
                    "range": range_value,
                    "interval": interval,
                    "includePrePost": "false",
                    "events": "div,splits",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            chart = payload.get("chart", {}) if isinstance(payload, dict) else {}
            error = chart.get("error")
            if error:
                raise DukeMarketApiUnavailable(error.get("description") or "Yahoo Finance chart request failed.")

            results = chart.get("result") or []
            if not results:
                raise DukeMarketApiUnavailable("No chart data returned from Yahoo Finance.")

            result = results[0]
            meta = result.get("meta") or {}
            timestamps = result.get("timestamp") or []
            quotes = ((result.get("indicators") or {}).get("quote") or [{}])[0]
            bars = self._normalize_bars(timestamps, quotes, include_time=include_time)
            if limit:
                bars = bars[: max(1, int(limit))]

            self.mark_available()
            return {"data": bars, "meta": meta}
        except requests.exceptions.RequestException as error:
            self.__class__._provider_failure_count += 1
            if self.__class__._provider_failure_count >= 2:
                self.mark_unavailable()
            raise DukeMarketApiUnavailable(str(error)) from error

    def _normalize_bars(self, timestamps, quotes, include_time):
        opens = quotes.get("open") or []
        highs = quotes.get("high") or []
        lows = quotes.get("low") or []
        closes = quotes.get("close") or []
        volumes = quotes.get("volume") or []
        rows = []

        for index, timestamp in enumerate(timestamps):
            close = self._at(closes, index)
            if close is None:
                continue

            parsed = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
            date_value = parsed.isoformat() if include_time else parsed.date().isoformat()
            rows.append(
                {
                    "date": date_value,
                    "open": self._at(opens, index, close),
                    "high": self._at(highs, index, close),
                    "low": self._at(lows, index, close),
                    "close": close,
                    "volume": self._at(volumes, index, 0),
                }
            )

        rows.sort(key=lambda row: row["date"], reverse=True)
        return rows

    def _at(self, values, index, default=None):
        if index >= len(values):
            return default

        value = values[index]
        return default if value is None else value
