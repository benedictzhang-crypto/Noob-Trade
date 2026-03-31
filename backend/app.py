from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask import send_from_directory
from sqlalchemy import inspect, text
from dotenv import load_dotenv

load_dotenv()

from config import Config
from extensions import db
from models import analysis, auth, market_data, trading
from models.auth import User
from routes.auth_routes import auth_blueprint, auth_legacy_blueprint
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


def ensure_auth_schema(app):
    with app.app_context():
        inspector = inspect(db.engine)
        table_names = set(inspector.get_table_names())

        if "users" not in table_names or "login_verification_codes" not in table_names or "login_activities" not in table_names:
            db.create_all()
            return

        user_columns = {column["name"] for column in inspector.get_columns("users")}

        if "role" not in user_columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))
        if "email_verified" not in user_columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0"))
        if "verified_at" not in user_columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN verified_at DATETIME"))
        db.session.commit()


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


def create_app():
    """Create and configure the Flask application."""
    project_root = Path(__file__).resolve().parent.parent
    frontend_dist = project_root / "frontend" / "dist"
    static_folder = str(frontend_dist) if frontend_dist.exists() else None

    app = Flask(__name__, static_folder=static_folder, static_url_path="")
    app.config.from_object(Config)

    # Allow requests from the local frontend during development.
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    db.init_app(app)

    app.register_blueprint(stock_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(auth_legacy_blueprint)

    app.config["DB_AVAILABLE"] = True

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
            if request.endpoint not in {"auth.csrf_token"}:
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
        initialize_database(app)
    except Exception:
        app.logger.exception("Database initialization failed on first attempt.")

        recovered = False
        if _is_sqlite_app(app):
            recovered = recover_sqlite_database(app)

        if not recovered:
            app.config["DB_AVAILABLE"] = False
            app.logger.exception("Database initialization failed; app will continue with temporary login fallback.")

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
