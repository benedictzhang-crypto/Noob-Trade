import os
import secrets
from pathlib import Path


DEFAULT_MATCH_SCORING_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK.B", "LLY", "AVGO", "JPM",
    "V", "XOM", "UNH", "MA", "COST", "JNJ", "HD", "ORCL", "PG", "MRK",
    "NFLX", "ABBV", "BAC", "KO", "AMD", "CVX", "PEP", "CRM", "WMT", "TMO",
    "ACN", "CSCO", "MCD", "ABT", "IBM", "GE", "LIN", "DIS", "ADBE", "NOW",
    "INTU", "QCOM", "CAT", "TXN", "AXP", "AMAT", "BKNG", "UBER", "GS", "SPY",
]


def _normalize_postgres_url(raw_url):
    if not raw_url:
        return raw_url

    normalized = raw_url.strip()
    if normalized.startswith("postgres://"):
        return normalized.replace("postgres://", "postgresql+psycopg://", 1)
    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", "postgresql+psycopg://", 1)
    return normalized


def _default_engine_options():
    database_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("APP_DATABASE_URL")
        or ""
    ).strip().lower()
    if database_url.startswith("postgres://") or database_url.startswith("postgresql://"):
        return {}
    return {
        "connect_args": {
            "timeout": 30,
            "check_same_thread": False,
        }
    }


def _parse_symbol_list(raw_symbols, fallback=None):
    if not raw_symbols:
        return list(fallback or [])

    parsed = []
    seen = set()

    for item in str(raw_symbols).split(","):
        symbol = item.strip().upper()
        if not symbol or symbol in seen:
            continue
        parsed.append(symbol)
        seen.add(symbol)

    return parsed or list(fallback or [])


def _resolve_environment():
    explicit = os.getenv("APP_ENV", "").strip().lower()
    if explicit:
        return explicit

    if os.getenv("RENDER", "").strip().lower() == "true":
        return "production"

    database_url = (os.getenv("DATABASE_URL") or os.getenv("APP_DATABASE_URL") or "").strip().lower()
    if database_url.startswith("postgres://") or database_url.startswith("postgresql://"):
        return "production"

    return "development"


def _is_production_environment():
    return _resolve_environment() == "production"


