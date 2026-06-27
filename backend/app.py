from pathlib import Path
from datetime import datetime
import sqlite3
import threading
import time

from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask import send_from_directory
from sqlalchemy import inspect, text
from dotenv import load_dotenv

load_dotenv()

from config import Config
from extensions import db
from models import analysis, auth, crypto_history, market_data, trading
from models.auth import LoginActivity, LoginVerificationCode, User
from routes.assistant_routes import assistant_blueprint
from routes.auth_routes import auth_blueprint
from routes.crypto_routes import crypto_blueprint
from routes.stock_routes import stock_blueprint
from services.rate_limit_service import rate_limit_service
from services.security_service import hash_secret, verify_secret


def _generate_compatible_password_hash(app, password):
    del app
    return hash_secret(password)


def _is_sqlite_app(app):
    database_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    return database_uri.startswith("sqlite:///")


def _sqlite_database_path(app):
    if not _is_sqlite_app(app):
        return None

    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    return Path(database_uri.removeprefix("sqlite:///"))


def _auth_database_uri(app):
    binds = app.config.get("SQLALCHEMY_BINDS") or {}
    auth_uri = binds.get("app", "")

    if isinstance(auth_uri, dict):
        return auth_uri.get("url", "")

    return auth_uri or ""


def _auth_sqlite_database_path(app):
    auth_uri = _auth_database_uri(app)
    if not auth_uri.startswith("sqlite:///"):
        return None

    return Path(auth_uri.removeprefix("sqlite:///"))


def _assert_production_postgres(app):
    environment = str(app.config.get("ENVIRONMENT", "")).lower()
    if environment != "production":
        return True, None

    primary_uri = str(app.config.get("SQLALCHEMY_DATABASE_URI", "") or "")
    auth_uri = str(_auth_database_uri(app) or "")

    if not primary_uri.startswith("postgresql") or not auth_uri.startswith("postgresql"):
        return False, "NoobTrade production must run on Postgres for both primary and auth storage."

    return True, None


def _build_engine_options(app):
    base_options = app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {}
    connect_args = dict(base_options.get("connect_args") or {})
    primary_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    auth_uri = _auth_database_uri(app)

    sqlite_only_keys = {"timeout", "check_same_thread"}
    uses_only_sqlite = primary_uri.startswith("sqlite:///") and (not auth_uri or auth_uri.startswith("sqlite:///"))

    if uses_only_sqlite:
        return base_options

    filtered_connect_args = {
        key: value
        for key, value in connect_args.items()
        if key not in sqlite_only_keys
    }

    normalized = dict(base_options)
    if filtered_connect_args:
        normalized["connect_args"] = filtered_connect_args
    else:
        normalized.pop("connect_args", None)

    return normalized


def _parse_sqlite_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value

    normalized = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def ensure_auth_schema(app):
    with app.app_context():
        inspector = inspect(db.engines["app"])
        table_names = set(inspector.get_table_names())

        if "users" not in table_names or "login_verification_codes" not in table_names or "login_activities" not in table_names:
            db.create_all()
            return

        user_columns = {column["name"] for column in inspector.get_columns("users")}

        with db.engines["app"].begin() as connection:
            if "role" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))
            if "email_verified" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0"))
            if "verified_at" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN verified_at DATETIME"))
            if "is_disabled" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN is_disabled BOOLEAN NOT NULL DEFAULT 0"))
            if "disabled_at" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN disabled_at DATETIME"))
            if "disabled_reason" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN disabled_reason VARCHAR(255)"))


def ensure_auth_postgres_sequences(app):
    with app.app_context():
        auth_engine = db.engines["app"]
        if auth_engine.dialect.name != "postgresql":
            return

        table_names = ("users", "login_verification_codes", "login_activities")

        with auth_engine.begin() as connection:
            for table_name in table_names:
                sequence_name = connection.execute(
                    text("SELECT pg_get_serial_sequence(:qualified_table, 'id')"),
                    {"qualified_table": f"public.{table_name}"},
                ).scalar()

                if not sequence_name:
                    continue

                connection.execute(
                    text(
                        f"""
                        SELECT setval(
                            :sequence_name,
                            GREATEST(COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1, 1),
                            false
                        )
                        """
                    ),
                    {"sequence_name": sequence_name},
                )


