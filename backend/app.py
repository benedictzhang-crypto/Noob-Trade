from pathlib import Path
from datetime import datetime
import sqlite3
import time

from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask import send_from_directory
from sqlalchemy import inspect, text
from dotenv import load_dotenv

load_dotenv()

from config import Config
from extensions import db
from models import analysis, auth, market_data, trading
from models.auth import LoginActivity, LoginVerificationCode, User
from routes.auth_routes import auth_blueprint
from routes.stock_routes import stock_blueprint
from services.rate_limit_service import rate_limit_service
from services.security_service import hash_secret


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

            existing_admin.password_hash = _generate_compatible_password_hash(app, admin_details["password"])
            updated = True

        if updated:
            db.session.commit()


def initialize_database(app):
    with app.app_context():
        db.create_all()

    ensure_auth_schema(app)
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


def create_app():
    """Create and configure the Flask application."""
    project_root = Path(__file__).resolve().parent.parent
    frontend_dist = project_root / "frontend" / "dist"
    static_folder = str(frontend_dist) if frontend_dist.exists() else None

    app = Flask(__name__, static_folder=static_folder, static_url_path="")
    app.config.from_object(Config)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = _build_engine_options(app)
    postgres_ok, postgres_error = _assert_production_postgres(app)
    app.config["PRODUCTION_POSTGRES_OK"] = postgres_ok
    app.config["PRODUCTION_POSTGRES_ERROR"] = postgres_error
    if not postgres_ok and postgres_error:
        app.logger.error(postgres_error)

    # Allow requests from the local frontend during development.
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    db.init_app(app)

    app.register_blueprint(stock_blueprint)
    app.register_blueprint(auth_blueprint)

    @app.before_request
    def apply_basic_security():
        client_ip = (
            str(request.headers.get("X-Forwarded-For", "")).split(",")[0].strip()
            or request.remote_addr
            or "unknown"
        )
        rate_limit_key = f"{client_ip}:{request.endpoint or request.path}:{request.method}"
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

    try:
        initialize_database_with_retries(app)
    except Exception:
        app.logger.exception("Database initialization failed after retries.")
        if _is_sqlite_app(app):
            recovered = recover_sqlite_database(app)
            if recovered:
                return app
        raise

    if frontend_dist.exists():
        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_frontend(path):
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