class Config:
    """Simple application settings for local development."""

    @staticmethod
    def _normalize_postgres_url(raw_url):
        return _normalize_postgres_url(raw_url)

    @staticmethod
    def _parse_admin_accounts():
        raw_accounts = os.getenv(
            "ADMIN_ACCOUNTS",
            "zzzzhly@126.com|Happy20252026|Noob Trade Admin,690991780@qq.com|mmd750114|Noob Trade Admin 2",
        )
        parsed_accounts = []

        for item in raw_accounts.split(","):
            email, password, *rest = [part.strip() for part in item.split("|")]
            if not email or not password:
                continue

            parsed_accounts.append(
                {
                    "email": email.lower(),
                    "password": password,
                    "full_name": (rest[0] if rest else "") or "Noob Trade Admin",
                }
            )

        return parsed_accounts

    @staticmethod
    def _default_database_uri():
        configured_url = os.getenv("DATABASE_URL")
        if configured_url:
            return _normalize_postgres_url(configured_url)

        if _is_production_environment():
            backend_dir = Path(__file__).resolve().parent
            sqlite_path = backend_dir / "noobtrade_local.db"
            return f"sqlite:///{sqlite_path}"

        backend_dir = Path(__file__).resolve().parent
        sqlite_path = backend_dir / "noobtrade_local.db"
        return f"sqlite:///{sqlite_path}"

    @staticmethod
    def _default_app_database_uri():
        configured_url = os.getenv("APP_DATABASE_URL")
        if configured_url:
            return _normalize_postgres_url(configured_url)

        configured_primary = os.getenv("DATABASE_URL")
        if configured_primary:
            return _normalize_postgres_url(configured_primary)

        if _is_production_environment():
            backend_dir = Path(__file__).resolve().parent
            sqlite_path = backend_dir / "noobtrade_user.db"
            return f"sqlite:///{sqlite_path}"

        backend_dir = Path(__file__).resolve().parent
        sqlite_path = backend_dir / "noobtrade_user.db"
        return f"sqlite:///{sqlite_path}"

    @staticmethod
    def _production_database_config_error():
        if not _is_production_environment():
            return None

        primary_url = (os.getenv("DATABASE_URL") or "").strip()
        app_url = (os.getenv("APP_DATABASE_URL") or "").strip()

        if not primary_url and not app_url:
            return "DATABASE_URL or APP_DATABASE_URL is missing in production."

        if not primary_url:
            return "DATABASE_URL is missing in production."

        return None

    ENVIRONMENT = _resolve_environment()
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true" and ENVIRONMENT != "production"
    USE_RELOADER = os.getenv("FLASK_USE_RELOADER", "false").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    CORS_ORIGINS = [
        origin.strip()
        for origin in (
            os.getenv(
                "CORS_ORIGINS",
                "http://localhost:4173,http://127.0.0.1:4173,http://localhost:5173,http://127.0.0.1:5173,https://noobtrade.com,https://www.noobtrade.com"
            )
            + ","
            + os.getenv("EXTERNAL_APP_CORS_ORIGINS", "")
        ).split(",")
        if origin.strip()
    ]
    DEFAULT_LOOKBACK = 30
    DEFAULT_INTERVAL = "daily"
    DEFAULT_INDICATORS = ["MA", "EMA", "MACD", "BOLL", "RSI", "VOL", "KDJ", "OI", "OBV"]
    PRECOMPUTE_DEMO_SYMBOLS = ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "AVGO", "TSLA", "BRK.B", "SPY", "QQQ"]
    MATCH_SCORING_SYMBOLS = _parse_symbol_list(
        os.getenv("MATCH_SCORING_SYMBOLS"),
        DEFAULT_MATCH_SCORING_SYMBOLS,
    )
    MARKET_DATA_BASE_URL = os.getenv(
        "MARKET_DATA_BASE_URL",
        "https://marketdata.colab.duke.edu/api/v1"
    )
    MARKET_DATA_TOKEN = os.getenv("MARKET_DATA_TOKEN", "")
    MARKET_DATA_PROVIDER = os.getenv("MARKET_DATA_PROVIDER", "auto").strip().lower()
    MARKET_DATA_TIMEOUT_SECONDS = float(os.getenv("MARKET_DATA_TIMEOUT_SECONDS", "3.5"))
    MARKET_DATA_COOLDOWN_SECONDS = int(os.getenv("MARKET_DATA_COOLDOWN_SECONDS", "10"))
    MARKET_DATA_CACHE_TTL_SECONDS = int(os.getenv("MARKET_DATA_CACHE_TTL_SECONDS", "90"))
    MARKET_DATA_INTRADAY_CACHE_TTL_SECONDS = int(os.getenv("MARKET_DATA_INTRADAY_CACHE_TTL_SECONDS", "60"))
    MARKET_DATA_OVERVIEW_CACHE_TTL_SECONDS = int(os.getenv("MARKET_DATA_OVERVIEW_CACHE_TTL_SECONDS", "900"))
    ANALYSIS_RESPONSE_CACHE_TTL_SECONDS = int(os.getenv("ANALYSIS_RESPONSE_CACHE_TTL_SECONDS", "300"))
    MATCH_PREVIEW_CACHE_TTL_SECONDS = int(os.getenv("MATCH_PREVIEW_CACHE_TTL_SECONDS", "900"))
    STOCK_PATTERN_SNAPSHOT_WARM_ON_START = os.getenv("STOCK_PATTERN_SNAPSHOT_WARM_ON_START", "true").lower() == "true"
    STOCK_ANALYSIS_CACHE_WARM_ON_START = os.getenv("STOCK_ANALYSIS_CACHE_WARM_ON_START", "true").lower() == "true"
    STOCK_ANALYSIS_CACHE_WARM_SYMBOLS = _parse_symbol_list(
        os.getenv("STOCK_ANALYSIS_CACHE_WARM_SYMBOLS"),
        ["AAPL", "NVDA", "TSLA", "SPY", "MSFT", "AMZN"],
    )
    PERIODIC_CACHE_WARM_ENABLED = os.getenv("PERIODIC_CACHE_WARM_ENABLED", "true").lower() == "true"
    PERIODIC_CACHE_WARM_INITIAL_DELAY_SECONDS = int(os.getenv("PERIODIC_CACHE_WARM_INITIAL_DELAY_SECONDS", "60"))
    PERIODIC_CACHE_WARM_INTERVAL_SECONDS = int(os.getenv("PERIODIC_CACHE_WARM_INTERVAL_SECONDS", "240"))
    PERIODIC_CACHE_WARM_STOCK_SYMBOLS = _parse_symbol_list(
        os.getenv("PERIODIC_CACHE_WARM_STOCK_SYMBOLS"),
        ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN"],
    )
    PERIODIC_CACHE_WARM_CRYPTO_SYMBOLS = _parse_symbol_list(
        os.getenv("PERIODIC_CACHE_WARM_CRYPTO_SYMBOLS"),
        ["BTC", "ETH", "SOL", "OKB"],
    )
    ALPACA_DATA_BASE_URL = os.getenv("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets/v2")
    YAHOO_DATA_BASE_URL = os.getenv("YAHOO_DATA_BASE_URL", "https://query1.finance.yahoo.com")
    OKX_DATA_BASE_URL = os.getenv("OKX_DATA_BASE_URL", "https://www.okx.com")
    COINGECKO_DATA_BASE_URL = os.getenv("COINGECKO_DATA_BASE_URL", "https://api.coingecko.com/api/v3")
    CRYPTO_PATTERN_STORE_PATH = os.getenv(
        "CRYPTO_PATTERN_STORE_PATH",
        str(Path(__file__).resolve().parent / "data" / "noobtrade_crypto_pattern_store.sqlite"),
    )
    CRYPTO_PATTERN_STORE_BACKEND = os.getenv("CRYPTO_PATTERN_STORE_BACKEND", "auto").strip().lower()
    CRYPTO_PATTERN_STORE_DATABASE_URL = os.getenv("CRYPTO_PATTERN_STORE_DATABASE_URL", os.getenv("DATABASE_URL", "")).strip()
    CRYPTO_PATTERN_STORE_WARM_ON_START = os.getenv("CRYPTO_PATTERN_STORE_WARM_ON_START", "true").lower() == "true"
    CRYPTO_PATTERN_STORE_WARM_SYMBOLS = _parse_symbol_list(
        os.getenv("CRYPTO_PATTERN_STORE_WARM_SYMBOLS"),
        ["BTC", "ETH", "SOL", "OKB", "DOGE", "ADA", "LINK", "AVAX"],
    )
    CRYPTO_EXCLUDE_STABLECOINS = os.getenv("CRYPTO_EXCLUDE_STABLECOINS", "true").lower() == "true"
    ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", os.getenv("APCA_API_KEY_ID", ""))
    ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET", os.getenv("APCA_API_SECRET_KEY", ""))
    ALPACA_DATA_FEED = os.getenv("ALPACA_DATA_FEED", "iex")
    ENABLE_DEMO_FALLBACK = os.getenv("ENABLE_DEMO_FALLBACK", "true").lower() == "true"
    ENABLE_DEMO_FALLBACK_ALL_SYMBOLS = os.getenv("ENABLE_DEMO_FALLBACK_ALL_SYMBOLS", "true").lower() == "true"
    DEMO_FALLBACK_SYMBOLS = _parse_symbol_list(
        os.getenv("DEMO_FALLBACK_SYMBOLS"),
        PRECOMPUTE_DEMO_SYMBOLS,
    )
    USE_MOCK_FALLBACK = os.getenv("USE_MOCK_FALLBACK", "true").lower() == "true"
    PERSIST_ANALYSIS_RUNS = os.getenv("PERSIST_ANALYSIS_RUNS", "false").lower() == "true"
    ADMIN_ACCOUNTS = _parse_admin_accounts.__func__()
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "zzzzhly@126.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Happy20252026")
    ADMIN_FULL_NAME = os.getenv("ADMIN_FULL_NAME", "Noob Trade Admin")
    ADMIN_LOGIN_CODE_REQUIRED = os.getenv("ADMIN_LOGIN_CODE_REQUIRED", "false").lower() == "true"
    LOGIN_CODE_EXPIRY_MINUTES = int(os.getenv("LOGIN_CODE_EXPIRY_MINUTES", "10"))
    EMAIL_VERIFICATION_CODE_EXPIRY_MINUTES = int(os.getenv("EMAIL_VERIFICATION_CODE_EXPIRY_MINUTES", "15"))
    PASSWORD_RESET_CODE_EXPIRY_MINUTES = int(os.getenv("PASSWORD_RESET_CODE_EXPIRY_MINUTES", "15"))
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    SMTP_TIMEOUT_SECONDS = float(os.getenv("SMTP_TIMEOUT_SECONDS", "20"))
    SMTP_SEND_ATTEMPTS = int(os.getenv("SMTP_SEND_ATTEMPTS", "3"))
    SMTP_RETRY_DELAY_SECONDS = float(os.getenv("SMTP_RETRY_DELAY_SECONDS", "0.8"))
    EMAIL_FROM = os.getenv("EMAIL_FROM", "")
    ALLOW_LOCAL_EMAIL_BYPASS = os.getenv("ALLOW_LOCAL_EMAIL_BYPASS", "false").lower() == "true"
    APP_NAME = os.getenv("APP_NAME", "Noob Trade")
    APP_BASE_URL = os.getenv("APP_BASE_URL", "https://noobtrade.onrender.com")
    SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", os.getenv("EMAIL_FROM", "support@noobtrade.com"))
    SUPPORT_PHONE = os.getenv("SUPPORT_PHONE", "+1 (800) 555-0149")
    X_URL = os.getenv("X_URL", "https://x.com/noobtrade")
    INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "https://noobtrade.onrender.com")
    DISCORD_URL = os.getenv("DISCORD_URL", "https://discord.gg/noobtrade")
    ASSISTANT_INTENT_PROVIDER = os.getenv("ASSISTANT_INTENT_PROVIDER", "openai").strip().lower()
    ASSISTANT_INTENT_MODEL = os.getenv("ASSISTANT_INTENT_MODEL", "gpt-4o-mini")
    ASSISTANT_INTENT_TIMEOUT_SECONDS = float(os.getenv("ASSISTANT_INTENT_TIMEOUT_SECONDS", "3.5"))
    ASSISTANT_RASA_URL = os.getenv("ASSISTANT_RASA_URL", "").strip()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    SQLALCHEMY_DATABASE_URI = _default_database_uri.__func__()
    SQLALCHEMY_BINDS = {
        "app": _default_app_database_uri.__func__(),
    }
    PRODUCTION_DATABASE_CONFIG_ERROR = _production_database_config_error.__func__()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _default_engine_options()
    SQLITE_DESTRUCTIVE_RECOVERY = os.getenv("SQLITE_DESTRUCTIVE_RECOVERY", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PASSWORD_HASH_METHOD = os.getenv("PASSWORD_HASH_METHOD", "pbkdf2:sha256:600000")