def migrate_auth_data_to_app_db(app):
    source_path = _sqlite_database_path(app)
    target_path = _auth_sqlite_database_path(app)

    if source_path is None or target_path is None or source_path == target_path or not source_path.exists():
        return

    with app.app_context():
        if User.query.count() > 0:
            return

    source_connection = sqlite3.connect(source_path)
    source_connection.row_factory = sqlite3.Row

    try:
        cursor = source_connection.cursor()
        existing_tables = {
            row["name"]
            for row in cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        if "users" not in existing_tables:
            return

        users = cursor.execute(
            """
            SELECT id, full_name, email, password_hash, risk_profile, membership, role,
                   email_verified, verified_at, created_at
            FROM users
            ORDER BY id ASC
            """
        ).fetchall()

        verification_codes = []
        if "login_verification_codes" in existing_tables:
            verification_codes = cursor.execute(
                """
                SELECT id, user_id, email, code_hash, purpose, expires_at, used_at, created_at
                FROM login_verification_codes
                ORDER BY id ASC
                """
            ).fetchall()

        login_activities = []
        if "login_activities" in existing_tables:
            login_activities = cursor.execute(
                """
                SELECT id, user_id, email, ip_address, user_agent, device_label, location_label,
                       is_new_device, is_new_location, created_at
                FROM login_activities
                ORDER BY id ASC
                """
            ).fetchall()

        if not users:
            return

        with app.app_context():
            for row in users:
                db.session.add(User(
                    id=row["id"],
                    full_name=row["full_name"],
                    email=row["email"],
                    password_hash=row["password_hash"],
                    risk_profile=row["risk_profile"] or "Balanced",
                    membership=row["membership"] or "Regular User",
                    role=row["role"] or "user",
                    email_verified=bool(row["email_verified"]),
                    verified_at=_parse_sqlite_datetime(row["verified_at"]),
                    is_disabled=bool(row["is_disabled"]) if "is_disabled" in row.keys() else False,
                    disabled_at=_parse_sqlite_datetime(row["disabled_at"]) if "disabled_at" in row.keys() else None,
                    disabled_reason=row["disabled_reason"] if "disabled_reason" in row.keys() else None,
                    created_at=_parse_sqlite_datetime(row["created_at"]),
                ))

            for row in verification_codes:
                db.session.add(LoginVerificationCode(
                    id=row["id"],
                    user_id=row["user_id"],
                    email=row["email"],
                    code_hash=row["code_hash"],
                    purpose=row["purpose"] or "admin_login",
                    expires_at=_parse_sqlite_datetime(row["expires_at"]),
                    used_at=_parse_sqlite_datetime(row["used_at"]),
                    created_at=_parse_sqlite_datetime(row["created_at"]),
                ))

            for row in login_activities:
                db.session.add(LoginActivity(
                    id=row["id"],
                    user_id=row["user_id"],
                    email=row["email"],
                    ip_address=row["ip_address"],
                    user_agent=row["user_agent"],
                    device_label=row["device_label"],
                    location_label=row["location_label"],
                    is_new_device=bool(row["is_new_device"]),
                    is_new_location=bool(row["is_new_location"]),
                    created_at=_parse_sqlite_datetime(row["created_at"]),
                ))

            db.session.commit()
            app.logger.info(
                "Migrated %s users from shared market SQLite to local app SQLite at %s.",
                len(users),
                target_path,
            )
    finally:
        source_connection.close()


def ensure_admin_user(app):
    with app.app_context():
        configured_admins = app.config.get("ADMIN_ACCOUNTS") or []
        if not configured_admins:
            configured_admins = [
                {
                    "email": app.config["ADMIN_EMAIL"].strip().lower(),
                    "password": app.config["ADMIN_PASSWORD"],
                    "full_name": app.config["ADMIN_FULL_NAME"].strip() or "Noob Trade Admin",
                }
            ]

        configured_admins_by_email = {
            admin["email"].strip().lower(): {
                "email": admin["email"].strip().lower(),
                "password": admin["password"],
                "full_name": admin["full_name"].strip() or "Noob Trade Admin",
            }
            for admin in configured_admins
            if admin.get("email") and admin.get("password")
        }
        updated = False

        for user in User.query.filter(User.role == "admin").all():
            normalized_email = user.email.strip().lower()
            if normalized_email in configured_admins_by_email:
                continue

            user.role = "user"
            if user.membership == "Administrator":
                user.membership = "Regular User"
            updated = True

        for admin_email, admin_details in configured_admins_by_email.items():
            existing_admin = User.query.filter_by(email=admin_email).first()

            if existing_admin is None:
                existing_admin = User(
                    full_name=admin_details["full_name"],
                    email=admin_email,
                    password_hash=_generate_compatible_password_hash(app, admin_details["password"]),
                    risk_profile="Balanced",
                    membership="Administrator",
                    role="admin",
                    email_verified=True,
                    verified_at=datetime.utcnow(),
                )
                db.session.add(existing_admin)
                updated = True
                continue

            if existing_admin.full_name != admin_details["full_name"]:
                existing_admin.full_name = admin_details["full_name"]
                updated = True
            if existing_admin.role != "admin":
                existing_admin.role = "admin"
                updated = True
            if existing_admin.membership != "Administrator":
                existing_admin.membership = "Administrator"
                updated = True
            if not getattr(existing_admin, "email_verified", False):
                existing_admin.email_verified = True
                existing_admin.verified_at = datetime.utcnow()
                updated = True

            if not existing_admin.password_hash:
                existing_admin.password_hash = _generate_compatible_password_hash(app, admin_details["password"])
                updated = True
            else:
                try:
                    if not verify_secret(existing_admin.password_hash, admin_details["password"]):
                        existing_admin.password_hash = _generate_compatible_password_hash(app, admin_details["password"])
                        updated = True
                except Exception:
                    existing_admin.password_hash = _generate_compatible_password_hash(app, admin_details["password"])
                    updated = True

        if updated:
            db.session.commit()


def initialize_database(app):
    with app.app_context():
        db.create_all()

    ensure_auth_schema(app)
    ensure_auth_postgres_sequences(app)
    migrate_auth_data_to_app_db(app)
    ensure_admin_user(app)


def recover_sqlite_database(app):
    sqlite_path = _sqlite_database_path(app)
    if sqlite_path is None:
        return False

    if not app.config.get("SQLITE_DESTRUCTIVE_RECOVERY", False):
        app.logger.warning(
            "Skipping destructive SQLite recovery for %s because SQLITE_DESTRUCTIVE_RECOVERY is disabled.",
            sqlite_path,
        )
        return False

    app.logger.warning("Attempting SQLite recovery for %s", sqlite_path)

    try:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()

        if sqlite_path.exists():
            backup_path = sqlite_path.with_suffix(f".backup-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{sqlite_path.suffix}")
            sqlite_path.replace(backup_path)
            app.logger.warning("Moved SQLite database to backup path %s before recovery.", backup_path)

        initialize_database(app)
        app.logger.warning("SQLite recovery succeeded for %s", sqlite_path)
        return True
    except Exception:
        app.logger.exception("SQLite recovery failed for %s", sqlite_path)
        return False


def initialize_database_with_retries(app, attempts=5, delay_seconds=2):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            initialize_database(app)
            if attempt > 1:
                app.logger.warning("Database initialization succeeded on retry %s.", attempt)
            return
        except Exception as error:
            last_error = error
            app.logger.exception(
                "Database initialization attempt %s/%s failed.",
                attempt,
                attempts,
            )
            if attempt < attempts:
                time.sleep(delay_seconds)

    raise last_error


def _start_background_database_init(app):
    if app.config.get("_DB_INIT_READY"):
        return

    lock = app.config.setdefault("_DB_INIT_LOCK", threading.Lock())

    with lock:
        if app.config.get("_DB_INIT_READY") or app.config.get("_DB_INIT_STARTED"):
            return

        retry_cooldown = max(
            1,
            float(app.config.get("DB_INIT_RETRY_COOLDOWN_SECONDS", 10) or 10),
        )
        last_error_at = app.config.get("_DB_INIT_LAST_ERROR_AT")
        if last_error_at and time.monotonic() - last_error_at < retry_cooldown:
            return

        app.config["_DB_INIT_STARTED"] = True
        app.config["_DB_INIT_READY"] = False
        app.config["_DB_INIT_ERROR"] = None

    def _runner():
        try:
            initialize_database_with_retries(app)
            with lock:
                app.config["_DB_INIT_STARTED"] = False
                app.config["_DB_INIT_READY"] = True
                app.config["_DB_INIT_ERROR"] = None
                app.config["_DB_INIT_LAST_ERROR_AT"] = None
        except Exception as error:
            app.logger.exception("Background database initialization failed.")
            with lock:
                app.config["_DB_INIT_STARTED"] = False
                app.config["_DB_INIT_READY"] = False
                app.config["_DB_INIT_ERROR"] = str(error)
                app.config["_DB_INIT_LAST_ERROR_AT"] = time.monotonic()
            return

        try:
            with app.app_context():
                _run_stock_pattern_snapshot_warmup(app)
            _warm_crypto_pattern_store(app)
            _warm_stock_analysis_cache(app)
            _start_periodic_cache_warmer(app)
        except Exception:
            app.logger.exception("Background cache warmup failed after database initialization.")

    threading.Thread(target=_runner, daemon=True).start()


def _wait_for_database_ready(app):
    if app.config.get("_DB_INIT_READY", False):
        return True

    timeout_seconds = max(
        0,
        float(app.config.get("DB_READY_WAIT_TIMEOUT_SECONDS", 4) or 0),
    )
    poll_seconds = max(
        0.05,
        float(app.config.get("DB_READY_WAIT_POLL_SECONDS", 0.15) or 0.15),
    )
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        if app.config.get("_DB_INIT_READY", False):
            return True
        if app.config.get("_DB_INIT_ERROR") and not app.config.get("_DB_INIT_STARTED"):
            return False
        time.sleep(min(poll_seconds, max(0, deadline - time.monotonic())))

    return app.config.get("_DB_INIT_READY", False)


def _database_warming_response(app):
    error_message = (
        app.config.get("_DB_INIT_ERROR")
        or "Database is warming up. Please try again in a few seconds."
    )
    response = jsonify({"message": error_message, "retryAfterSeconds": 2})
    response.status_code = 503
    response.headers["Retry-After"] = "2"
    return response


def _warm_crypto_pattern_store(app):
    if not app.config.get("CRYPTO_PATTERN_STORE_WARM_ON_START", True):
        return

    _run_crypto_pattern_store_warmup(app, app.config.get("CRYPTO_PATTERN_STORE_WARM_SYMBOLS") or [])


def _run_crypto_pattern_store_warmup(app, symbols=None):
    try:
        from services.crypto_pattern_store_service import CryptoPatternStoreService

        result = CryptoPatternStoreService(app.config).warm_cache(
            symbols=symbols or [],
        )
        app.logger.info("Crypto pattern store warmup complete: %s", result)
    except Exception:
        app.logger.exception("Crypto pattern store warmup failed; continuing with lazy loading.")


def _warm_stock_pattern_snapshot(app):
    if not app.config.get("STOCK_PATTERN_SNAPSHOT_WARM_ON_START", True):
        return

    def _runner():
        with app.app_context():
            _run_stock_pattern_snapshot_warmup(app)

    threading.Thread(target=_runner, daemon=True).start()


def _run_stock_pattern_snapshot_warmup(app):
    try:
        from services.persistence_service import PersistenceService

        result = PersistenceService().warm_match_candidate_snapshot(
            timeframes=[app.config.get("DEFAULT_INTERVAL", "daily")],
            window_sizes=[app.config.get("DEFAULT_LOOKBACK", 30)],
        )
        app.logger.info("Stock pattern snapshot warmup complete: %s", result)
    except Exception:
        app.logger.exception("Stock pattern snapshot warmup failed; continuing with lazy loading.")


def _warm_stock_analysis_cache(app):
    if not app.config.get("STOCK_ANALYSIS_CACHE_WARM_ON_START", False):
        return

    symbols = app.config.get("STOCK_ANALYSIS_CACHE_WARM_SYMBOLS") or []
    if not symbols:
        return

    def _runner():
        with app.app_context():
            _run_stock_analysis_cache_warmup(app, symbols)

    threading.Thread(target=_runner, daemon=True).start()


def _run_stock_analysis_cache_warmup(app, symbols=None):
    symbols = symbols or []
    if not symbols:
        return

    try:
        from services.market_data_service import MarketDataService

        market_data_service = MarketDataService(app.config)
        indicators = app.config.get("DEFAULT_INDICATORS") or []
        raw_indicators = ",".join(indicators)
        warmed_symbols = []

        for symbol in symbols:
            try:
                started_at = time.time()
                market_data_service.get_stock_pattern_analysis(
                    symbol=symbol,
                    interval=app.config.get("DEFAULT_INTERVAL", "daily"),
                    chart_interval=app.config.get("DEFAULT_INTERVAL", "daily"),
                    lookback_window=app.config.get("DEFAULT_LOOKBACK", 30),
                    raw_indicators=raw_indicators,
                    default_indicators=indicators,
                    compact_response=True,
                    analysis_mode="full",
                    scoring_profile="public_equal9",
                )
                warmed_symbols.append(f"{symbol}:{time.time() - started_at:.1f}s")
            except Exception:
                app.logger.warning("Stock analysis cache warmup failed for %s.", symbol, exc_info=True)

        app.logger.info("Stock analysis cache warmup complete: %s", warmed_symbols)
    except Exception:
        app.logger.exception("Stock analysis cache warmup failed; continuing with lazy loading.")


def _run_crypto_analysis_cache_warmup(app, symbols=None):
    symbols = symbols or []
    if not symbols:
        return

    try:
        from services.crypto_market_data_service import CryptoMarketDataService

        market_data_service = CryptoMarketDataService(app.config)
        indicators = app.config.get("DEFAULT_INDICATORS") or []
        raw_indicators = ",".join(indicators)
        warmed_symbols = []

        for symbol in symbols:
            try:
                started_at = time.time()
                market_data_service.get_crypto_pattern_analysis(
                    symbol=symbol,
                    interval=app.config.get("DEFAULT_INTERVAL", "daily"),
                    lookback_window=app.config.get("DEFAULT_LOOKBACK", 30),
                    raw_indicators=raw_indicators,
                    default_indicators=indicators,
                    compact_response=True,
                    analysis_mode="full",
                )
                warmed_symbols.append(f"{symbol}:{time.time() - started_at:.1f}s")
            except Exception:
                app.logger.warning("Crypto analysis cache warmup failed for %s.", symbol, exc_info=True)

        app.logger.info("Crypto analysis cache warmup complete: %s", warmed_symbols)
    except Exception:
        app.logger.exception("Crypto analysis cache warmup failed; continuing with lazy loading.")


def _run_periodic_cache_warm_once(app):
    with app.app_context():
        _run_stock_pattern_snapshot_warmup(app)
        _run_crypto_pattern_store_warmup(app, app.config.get("PERIODIC_CACHE_WARM_CRYPTO_SYMBOLS") or [])
        _run_stock_analysis_cache_warmup(app, app.config.get("PERIODIC_CACHE_WARM_STOCK_SYMBOLS") or [])
        _run_crypto_analysis_cache_warmup(app, app.config.get("PERIODIC_CACHE_WARM_CRYPTO_SYMBOLS") or [])


def _start_periodic_cache_warmer(app):
    if not app.config.get("PERIODIC_CACHE_WARM_ENABLED", True):
        return
    if app.config.get("_PERIODIC_CACHE_WARMER_STARTED"):
        return

    app.config["_PERIODIC_CACHE_WARMER_STARTED"] = True
    interval_seconds = max(60, int(app.config.get("PERIODIC_CACHE_WARM_INTERVAL_SECONDS", 240) or 240))
    initial_delay_seconds = max(0, int(app.config.get("PERIODIC_CACHE_WARM_INITIAL_DELAY_SECONDS", 60) or 0))

    def _runner():
        if initial_delay_seconds:
            time.sleep(initial_delay_seconds)

        while True:
            started_at = time.time()
            try:
                _run_periodic_cache_warm_once(app)
            except Exception:
                app.logger.exception("Periodic cache warmup failed; continuing with lazy loading.")

            elapsed_seconds = time.time() - started_at
            time.sleep(max(30, interval_seconds - elapsed_seconds))

    threading.Thread(target=_runner, daemon=True, name="periodic-cache-warmer").start()
    app.logger.info(
        "Periodic cache warmer started: interval=%ss initial_delay=%ss",
        interval_seconds,
        initial_delay_seconds,
    )


def create_app():
    """Create and configure the Flask application."""
    project_root = Path(__file__).resolve().parent.parent
    frontend_dist = project_root / "frontend" / "dist"
    ampli_lab_dist = project_root / "backend" / "ampli_lab_site"
    static_folder = str(frontend_dist) if frontend_dist.exists() else None

    app = Flask(__name__, static_folder=static_folder, static_url_path="")
    app.config.from_object(Config)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = _build_engine_options(app)
    postgres_ok, postgres_error = _assert_production_postgres(app)
    app.config["PRODUCTION_POSTGRES_OK"] = postgres_ok
    app.config["PRODUCTION_POSTGRES_ERROR"] = postgres_error
    if not postgres_ok and postgres_error:
        app.logger.error(postgres_error)
        if str(app.config.get("ENVIRONMENT", "")).lower() == "production":
            raise RuntimeError(postgres_error)

    # Allow browser apps on the configured origin whitelist to call the API.
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )
    db.init_app(app)

    app.register_blueprint(stock_blueprint)
    app.register_blueprint(crypto_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(assistant_blueprint)

    app.config["_DB_INIT_STARTED"] = False
    app.config["_DB_INIT_READY"] = False
    app.config["_DB_INIT_ERROR"] = None
    app.config["_DB_INIT_LAST_ERROR_AT"] = None
    app.config["_DB_INIT_LOCK"] = threading.Lock()

    def _is_ampli_lab_host():
        host = request.host.split(":", 1)[0].lower()
        return host in {"amplialpha.net", "www.amplialpha.net"}

    def _is_live_market_snapshot_request():
        if request.method != "GET":
            return False

        if request.endpoint in {
            "stock.get_stock_chart",
            "stock.get_market_news",
            "crypto.get_crypto_chart",
            "crypto.get_crypto_top50",
        }:
            return True

        if request.endpoint in {"stock.get_stock", "crypto.get_crypto"}:
            analysis_mode = str(request.args.get("analysis", "")).strip().lower()
            return analysis_mode in {"search", "summary"}

        return False

    USAGE_LIMITS = {
        "search_chart": (
            {"name": "minute", "limit": 120, "windowSeconds": 60, "label": "120 requests per minute"},
        ),
        "explore": (
            {"name": "minute", "limit": 60, "windowSeconds": 60, "label": "60 explore requests per minute"},
        ),
        "single_generate": (
            {"name": "minute", "limit": 20, "windowSeconds": 60, "label": "20 Generate requests per minute"},
            {"name": "day", "limit": 200, "windowSeconds": 86400, "label": "200 Generate requests per day"},
        ),
        "dashboard_scan": (
            {"name": "minute", "limit": 5, "windowSeconds": 60, "label": "5 Dashboard Scan runs per minute"},
            {"name": "day", "limit": 80, "windowSeconds": 86400, "label": "80 Dashboard Scan runs per day"},
        ),
        "matched_detail": (
            {"name": "hour", "limit": 120, "windowSeconds": 3600, "label": "120 matched-history detail requests per hour"},
            {"name": "day", "limit": 300, "windowSeconds": 86400, "label": "300 matched-history detail requests per day"},
        ),
    }

    USAGE_LIMIT_LABELS = {
        "search_chart": "live search and chart loading",
        "explore": "Explore loading",
        "single_generate": "single-symbol Generate",
        "dashboard_scan": "Dashboard Scan",
        "matched_detail": "matched-history detail",
    }

    def _normalized_usage_email():
        return str(session.get("user_email", "")).strip().lower()

    def _split_configured_emails(value):
        if isinstance(value, (list, tuple, set)):
            raw_values = value
        else:
            raw_values = str(value or "").replace(";", ",").split(",")
        return {str(item or "").strip().lower() for item in raw_values if str(item or "").strip()}

    def _usage_actor_key(client_ip):
        email = _normalized_usage_email()
        if email:
            return f"user:{email}"
        return f"ip:{client_ip or 'unknown'}"

    def _is_usage_unlimited_user(app):
        email = _normalized_usage_email()
        role = str(session.get("user_role", "")).strip().lower()
        session_snapshot = session.get("user_snapshot")

        if isinstance(session_snapshot, dict):
            role = role or str(session_snapshot.get("role", "")).strip().lower()
            if bool(session_snapshot.get("isAdmin")):
                return True
            membership = str(session_snapshot.get("membership", "")).strip().lower()
            if any(token in membership for token in ("pro", "premium", "unlimited")):
                return True

        if role == "admin":
            return True

        configured_pro_emails = _split_configured_emails(app.config.get("NOOBTRADE_PRO_EMAILS", ""))
        if email and email in configured_pro_emails:
            return True

        return False

    def _usage_limit_category():
        if request.method != "GET":
            return None

        endpoint = request.endpoint or ""

        if endpoint in {"stock.get_stock", "crypto.get_crypto"}:
            analysis_mode = str(request.args.get("analysis", "full")).strip().lower()
            if analysis_mode in {"search", "summary"}:
                return "search_chart"
            if request.args.get("matchDetails", default=0, type=int) == 1:
                return "matched_detail"
            usage_context = str(request.args.get("usage", "")).strip().lower()
            if usage_context == "dashboard-scan" or request.args.get("scan", default=0, type=int) == 1:
                return "dashboard_scan"
            return "single_generate"

        if endpoint in {"stock.get_stock_chart", "crypto.get_crypto_chart", "stock.get_market_news"}:
            return "search_chart"

        if endpoint == "crypto.get_crypto_top50":
            return "explore"

        return None

    def _should_count_usage_event(actor_key, category):
        if category != "dashboard_scan":
            return True

        batch_id = str(request.args.get("scanBatchId", "")).strip()[:96]
        if not batch_id:
            return True

        marker_key = f"usage-seen:{actor_key}:{category}:{batch_id}"
        return rate_limit_service.mark_once(marker_key, ttl_seconds=86400)

    def _usage_limit_response(category, decision, limit_label):
        retry_after = max(1, int(decision.get("retryAfterSeconds") or 60))
        response = jsonify(
            {
                "status": "limit_exceeded",
                "code": "usage_limit_exceeded",
                "message": "You have reached the free request limit for this feature. Upgrade for unlimited requests.",
                "usageCategory": category,
                "usageLabel": USAGE_LIMIT_LABELS.get(category, "NoobTrade requests"),
                "limitLabel": limit_label,
                "retryAfterSeconds": retry_after,
                "upgrade": {
                    "required": True,
                    "planName": "NoobTrade Pro",
                    "displayPrice": "$29.99/month",
                    "priceMonthly": 29.99,
                    "currency": "USD",
                    "benefit": "Unlimited Generate, Dashboard Scan, live chart, and matched-history requests.",
                },
            }
        )
        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)
        return response

    def _apply_usage_limits(app, client_ip):
        category = _usage_limit_category()
        if category is None:
            return None

        if _is_usage_unlimited_user(app):
            return None

        actor_key = _usage_actor_key(client_ip)
        if not _should_count_usage_event(actor_key, category):
            return None

        checks = []
        limit_labels = {}
        for spec in USAGE_LIMITS.get(category, ()):  # pragma: no branch - categories are fixed above.
            check_key = f"usage:{actor_key}:{category}:{spec['name']}"
            checks.append((check_key, spec["limit"], spec["windowSeconds"]))
            limit_labels[check_key] = spec["label"]

        decision = rate_limit_service.consume(checks)
        if decision.get("allowed"):
            return None

        return _usage_limit_response(
            category,
            decision,
            limit_labels.get(decision.get("key"), USAGE_LIMIT_LABELS.get(category, "free request limit")),
        )

    @app.before_request
    def apply_basic_security():
        is_public_ready_endpoint = request.endpoint in {
            "stock.health_check",
            "serve_ampli_lab",
            "serve_frontend",
            "static",
        }
        if _is_live_market_snapshot_request():
            is_public_ready_endpoint = True
        if request.endpoint == "serve_frontend" and _is_ampli_lab_host():
            is_public_ready_endpoint = True

        if not is_public_ready_endpoint and str(app.config.get("ENVIRONMENT", "")).lower() == "production":
            _start_background_database_init(app)
            if not _wait_for_database_ready(app):
                return _database_warming_response(app)

        client_ip = (
            str(request.headers.get("X-Forwarded-For", "")).split(",")[0].strip()
            or request.remote_addr
            or "unknown"
        )
        usage_limit_response = _apply_usage_limits(app, client_ip)
        if usage_limit_response is not None:
            return usage_limit_response

        if _usage_limit_category() is None:
            rate_limit_key = f"{client_ip}:{request.endpoint or request.path}:{request.method}"
            if request.endpoint == "stock.get_pro_signal":
                limit = 240
            else:
                limit = 20 if request.method in {"POST", "PUT", "PATCH", "DELETE"} else 120
            window_seconds = 60

            if not rate_limit_service.allow(rate_limit_key, limit=limit, window_seconds=window_seconds):
                return jsonify({"message": "Too many requests. Please slow down and try again."}), 429

        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            csrf_exempt_endpoints = {"auth.csrf_token", "auth.login", "stock.get_pro_signal"}
            if request.endpoint not in csrf_exempt_endpoints:
                sent_token = request.headers.get("X-CSRF-Token", "")
                session_token = session.get("csrf_token", "")

                if not sent_token or not session_token or sent_token != session_token:
                    return jsonify({"message": "CSRF validation failed."}), 403

    @app.after_request
    def apply_security_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self' http://127.0.0.1:5010 http://127.0.0.1:5173 http://127.0.0.1:5174;"
        return response

    if str(app.config.get("ENVIRONMENT", "")).lower() == "production":
        _start_background_database_init(app)
    else:
        try:
            initialize_database_with_retries(app)
        except Exception:
            app.logger.exception("Database initialization failed after retries.")
            if _is_sqlite_app(app):
                recovered = recover_sqlite_database(app)
                if recovered:
                    return app
            raise

    if ampli_lab_dist.exists():
        @app.route("/amplialpha/", defaults={"path": ""})
        @app.route("/amplialpha/<path:path>")
        @app.route("/ampli-lab/", defaults={"path": ""})
        @app.route("/ampli-lab/<path:path>")
        def serve_ampli_lab(path):
            requested_path = ampli_lab_dist / path

            if path and requested_path.exists() and requested_path.is_file():
                return send_from_directory(ampli_lab_dist, path)

            return send_from_directory(ampli_lab_dist, "index.html")

    if frontend_dist.exists():
        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_frontend(path):
            if _is_ampli_lab_host() and ampli_lab_dist.exists():
                requested_path = ampli_lab_dist / path

                if path and requested_path.exists() and requested_path.is_file():
                    return send_from_directory(ampli_lab_dist, path)

                return send_from_directory(ampli_lab_dist, "index.html")

            requested_path = frontend_dist / path

            if path and requested_path.exists() and requested_path.is_file():
                return send_from_directory(frontend_dist, path)

            return send_from_directory(frontend_dist, "index.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
        use_reloader=app.config["USE_RELOADER"],
    )
