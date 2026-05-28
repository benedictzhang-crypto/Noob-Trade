from datetime import datetime, timedelta
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter

from services.duke_market_api_service import DukeMarketApiUnavailable


class AlpacaMarketApiService:
    """Small Alpaca Market Data client with the same surface as the Duke client."""

    _provider_disabled_until = None
    _provider_failure_count = 0
    SYMBOL_ALIASES = {
        "APL": "AAPL",
        "APPL": "AAPL",
        "BRK-B": "BRK.B",
        "BRK/B": "BRK.B",
        "BF-B": "BF.B",
        "BF/B": "BF.B",
    }
    INTRADAY_TIMEFRAMES = {
        "1min": "1Min",
        "5min": "5Min",
        "15min": "15Min",
        "30min": "30Min",
        "1hour": "1Hour",
        "hourly": "1Hour",
    }

    def __init__(
        self,
        api_key,
        api_secret,
        base_url="https://data.alpaca.markets/v2",
        feed="iex",
        timeout=3.0,
        cooldown_seconds=10,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.feed = str(feed or "iex").strip().lower()
        self.timeout = timeout
        self.cooldown_seconds = cooldown_seconds
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(
            {
                "APCA-API-KEY-ID": self.api_key or "",
                "APCA-API-SECRET-KEY": self.api_secret or "",
                "Connection": "keep-alive",
            }
        )

    def is_configured(self):
        return bool(self.api_key and self.api_secret)

    def is_available(self):
        disabled_until = self.__class__._provider_disabled_until
        return disabled_until is None or datetime.utcnow() >= disabled_until

    def get_daily_prices(self, symbol, limit):
        return self._get_bars(symbol, timeframe="1Day", limit=limit)

    def get_intraday_prices(self, symbol, interval, limit=390):
        timeframe = self.INTRADAY_TIMEFRAMES.get(str(interval or "").lower())
        if not timeframe:
            return {"data": []}

        return self._get_bars(symbol, timeframe=timeframe, limit=limit)

    def get_company_overview(self, symbol):
        symbol_code = self._normalize_symbol(symbol)
        return {
            "data": {
                "symbol": symbol_code,
                "companyName": symbol_code,
                "sector": "Alpaca IEX",
                "industry": "Market Data",
                "exchange": "US",
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
        normalized = str(symbol).strip().upper()
        normalized = self.SYMBOL_ALIASES.get(normalized, normalized)
        return normalized

    def _get_bars(self, symbol, timeframe, limit):
        if not self.is_configured():
            raise DukeMarketApiUnavailable("Alpaca market data credentials are not configured.")

        if not self.is_available():
            raise DukeMarketApiUnavailable("Market data provider is temporarily disabled after a recent connection failure.")

        symbol_code = self._normalize_symbol(symbol)
        try:
            response = self.session.get(
                f"{self.base_url}/stocks/{quote(symbol_code, safe='')}/bars",
                params={
                    "timeframe": timeframe,
                    "limit": max(1, int(limit or 1)),
                    "adjustment": "all",
                    "feed": self.feed,
                    "sort": "desc",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            self.mark_available()
            payload = response.json()
            return {"data": self._normalize_bars(payload.get("bars", []), include_time=timeframe != "1Day")}
        except requests.exceptions.RequestException as error:
            if isinstance(error, requests.exceptions.HTTPError) and error.response is not None and error.response.status_code < 500:
                raise

            self.__class__._provider_failure_count += 1
            if self.__class__._provider_failure_count >= 2:
                self.mark_unavailable()
            raise DukeMarketApiUnavailable(str(error)) from error

    def _normalize_bars(self, bars, include_time=False):
        normalized = []

        for bar in bars or []:
            timestamp = str(bar.get("t") or "").strip()
            if not timestamp:
                continue

            date_value = timestamp.split("T", 1)[0]
            if include_time and "T" in timestamp:
                date_value = timestamp.replace("Z", "+00:00")

            normalized.append(
                {
                    "date": date_value,
                    "open": bar.get("o"),
                    "high": bar.get("h"),
                    "low": bar.get("l"),
                    "close": bar.get("c"),
                    "volume": bar.get("v"),
                }
            )

        return normalized
