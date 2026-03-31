from datetime import datetime, timedelta
from urllib.parse import quote

import requests


class DukeMarketApiUnavailable(Exception):
    """Raised when the external market data provider is temporarily unreachable."""


class DukeMarketApiService:
    """Small client for the external market data API."""

    _provider_disabled_until = None
    SYMBOL_ALIASES = {
        "BRK.B": "BRK-B",
        "BRK/A": "BRK-A",
        "BRK/B": "BRK-B",
        "BF.B": "BF-B",
        "BF/A": "BF-A",
        "BF/B": "BF-B",
    }

    def __init__(self, base_url, token, timeout=3):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def is_configured(self):
        return bool(self.token)

    def is_available(self):
        disabled_until = self.__class__._provider_disabled_until
        return disabled_until is None or datetime.utcnow() >= disabled_until

    def get_daily_prices(self, symbol, limit):
        return self._get(
            f"/stocks/{self._normalize_symbol(symbol)}/prices/daily",
            params={"limit": limit}
        )

    def get_company_overview(self, symbol):
        return self._get(f"/stocks/{self._normalize_symbol(symbol)}/overview")

    def get_stock_news(self, symbol, limit=5):
        return self._get(
            f"/stocks/{self._normalize_symbol(symbol)}/news",
            params={"limit": limit},
        )

    def mark_unavailable(self, cooldown_seconds=120):
        self.__class__._provider_disabled_until = datetime.utcnow() + timedelta(seconds=cooldown_seconds)

    def _normalize_symbol(self, symbol):
        normalized = str(symbol).strip().upper()
        normalized = self.SYMBOL_ALIASES.get(normalized, normalized)
        return quote(normalized, safe="")

    def _get(self, path, params=None):
        if not self.is_available():
            raise DukeMarketApiUnavailable("Market data provider is temporarily disabled after a recent connection failure.")

        try:
            response = requests.get(
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.token}"},
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            if isinstance(error, requests.exceptions.HTTPError) and error.response is not None and error.response.status_code < 500:
                raise

            self.mark_unavailable()
            raise DukeMarketApiUnavailable(str(error)) from error
