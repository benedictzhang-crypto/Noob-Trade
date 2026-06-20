import time
from datetime import datetime, timedelta, timezone

import requests
from requests.adapters import HTTPAdapter

from services.duke_market_api_service import DukeMarketApiUnavailable


class CryptoMarketApiService:
    """Free crypto market data client backed by no-key public endpoints."""

    _provider_disabled_until = None
    _provider_failure_count = 0
    _top_assets_cache = None
    _top_assets_expires_at = None
    _okx_spot_inst_ids_cache = None
    _okx_spot_inst_ids_expires_at = None
    _okx_usdt_assets_cache = None
    _okx_usdt_assets_expires_at = None

    STABLECOIN_SYMBOLS = {
        "USDT",
        "USDC",
        "DAI",
        "FDUSD",
        "TUSD",
        "USDE",
        "USDS",
        "PYUSD",
        "BUSD",
    }
    SYMBOL_ALIASES = {
        "XBT": "BTC",
        "WBTC": "BTC",
    }
    OKX_INTERVALS = {
        "1min": "1m",
        "5min": "5m",
        "15min": "15m",
        "30min": "30m",
        "1hour": "1H",
        "hourly": "1H",
        "daily": "1Dutc",
    }

    def __init__(
        self,
        okx_base_url="https://www.okx.com",
        coingecko_base_url="https://api.coingecko.com/api/v3",
        timeout=3.5,
        cooldown_seconds=10,
        exclude_stablecoins=False,
    ):
        self.okx_base_url = okx_base_url.rstrip("/")
        self.coingecko_base_url = coingecko_base_url.rstrip("/")
        self.timeout = timeout
        self.cooldown_seconds = cooldown_seconds
        self.exclude_stablecoins = bool(exclude_stablecoins)
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=12, pool_maxsize=12)
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

    def mark_unavailable(self, cooldown_seconds=None):
        cooldown = self.cooldown_seconds if cooldown_seconds is None else cooldown_seconds
        self.__class__._provider_disabled_until = datetime.utcnow() + timedelta(seconds=cooldown)

    def mark_available(self):
        self.__class__._provider_disabled_until = None
        self.__class__._provider_failure_count = 0

    def get_daily_prices(self, symbol, limit):
        requested_limit = max(1, int(limit or 3650))
        try:
            bars = self._get_okx_candles(
                symbol,
                interval="daily",
                limit=requested_limit,
                include_time=False,
            )
            if bars:
                self.mark_available()
                return {"data": bars, "meta": {"provider": "OKX public spot", "symbol": self._okx_inst_id(symbol)}}
        except Exception:
            self._track_soft_failure()

        raise DukeMarketApiUnavailable(f"No OKX daily candles returned for {self._okx_inst_id(symbol)}.")

    def get_intraday_prices(self, symbol, interval, limit=390):
        requested_limit = max(1, int(limit or 390))
        interval_key = str(interval or "5min").lower()

        try:
            bars = self._get_okx_candles(
                symbol,
                interval=interval_key,
                limit=requested_limit,
                include_time=True,
            )
            if bars:
                self.mark_available()
                return {"data": bars, "meta": {"provider": "OKX public spot", "symbol": self._okx_inst_id(symbol)}}
        except Exception:
            self._track_soft_failure()

        raise DukeMarketApiUnavailable(f"No OKX {interval_key} candles returned for {self._okx_inst_id(symbol)}.")

    def get_company_overview(self, symbol):
        symbol_code = self._normalize_asset_symbol(symbol)
        asset = self._find_asset_metadata(symbol_code)
        return {
            "data": {
                "symbol": symbol_code,
                "companyName": asset.get("name") or f"{symbol_code} Crypto",
                "sector": "Crypto",
                "industry": asset.get("category") or "Digital Asset",
                "exchange": "OKX",
                "marketCap": asset.get("market_cap"),
                "marketCapRank": asset.get("market_cap_rank"),
            }
        }

    def get_stock_news(self, symbol, limit=5):
        del symbol, limit
        return {"data": []}

    def get_top_market_assets(self, limit=50):
        requested_limit = max(1, min(int(limit or 50), 250))
        page_size = min(250, requested_limit * 2 if self.exclude_stablecoins else requested_limit)
        now = datetime.utcnow()
        if (
            self.__class__._top_assets_cache is not None
            and self.__class__._top_assets_expires_at is not None
            and self.__class__._top_assets_expires_at > now
            and len(self.__class__._top_assets_cache) >= requested_limit
        ):
            return self.__class__._top_assets_cache[:requested_limit]

        try:
            response = self.session.get(
                f"{self.coingecko_base_url}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": page_size,
                    "page": 1,
                    "sparkline": "false",
                    "price_change_percentage": "24h",
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            assets = [self._normalize_coingecko_asset(item) for item in payload if isinstance(item, dict)]
            assets = [item for item in assets if item.get("symbol")]
            if self.exclude_stablecoins:
                assets = [item for item in assets if item["symbol"] not in self.STABLECOIN_SYMBOLS]
            if assets:
                self.__class__._top_assets_cache = assets
                self.__class__._top_assets_expires_at = now + timedelta(minutes=30)
                return assets[:requested_limit]
        except requests.exceptions.RequestException:
            self._track_soft_failure()

        fallback_assets = self._fallback_top_assets()
        return fallback_assets[:requested_limit]

    def get_okx_usdt_market_assets(self, limit=250):
        requested_limit = max(1, min(int(limit or 250), 300))
        now = datetime.utcnow()
        if (
            self.__class__._okx_usdt_assets_cache is not None
            and self.__class__._okx_usdt_assets_expires_at is not None
            and self.__class__._okx_usdt_assets_expires_at > now
            and len(self.__class__._okx_usdt_assets_cache) >= requested_limit
        ):
            return self.__class__._okx_usdt_assets_cache[:requested_limit]

        try:
            inst_ids = self.get_okx_spot_inst_ids()
            okx_usdt_symbols = {
                inst_id.rsplit("-", 1)[0]
                for inst_id in inst_ids
                if inst_id.endswith("-USDT") and "-" in inst_id
            }
            okx_usdt_symbols = {
                symbol
                for symbol in okx_usdt_symbols
                if symbol and (not self.exclude_stablecoins or symbol not in self.STABLECOIN_SYMBOLS)
            }
            ranked_assets = []
            seen_symbols = set()

            for asset in self.get_top_market_assets(limit=250):
                symbol = asset.get("symbol")
                if not symbol or symbol not in okx_usdt_symbols or symbol in seen_symbols:
                    continue
                ranked_assets.append(
                    {
                        **asset,
                        "category": asset.get("category") or "OKX Spot",
                        "exchange": "OKX",
                        "okx_inst_id": f"{symbol}-USDT",
                    }
                )
                seen_symbols.add(symbol)

            for symbol in sorted(okx_usdt_symbols):
                if symbol in seen_symbols:
                    continue
                ranked_assets.append(
                    {
                        "symbol": symbol,
                        "name": f"{symbol} Crypto",
                        "category": "OKX Spot",
                        "exchange": "OKX",
                        "okx_inst_id": f"{symbol}-USDT",
                    }
                )
                seen_symbols.add(symbol)

            if ranked_assets:
                self.__class__._okx_usdt_assets_cache = ranked_assets
                self.__class__._okx_usdt_assets_expires_at = now + timedelta(hours=6)
                return ranked_assets[:requested_limit]
        except requests.exceptions.RequestException:
            self._track_soft_failure()
        except Exception:
            self._track_soft_failure()

        return self.get_top_market_assets(limit=requested_limit)

    def get_okx_spot_inst_ids(self):
        now = datetime.utcnow()
        if (
            self.__class__._okx_spot_inst_ids_cache is not None
            and self.__class__._okx_spot_inst_ids_expires_at is not None
            and self.__class__._okx_spot_inst_ids_expires_at > now
        ):
            return self.__class__._okx_spot_inst_ids_cache

        response = self.session.get(
            f"{self.okx_base_url}/api/v5/public/instruments",
            params={"instType": "SPOT"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if str(payload.get("code")) != "0":
            raise DukeMarketApiUnavailable(payload.get("msg") or "OKX instruments request failed.")

        inst_ids = {
            str(item.get("instId") or "").upper()
            for item in payload.get("data") or []
            if item.get("instId")
        }
        self.__class__._okx_spot_inst_ids_cache = inst_ids
        self.__class__._okx_spot_inst_ids_expires_at = now + timedelta(hours=6)
        return inst_ids

    def has_okx_spot_pair(self, symbol):
        return self._okx_inst_id(symbol).upper() in self.get_okx_spot_inst_ids()

    def _normalize_asset_symbol(self, symbol):
        normalized = str(symbol or "").strip().upper()
        normalized = normalized.replace(" ", "")

        for separator in ("/", "-", "_"):
            if separator in normalized:
                normalized = normalized.split(separator, 1)[0]
                break

        for suffix in ("USDT", "USDC", "BUSD", "USD"):
            if normalized.endswith(suffix) and len(normalized) > len(suffix) + 1:
                normalized = normalized[: -len(suffix)]
                break

        return self.SYMBOL_ALIASES.get(normalized, normalized)

    def _okx_inst_id(self, symbol):
        return f"{self._normalize_asset_symbol(symbol)}-USDT"

    def _get_okx_candles(self, symbol, interval, limit, include_time):
        if not self.is_available():
            raise DukeMarketApiUnavailable("OKX crypto data provider is temporarily disabled after a recent connection failure.")

        inst_id = self._okx_inst_id(symbol)
        interval_key = str(interval or "15min").lower()
        bar = self.OKX_INTERVALS.get(interval_key, "15m")
        remaining = max(1, int(limit or 300))
        after = None
        rows = []

        while remaining > 0:
            batch_limit = min(remaining, 300)
            params = {
                "instId": inst_id,
                "bar": bar,
                "limit": str(batch_limit),
            }
            if after is not None:
                params["after"] = str(after)

            response = self.session.get(
                f"{self.okx_base_url}/api/v5/market/history-candles",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if str(payload.get("code")) != "0":
                raise DukeMarketApiUnavailable(payload.get("msg") or f"OKX candles failed for {inst_id}.")

            batch = payload.get("data") or []
            if not batch:
                break

            rows.extend(batch)
            oldest_ts = int(batch[-1][0])
            if after == oldest_ts or len(batch) < batch_limit:
                break
            after = oldest_ts
            remaining -= len(batch)
            time.sleep(0.11)

        bars = self._normalize_okx_bars(rows, include_time=include_time)
        return bars[: max(1, int(limit or 300))]

    def _normalize_okx_bars(self, rows, include_time):
        bars_by_time = {}
        for row in rows:
            if not isinstance(row, list) or len(row) < 6:
                continue

            opened_at = datetime.fromtimestamp(int(row[0]) / 1000, tz=timezone.utc)
            date_value = opened_at.isoformat() if include_time else opened_at.date().isoformat()
            try:
                close_value = float(row[4])
            except (TypeError, ValueError):
                continue

            bars_by_time[date_value] = {
                "date": date_value,
                "open": self._to_float(row[1], close_value),
                "high": self._to_float(row[2], close_value),
                "low": self._to_float(row[3], close_value),
                "close": close_value,
                "volume": self._volume_to_int(row[5]),
            }

        normalized = list(bars_by_time.values())
        normalized.sort(key=lambda row: row["date"], reverse=True)
        return normalized

    def _find_asset_metadata(self, symbol):
        for asset in self.get_top_market_assets(limit=250):
            if asset.get("symbol") == symbol:
                return asset
        return {"symbol": symbol, "name": f"{symbol} Crypto"}

    def _normalize_coingecko_asset(self, item):
        symbol = self._normalize_asset_symbol(item.get("symbol"))
        return {
            "id": item.get("id"),
            "symbol": symbol,
            "name": item.get("name") or symbol,
            "image": item.get("image"),
            "current_price": item.get("current_price"),
            "market_cap": item.get("market_cap"),
            "market_cap_rank": item.get("market_cap_rank"),
            "total_volume": item.get("total_volume"),
            "price_change_percentage_24h": item.get("price_change_percentage_24h"),
            "last_updated": item.get("last_updated"),
            "category": "Market Cap Top Crypto",
        }

    def _fallback_top_assets(self):
        symbols = [
            ("BTC", "Bitcoin"),
            ("ETH", "Ethereum"),
            ("BNB", "BNB"),
            ("SOL", "Solana"),
            ("XRP", "XRP"),
            ("DOGE", "Dogecoin"),
            ("ADA", "Cardano"),
            ("TRX", "TRON"),
            ("AVAX", "Avalanche"),
            ("LINK", "Chainlink"),
            ("TON", "Toncoin"),
            ("SHIB", "Shiba Inu"),
            ("DOT", "Polkadot"),
            ("BCH", "Bitcoin Cash"),
            ("NEAR", "NEAR Protocol"),
            ("LTC", "Litecoin"),
            ("UNI", "Uniswap"),
            ("ICP", "Internet Computer"),
            ("APT", "Aptos"),
            ("ETC", "Ethereum Classic"),
            ("HBAR", "Hedera"),
            ("ATOM", "Cosmos"),
            ("FIL", "Filecoin"),
            ("ARB", "Arbitrum"),
            ("IMX", "Immutable"),
            ("STX", "Stacks"),
            ("OP", "Optimism"),
            ("INJ", "Injective"),
            ("SUI", "Sui"),
            ("MKR", "Maker"),
            ("AAVE", "Aave"),
            ("GRT", "The Graph"),
            ("RUNE", "THORChain"),
            ("LDO", "Lido DAO"),
            ("SEI", "Sei"),
            ("RENDER", "Render"),
            ("FET", "Artificial Superintelligence Alliance"),
            ("ALGO", "Algorand"),
            ("VET", "VeChain"),
            ("MATIC", "Polygon"),
            ("FTM", "Fantom"),
            ("XLM", "Stellar"),
            ("MNT", "Mantle"),
            ("OKB", "OKB"),
            ("CRO", "Cronos"),
            ("KAS", "Kaspa"),
            ("TIA", "Celestia"),
            ("JUP", "Jupiter"),
            ("WIF", "dogwifhat"),
            ("PEPE", "Pepe"),
        ]
        return [
            {
                "symbol": symbol,
                "name": name,
                "market_cap_rank": index,
                "category": "Fallback Top Crypto",
            }
            for index, (symbol, name) in enumerate(symbols, start=1)
            if not (self.exclude_stablecoins and symbol in self.STABLECOIN_SYMBOLS)
        ]

    def _track_soft_failure(self):
        self.__class__._provider_failure_count += 1

    def _to_float(self, value, default=0.0):
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _volume_to_int(self, value):
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0
