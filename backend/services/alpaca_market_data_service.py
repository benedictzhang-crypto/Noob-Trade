import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

try:
    import certifi
except Exception:
    certifi = None


class AlpacaMarketDataUnavailable(RuntimeError):
    """Raised when Alpaca market data cannot be fetched."""


class AlpacaMarketDataService:
    def __init__(self, base_url="", api_key="", secret_key="", timeout=5.0):
        self.base_url = str(base_url or "").rstrip("/")
        self.api_key = str(api_key or "").strip()
        self.secret_key = str(secret_key or "").strip()
        self.timeout = float(timeout or 5.0)

    def is_configured(self):
        return bool(self.base_url and self.api_key and self.secret_key)

    def _ssl_context(self):
        if certifi is not None:
            return ssl.create_default_context(cafile=certifi.where())
        return ssl.create_default_context()

    def _headers(self):
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Accept": "application/json",
            "User-Agent": "NoobTrade/1.0",
        }

    def get_stock_snapshot(self, symbol):
        if not self.is_configured():
            raise AlpacaMarketDataUnavailable("Alpaca market data service is not configured.")

        route = f"/v2/stocks/snapshots?symbols={urllib.parse.quote(symbol.upper())}"
        request = urllib.request.Request(
            f"{self.base_url}{route}",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
                context=self._ssl_context(),
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise AlpacaMarketDataUnavailable(f"Alpaca HTTP {exc.code}: {body[:200]}") from exc
        except Exception as exc:
            raise AlpacaMarketDataUnavailable(str(exc)) from exc

        snapshots = payload.get("snapshots") or {}
        snapshot = snapshots.get(symbol.upper()) or snapshots.get(symbol) or {}
        if not snapshot:
            raise AlpacaMarketDataUnavailable(f"No Alpaca snapshot returned for {symbol.upper()}.")
        return snapshot
