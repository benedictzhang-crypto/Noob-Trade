from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import hmac
import html
import re
import secrets
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from extensions import db
from models.auth import LoginActivity, LoginVerificationCode, UsageActivity, User, UserWatchlist
from services.email_service import EmailService
from services.security_service import hash_secret, needs_rehash, verify_secret

auth_blueprint = Blueprint("auth", __name__, url_prefix="/api/auth")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9]+$")
WATCHLIST_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,19}$")
WATCHLIST_MARKETS = {"stock", "crypto"}
DEFAULT_WATCHLIST_SYMBOLS = {
    "stock": ["AAPL", "NVDA", "TSLA"],
    "crypto": ["BTC", "ETH", "SOL", "OKB"],
}
MAX_WATCHLIST_SYMBOLS = 500


def _utcnow():
    return datetime.now(timezone.utc)


def _coerce_utc_datetime(value):
    if value in (None, ""):
        return None

    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            value = datetime.fromisoformat(normalized)
        except ValueError:
            return None

    if not isinstance(value, datetime):
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _serialize_user(user, display_code=None):
    resolved_display_code = _display_code_for_user(user) if display_code is None else display_code
    return {
        "id": user.id,
        "displayCode": resolved_display_code,
        "fullName": user.full_name,
        "email": user.email,
        "riskProfile": user.risk_profile,
        "membership": user.membership,
        "joinedAt": user.created_at.strftime("%B %Y") if user.created_at else "Recent",
        "role": user.role,
        "isAdmin": user.role == "admin",
        "emailVerified": bool(getattr(user, "email_verified", False)),
        "isDisabled": bool(getattr(user, "is_disabled", False)),
        "disabledAt": user.disabled_at.isoformat() if getattr(user, "disabled_at", None) else None,
        "disabledReason": getattr(user, "disabled_reason", None),
    }


def _serialize_user_with_display_code(user, display_code_map):
    return _serialize_user(user, display_code_map.get(user.id, 0))


def _serialized_admin_users():
    users = User.query.order_by(User.created_at.asc()).all()
    display_code_map = _build_display_code_map(users)
    return _serialize_admin_users_with_map(users, display_code_map)


def _serialize_admin_users_with_map(users, display_code_map):
    users = sorted(
        users,
        key=lambda user: (
            0 if user.role == "admin" else 1,
            display_code_map.get(user.id, 0),
            user.created_at or datetime.max,
            user.email.lower(),
        ),
    )
    return [
        {
            **_serialize_user_with_display_code(user, display_code_map),
            "createdAt": user.created_at.isoformat() if user.created_at else None,
        }
        for user in users
    ]


def _sanitize_text(value, max_length=255):
    return html.escape(str(value or "").strip())[:max_length]


def _configured_admin_emails():
    configured_admins = current_app.config.get("ADMIN_ACCOUNTS") or []
    return [str(item.get("email") or "").strip().lower() for item in configured_admins if item.get("email")]


def _configured_admin_account(email):
    normalized_email = str(email or "").strip().lower()
    configured_admins = current_app.config.get("ADMIN_ACCOUNTS") or []

    for admin in configured_admins:
        admin_email = str(admin.get("email") or "").strip().lower()
        if admin_email == normalized_email:
            return {
                "email": admin_email,
                "password": str(admin.get("password") or ""),
                "full_name": str(admin.get("full_name") or "").strip() or "Noob Trade Admin",
            }

    return None


def _serialized_configured_admin_user(configured_admin):
    configured_admins = _configured_admin_emails()
    normalized_email = str(configured_admin.get("email") or "").strip().lower()
    display_code = configured_admins.index(normalized_email) + 1 if normalized_email in configured_admins else 1

    return {
        "id": display_code,
        "displayCode": display_code,
        "fullName": str(configured_admin.get("full_name") or "").strip() or "Noob Trade Admin",
        "email": normalized_email,
        "riskProfile": "Balanced",
        "membership": "Administrator",
        "joinedAt": "Configured",
        "role": "admin",
        "isAdmin": True,
        "emailVerified": True,
        "isDisabled": False,
        "disabledAt": None,
        "disabledReason": None,
    }


def _display_code_for_user(user):
    normalized_email = str(user.email or "").strip().lower()
    configured_admins = _configured_admin_emails()
    if user.role == "admin" and normalized_email in configured_admins:
        return configured_admins.index(normalized_email) + 1

    regular_users = User.query.filter(User.role != "admin").order_by(User.created_at.asc(), User.id.asc()).all()
    for index, regular_user in enumerate(regular_users, start=101):
        if regular_user.id == user.id:
            return index
    return 0


def _build_display_code_map(users):
    configured_admins = _configured_admin_emails()
    display_code_map = {}

    regular_users = [
        user
        for user in users
        if getattr(user, "role", "user") != "admin"
    ]
    regular_users = sorted(
        regular_users,
        key=lambda user: (
            user.created_at or datetime.max,
            user.id or 0,
            str(user.email or "").lower(),
        ),
    )

    for user in users:
        normalized_email = str(user.email or "").strip().lower()
        if user.role == "admin" and normalized_email in configured_admins:
            display_code_map[user.id] = configured_admins.index(normalized_email) + 1

    for index, regular_user in enumerate(regular_users, start=101):
        display_code_map[regular_user.id] = index

    return display_code_map


def _get_admin_user():
    admin_email = str(session.get("user_email", "")).strip().lower()

    if not admin_email:
        return None

    session_snapshot = session.get("user_snapshot")
    if (
        isinstance(session_snapshot, dict)
        and str(session_snapshot.get("email") or "").strip().lower() == admin_email
        and bool(session_snapshot.get("isAdmin"))
    ):
        return session_snapshot

    user = User.query.filter_by(email=admin_email).first()
    if user is None or user.role != "admin":
        return None

    return user


def _email_service():
    return EmailService(current_app.config)


def _email_delivery_available():
    return _email_service().is_configured()


def _allow_local_email_bypass():
    return bool(current_app.config.get("ALLOW_LOCAL_EMAIL_BYPASS", False))


def _email_required_message():
    return (
        "Email delivery is required for this app environment. "
        "Please configure SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and EMAIL_FROM."
    )


def _issue_csrf_token():
    token = secrets.token_urlsafe(32)
    session["csrf_token"] = token
    return token


def _session_user_payload(user):
    return {
        "user_id": user.id,
        "user_email": user.email,
        "user_role": user.role,
    }


def _session_user_payload_from_serialized_user(user):
    return {
        "user_id": user.get("id"),
        "user_email": user.get("email"),
        "user_role": user.get("role"),
    }


def _session_response_payload():
    session_email = str(session.get("user_email", "")).strip().lower()

    if not session_email:
        return None

    session_snapshot = session.get("user_snapshot")
    if (
        isinstance(session_snapshot, dict)
        and str(session_snapshot.get("email") or "").strip().lower() == session_email
        and bool(session_snapshot.get("isAdmin"))
    ):
        return {
            "user": session_snapshot,
            "adminUsers": None,
        }

    user = _find_user_by_email(session_email)
    if user is None:
        return None
    if bool(getattr(user, "is_disabled", False)):
        session.clear()
        return None

    return {
        "user": _serialize_user(user),
        "adminUsers": None,
    }


def _authenticated_owner_email():
    session_payload = _session_response_payload()
    if session_payload is None:
        return None
    return str(session_payload["user"].get("email") or "").strip().lower() or None


def _normalize_watchlist_symbols(symbols):
    if not isinstance(symbols, list):
        return None

    normalized = []
    seen = set()
    for symbol in symbols:
        cleaned_symbol = str(symbol or "").strip().upper()
        if not cleaned_symbol or not WATCHLIST_SYMBOL_PATTERN.fullmatch(cleaned_symbol):
            continue
        if cleaned_symbol in seen:
            continue
        seen.add(cleaned_symbol)
        normalized.append(cleaned_symbol)
        if len(normalized) >= MAX_WATCHLIST_SYMBOLS:
            break

    return normalized


def _get_or_create_user_watchlists(owner_email):
    rows = UserWatchlist.query.filter_by(owner_email=owner_email).all()
    rows_by_market = {row.market: row for row in rows if row.market in WATCHLIST_MARKETS}
    created = False

    for market in WATCHLIST_MARKETS:
        if market in rows_by_market:
            continue
        row = UserWatchlist(
            owner_email=owner_email,
            market=market,
            symbols=list(DEFAULT_WATCHLIST_SYMBOLS[market]),
        )
        db.session.add(row)
        rows_by_market[market] = row
        created = True

    if created:
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            rows = UserWatchlist.query.filter_by(owner_email=owner_email).all()
            rows_by_market = {row.market: row for row in rows if row.market in WATCHLIST_MARKETS}

    return rows_by_market


def _ensure_user_is_active(user):
    if user is None:
        return False, (jsonify({"message": "We could not find an account with that email."}), 404)
    if bool(getattr(user, "is_disabled", False)):
        session.clear()
        return False, (jsonify({"message": "This account has been disabled. Please contact an administrator."}), 403)
    return True, None


def _send_login_notice(user):
    try:
        login_context = _record_login_activity(user)
    except Exception:
        db.session.rollback()
        current_app.logger.warning("Login activity recording skipped for %s", user.email, exc_info=True)
        login_context = None

    try:
        _email_service().send_login_notice(user.email, login_context=login_context)
        return True, None
    except ValueError as error:
        current_app.logger.warning("Login notice email skipped: %s", error)
        return False, str(error)
    except Exception:
        current_app.logger.exception("Could not send login notice email")
        return False, "Could not send the login notice email right now."


def _send_login_notice_to_email(email):
    try:
        _email_service().send_login_notice(email)
        return True, None
    except ValueError as error:
        current_app.logger.warning("Login notice email skipped: %s", error)
        return False, str(error)
    except Exception:
        current_app.logger.exception("Could not send login notice email")
        return False, "Could not send the login notice email right now."


def _generate_compatible_password_hash(password):
    return hash_secret(password)


def _generate_six_digit_code():
    return f"{secrets.randbelow(1000000):06d}"


def _issue_security_code(user, purpose, expiry_minutes):
    code = _generate_six_digit_code()
    verification_record = LoginVerificationCode(
        user_id=user.id,
        email=user.email,
        code_hash=_generate_compatible_password_hash(code),
        purpose=purpose,
        expires_at=_utcnow() + timedelta(minutes=expiry_minutes),
    )
    db.session.add(verification_record)
    db.session.commit()
    return code


def _issue_security_code_or_response(user, purpose, expiry_minutes, log_label, failure_message):
    try:
        return _issue_security_code(user, purpose, expiry_minutes), None
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Could not persist %s security code for %s", log_label, user.email)
        return None, (jsonify({"message": failure_message}), 500)


def _consume_security_code(user, purpose, code):
    recent_codes = LoginVerificationCode.query.filter_by(
        user_id=user.id,
        email=user.email,
        purpose=purpose,
        used_at=None,
    ).order_by(LoginVerificationCode.created_at.desc()).limit(5).all()

    now = _utcnow()

    for record in recent_codes:
        expires_at = _coerce_utc_datetime(record.expires_at)
        if expires_at and expires_at < now:
            continue

        if verify_secret(record.code_hash, code):
            record.used_at = now
            db.session.commit()
            return True

    return False


def _find_user_by_email(email):
    return User.query.filter_by(email=email).first()


def _ensure_configured_admin_user(user, configured_admin):
    updated = False

    if user is None:
        user = User(
            full_name=configured_admin["full_name"],
            email=configured_admin["email"],
            password_hash=_generate_compatible_password_hash(configured_admin["password"]),
            risk_profile="Balanced",
            membership="Administrator",
            role="admin",
            email_verified=True,
            verified_at=_utcnow(),
        )
        db.session.add(user)
        db.session.commit()
        return user

    if user.full_name != configured_admin["full_name"]:
        user.full_name = configured_admin["full_name"]
        updated = True
    if user.role != "admin":
        user.role = "admin"
        updated = True
    if user.membership != "Administrator":
        user.membership = "Administrator"
        updated = True
    if not getattr(user, "email_verified", False):
        user.email_verified = True
        user.verified_at = _utcnow()
        updated = True

    if updated:
        db.session.commit()

    return user


def _validate_password_rules(password):
    if len(password) < 8:
        return "Please use a password with at least 8 characters."
    if password.isalnum():
        return "Please include at least one special symbol such as _, !, or # in your password."
    return None


def _validate_username_rules(username):
    if not username:
        return "Please enter a username."
    if len(username) > 120:
        return "Please keep your username within 120 characters."
    if not USERNAME_PATTERN.fullmatch(username):
        return "Username must use only English letters and numbers."
    return None


def _client_ip():
    forwarded_for = str(request.headers.get("X-Forwarded-For", "")).strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = str(request.headers.get("X-Real-IP", "")).strip()
    if real_ip:
        return real_ip

    return request.remote_addr or "Unknown"


def _client_user_agent():
    return str(request.headers.get("User-Agent", "")).strip() or "Unknown device"


def _device_label(user_agent):
    lowered = user_agent.lower()

    if "iphone" in lowered:
        return "iPhone"
    if "ipad" in lowered:
        return "iPad"
    if "android" in lowered:
        return "Android device"
    if "macintosh" in lowered or "mac os" in lowered:
        return "Mac"
    if "windows" in lowered:
        return "Windows PC"

    return user_agent[:120] if user_agent else "Unknown device"


def _location_label(ip_address):
    if ip_address in ("127.0.0.1", "::1", "localhost"):
        return "Local development environment"

    if not ip_address or ip_address == "Unknown":
        return "Unknown location"

    return f"IP {ip_address}"


def _record_login_activity(user):
    ip_address = _client_ip()
    user_agent = _client_user_agent()
    device_label = _device_label(user_agent)
    location_label = _location_label(ip_address)

    prior_device = LoginActivity.query.filter_by(
        user_id=user.id,
        device_label=device_label,
    ).first()
    prior_location = LoginActivity.query.filter_by(
        user_id=user.id,
        ip_address=ip_address,
    ).first()

    activity = LoginActivity(
        user_id=user.id,
        email=user.email,
        ip_address=ip_address,
        user_agent=user_agent,
        device_label=device_label,
        location_label=location_label,
        is_new_device=prior_device is None,
        is_new_location=prior_location is None,
    )
    db.session.add(activity)
    db.session.commit()

    return {
        "timeLabel": _utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "ipAddress": ip_address,
        "deviceLabel": device_label,
        "locationLabel": location_label,
        "isNewDevice": activity.is_new_device,
        "isNewLocation": activity.is_new_location,
    }


@auth_blueprint.route("/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {}
    full_name = str(payload.get("fullName", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    risk_profile = str(payload.get("riskProfile", "Balanced")).strip() or "Balanced"

    if not full_name or not email or not password:
        return jsonify({"message": "Please complete username, email, and password."}), 400

    username_error = _validate_username_rules(full_name)
    if username_error:
        return jsonify({"message": username_error}), 400

    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"message": "Please enter a valid email address."}), 400

    password_error = _validate_password_rules(password)
    if password_error:
        return jsonify({"message": password_error}), 400

    existing_user = _find_user_by_email(email)

    if existing_user is not None and existing_user.email_verified:
        return jsonify({"message": "An account with this email already exists."}), 409

    email_delivery_available = _email_delivery_available()

    if existing_user is None:
        user = User(
            full_name=_sanitize_text(full_name, max_length=120),
            email=email,
            password_hash=_generate_compatible_password_hash(password),
            risk_profile=_sanitize_text(risk_profile, max_length=40) or "Balanced",
            role="user",
            email_verified=not email_delivery_available,
        )
        if not email_delivery_available:
            user.verified_at = _utcnow()
        db.session.add(user)
        db.session.commit()
    else:
        existing_user.full_name = _sanitize_text(full_name, max_length=120)
        existing_user.password_hash = _generate_compatible_password_hash(password)
        existing_user.risk_profile = _sanitize_text(risk_profile, max_length=40) or "Balanced"
        existing_user.email_verified = not email_delivery_available
        existing_user.verified_at = _utcnow() if not email_delivery_available else None
        user = existing_user
        db.session.commit()

    if not email_delivery_available and not _allow_local_email_bypass():
        return jsonify({"message": _email_required_message()}), 503

    if not email_delivery_available:
        return jsonify({"message": _email_required_message()}), 503

    code, error_response = _issue_security_code_or_response(
        user=user,
        purpose="email_verification",
        expiry_minutes=current_app.config.get("EMAIL_VERIFICATION_CODE_EXPIRY_MINUTES", 15),
        log_label="email verification",
        failure_message="Could not create the email verification code right now. Please try again.",
    )
    if error_response is not None:
        return error_response

    try:
        _email_service().send_email_verification_code(user.email, code)
    except Exception as error:
        current_app.logger.exception("Could not send email verification code")
        return jsonify({"message": str(error) if isinstance(error, ValueError) else "Could not send the verification email right now."}), 500

    return jsonify(
        {
            "message": f"Account created for {user.full_name}. Enter the verification code sent to {user.email}.",
            "requiresEmailVerification": True,
            "user": _serialize_user(user),
        }
    ), 201


@auth_blueprint.route("/verify-email/request", methods=["POST"])
def request_email_verification():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()

    if not email:
        return jsonify({"message": "Please enter your email address."}), 400

    user = _find_user_by_email(email)

    if user is None:
        return jsonify({"message": "We could not find an account with that email."}), 404

    if user.email_verified:
        return jsonify({"message": "This email is already verified."})

    if not _email_delivery_available():
        return jsonify({"message": _email_required_message()}), 503

    code, error_response = _issue_security_code_or_response(
        user=user,
        purpose="email_verification",
        expiry_minutes=current_app.config.get("EMAIL_VERIFICATION_CODE_EXPIRY_MINUTES", 15),
        log_label="email verification",
        failure_message="Could not create the email verification code right now. Please try again.",
    )
    if error_response is not None:
        return error_response

    try:
        _email_service().send_email_verification_code(user.email, code)
    except Exception as error:
        current_app.logger.exception("Could not resend email verification code")
        return jsonify({"message": str(error) if isinstance(error, ValueError) else "Could not send the verification email right now."}), 500

    return jsonify({"message": f"A verification code was sent to {user.email}."})


@auth_blueprint.route("/verify-email/confirm", methods=["POST"])
def confirm_email_verification():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    code = str(payload.get("code", "")).strip()

    if not email or not code:
        return jsonify({"message": "Please enter both email and verification code."}), 400

    user = _find_user_by_email(email)

    if user is None:
        return jsonify({"message": "We could not find an account with that email."}), 404

    if user.email_verified:
        return jsonify({"message": "This email is already verified.", "user": _serialize_user(user)})

    if not _consume_security_code(user, "email_verification", code):
        return jsonify({"message": "That verification code is invalid or expired."}), 400

    user.email_verified = True
    user.verified_at = _utcnow()
    db.session.commit()

    return jsonify(
        {
            "message": f"{user.email} has been verified. You can sign in now.",
            "user": _serialize_user(user),
        }
    )


@auth_blueprint.route("/password-reset/request", methods=["POST"])
def request_password_reset():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()

    if not email:
        return jsonify({"message": "Please enter your email address."}), 400

    user = _find_user_by_email(email)

    if user is None:
        return jsonify({"message": "We could not find an account with that email."}), 404

    if not _email_delivery_available():
        return jsonify({"message": _email_required_message()}), 503

    code, error_response = _issue_security_code_or_response(
        user=user,
        purpose="password_reset",
        expiry_minutes=current_app.config.get("PASSWORD_RESET_CODE_EXPIRY_MINUTES", 15),
        log_label="password reset",
        failure_message="Could not create the password reset code right now. Please try again.",
    )
    if error_response is not None:
        return error_response

    try:
        _email_service().send_password_reset_code(user.email, code)
    except Exception as error:
        current_app.logger.exception("Could not send password reset code")
        return jsonify({"message": str(error) if isinstance(error, ValueError) else "Could not send the password reset email right now."}), 500

    return jsonify({"message": f"A password reset code was sent to {user.email}."})


@auth_blueprint.route("/password-reset/confirm", methods=["POST"])
def confirm_password_reset():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    code = str(payload.get("code", "")).strip()
    new_password = str(payload.get("newPassword", ""))

    if not email or not code or not new_password:
        return jsonify({"message": "Please complete email, verification code, and new password."}), 400

    password_error = _validate_password_rules(new_password)
    if password_error:
        return jsonify({"message": password_error}), 400

    user = _find_user_by_email(email)

    if user is None:
        return jsonify({"message": "We could not find an account with that email."}), 404

    if not _consume_security_code(user, "password_reset", code):
        return jsonify({"message": "That password reset code is invalid or expired."}), 400

    user.password_hash = _generate_compatible_password_hash(new_password)
    db.session.commit()

    return jsonify({"message": "Your password has been updated. You can sign in now."})


def _login_impl():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    if not email or not password:
        return jsonify({"message": "Please enter both email and password."}), 400

    configured_admin = _configured_admin_account(email)
    if configured_admin is not None:
        if not hmac.compare_digest(password, configured_admin["password"]):
            return jsonify({"message": "Incorrect email or password."}), 401
        serialized_user = _serialized_configured_admin_user(configured_admin)

        session.clear()
        session.update(_session_user_payload_from_serialized_user(serialized_user))
        session["user_snapshot"] = serialized_user

        return jsonify(
            {
                "code": 200,
                "message": f"Welcome back, {serialized_user['fullName']}.",
                "emailNoticeSent": False,
                "emailNoticeMessage": None,
                "user": serialized_user,
                "adminUsers": None,
                "csrfToken": _issue_csrf_token(),
            }
        )

    user = _find_user_by_email(email)

    if user is None or not verify_secret(user.password_hash, password):
        return jsonify({"message": "Incorrect email or password."}), 401

    is_active, error_response = _ensure_user_is_active(user)
    if not is_active:
        return error_response

    if needs_rehash(user.password_hash):
        user.password_hash = _generate_compatible_password_hash(password)
        db.session.commit()

    if not user.email_verified:
        return jsonify(
            {
                "message": "Please verify your email before signing in.",
                "requiresEmailVerification": True,
                "user": _serialize_user(user),
            }
        ), 403

    serialized_user = _serialize_user(user)

    session.clear()
    session.update(_session_user_payload(user))
    session["user_snapshot"] = serialized_user

    message = f"Welcome back, {user.full_name}."
    notice_sent = False
    notice_error = None

    if user.role != "admin":
        notice_sent, notice_error = _send_login_notice(user)
        if notice_sent:
            message = f"Welcome back, {user.full_name}. A login notice was sent to {user.email}."
        elif notice_error:
            message = f"Welcome back, {user.full_name}. Login notice email is unavailable right now."

    return jsonify(
        {
            "code": 200,
            "message": message,
            "emailNoticeSent": notice_sent,
            "emailNoticeMessage": notice_error,
            "user": serialized_user,
            "adminUsers": None,
            "csrfToken": _issue_csrf_token(),
        }
    )


@auth_blueprint.route("/csrf-token", methods=["GET"])
def csrf_token():
    return jsonify({"csrfToken": session.get("csrf_token") or _issue_csrf_token()})


@auth_blueprint.route("/session", methods=["GET"])
def auth_session():
    session_payload = _session_response_payload()

    if session_payload is None:
        return jsonify({"authenticated": False, "user": None}), 401

    return jsonify(
        {
            "authenticated": True,
            "user": session_payload["user"],
            "adminUsers": session_payload.get("adminUsers"),
            "csrfToken": session.get("csrf_token") or _issue_csrf_token(),
        }
    )


@auth_blueprint.route("/watchlists", methods=["GET"])
def get_watchlists():
    owner_email = _authenticated_owner_email()
    if owner_email is None:
        return jsonify({"message": "Sign in to load saved symbols."}), 401

    rows_by_market = _get_or_create_user_watchlists(owner_email)
    return jsonify(
        {
            "watchlists": {
                market: _normalize_watchlist_symbols(rows_by_market[market].symbols) or []
                for market in sorted(WATCHLIST_MARKETS)
            }
        }
    )


@auth_blueprint.route("/watchlists/<market>", methods=["PUT"])
def save_watchlist(market):
    normalized_market = str(market or "").strip().lower()
    if normalized_market not in WATCHLIST_MARKETS:
        return jsonify({"message": "Unknown watchlist market."}), 404

    owner_email = _authenticated_owner_email()
    if owner_email is None:
        return jsonify({"message": "Sign in to save symbols."}), 401

    payload = request.get_json(silent=True) or {}
    normalized_symbols = _normalize_watchlist_symbols(payload.get("symbols"))
    if normalized_symbols is None:
        return jsonify({"message": "Symbols must be provided as a list."}), 400

    rows_by_market = _get_or_create_user_watchlists(owner_email)
    row = rows_by_market[normalized_market]
    row.symbols = normalized_symbols
    db.session.commit()

    return jsonify({"market": normalized_market, "symbols": normalized_symbols})


@auth_blueprint.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Signed out."})


@auth_blueprint.route("/login", methods=["POST"])
def login():
    return _login_impl()


@auth_blueprint.route("/users", methods=["GET"])
def list_users():
    admin_user = _get_admin_user()
    if admin_user is None:
        return jsonify({"message": "Admin access is required."}), 403
    return jsonify({"users": _serialized_admin_users()})


@auth_blueprint.route("/users/<int:user_id>/activity", methods=["GET"])
def get_user_activity(user_id):
    admin_user = _get_admin_user()
    if admin_user is None:
        return jsonify({"message": "Admin access is required."}), 403

    target_user = User.query.filter_by(id=user_id).first()
    if target_user is None:
        return jsonify({"message": "User not found."}), 404

    now = _utcnow()
    login_rows = (
        LoginActivity.query
        .filter_by(user_id=target_user.id)
        .order_by(LoginActivity.created_at.asc())
        .all()
    )
    usage_rows = (
        UsageActivity.query
        .filter_by(user_id=target_user.id)
        .order_by(UsageActivity.created_at.asc())
        .all()
    )

    login_times = []
    for row in login_rows:
        created_at = _coerce_utc_datetime(row.created_at)
        if created_at is not None:
            login_times.append(created_at)

    usage_records = []
    for row in usage_rows:
        created_at = _coerce_utc_datetime(row.created_at)
        if created_at is not None:
            usage_records.append((row, created_at))

    category_counts = Counter(row.category for row, _ in usage_records)
    market_counts = Counter(row.market for row, _ in usage_records)
    successful_records = [
        (row, created_at)
        for row, created_at in usage_records
        if 200 <= int(row.status_code or 0) < 400
    ]
    successful_category_counts = Counter(row.category for row, _ in successful_records)

    def _count_since(records, since):
        return sum(1 for _, created_at in records if created_at >= since)

    daily_counts = Counter(
        created_at.date().isoformat()
        for _, created_at in usage_records
        if created_at >= now - timedelta(days=30)
    )

    return jsonify(
        {
            "user": _serialize_user(target_user),
            "login": {
                "total": len(login_rows),
                "firstAt": login_times[0].isoformat() if login_times else None,
                "lastAt": login_times[-1].isoformat() if login_times else None,
                "distinctDevices": len({row.device_label for row in login_rows if row.device_label}),
                "distinctLocations": len({row.location_label for row in login_rows if row.location_label}),
            },
            "usage": {
                "trackingStartedAt": usage_records[0][1].isoformat() if usage_records else None,
                "lastUsedAt": usage_records[-1][1].isoformat() if usage_records else None,
                "total": len(usage_records),
                "successful": len(successful_records),
                "failed": len(usage_records) - len(successful_records),
                "last24Hours": _count_since(usage_records, now - timedelta(hours=24)),
                "last7Days": _count_since(usage_records, now - timedelta(days=7)),
                "last30Days": _count_since(usage_records, now - timedelta(days=30)),
                "byCategory": [
                    {
                        "category": category,
                        "total": count,
                        "successful": successful_category_counts.get(category, 0),
                    }
                    for category, count in sorted(category_counts.items())
                ],
                "byMarket": [
                    {"market": market, "total": count}
                    for market, count in sorted(market_counts.items())
                ],
                "daily": [
                    {"date": date, "total": count}
                    for date, count in sorted(daily_counts.items())
                ],
            },
        }
    )


def _weekly_period_metrics(period_start, period_end):
    grouped_rows = (
        db.session.query(
            UsageActivity.user_id,
            UsageActivity.category,
            UsageActivity.market,
            UsageActivity.status_code,
            func.count(UsageActivity.id),
            func.max(UsageActivity.created_at),
        )
        .filter(
            UsageActivity.created_at >= period_start,
            UsageActivity.created_at < period_end,
        )
        .group_by(
            UsageActivity.user_id,
            UsageActivity.category,
            UsageActivity.market,
            UsageActivity.status_code,
        )
        .all()
    )
    active_day_rows = (
        db.session.query(
            UsageActivity.user_id,
            func.count(func.distinct(func.date(UsageActivity.created_at))),
        )
        .filter(
            UsageActivity.created_at >= period_start,
            UsageActivity.created_at < period_end,
        )
        .group_by(UsageActivity.user_id)
        .all()
    )

    metrics = {}
    for user_id, category, market, status_code, count, last_used_at in grouped_rows:
        user_metrics = metrics.setdefault(
            user_id,
            {
                "actions": 0,
                "successful": 0,
                "failed": 0,
                "activeDays": 0,
                "byCategory": Counter(),
                "byMarket": Counter(),
                "lastUsedAt": None,
            },
        )
        event_count = int(count or 0)
        user_metrics["actions"] += event_count
        if 200 <= int(status_code or 0) < 400:
            user_metrics["successful"] += event_count
        else:
            user_metrics["failed"] += event_count
        user_metrics["byCategory"][category] += event_count
        user_metrics["byMarket"][market] += event_count

        coerced_last_used_at = _coerce_utc_datetime(last_used_at)
        if coerced_last_used_at is not None and (
            user_metrics["lastUsedAt"] is None
            or coerced_last_used_at > user_metrics["lastUsedAt"]
        ):
            user_metrics["lastUsedAt"] = coerced_last_used_at

    for user_id, active_days in active_day_rows:
        user_metrics = metrics.setdefault(
            user_id,
            {
                "actions": 0,
                "successful": 0,
                "failed": 0,
                "activeDays": 0,
                "byCategory": Counter(),
                "byMarket": Counter(),
                "lastUsedAt": None,
            },
        )
        user_metrics["activeDays"] = int(active_days or 0)

    return metrics


def _serialize_week_metrics(metrics):
    actions = int(metrics.get("actions") or 0)
    active_days = int(metrics.get("activeDays") or 0)
    successful = int(metrics.get("successful") or 0)
    last_used_at = metrics.get("lastUsedAt")

    return {
        "actions": actions,
        "activeDays": active_days,
        "averagePerActiveDay": round(actions / active_days, 2) if active_days else 0,
        "successful": successful,
        "failed": int(metrics.get("failed") or 0),
        "successRate": round((successful / actions) * 100, 2) if actions else None,
        "lastUsedAt": last_used_at.isoformat() if last_used_at else None,
        "byCategory": dict(sorted(metrics.get("byCategory", {}).items())),
        "byMarket": dict(sorted(metrics.get("byMarket", {}).items())),
    }


@auth_blueprint.route("/activity/weekly", methods=["GET"])
def get_weekly_activity_report():
    admin_user = _get_admin_user()
    if admin_user is None:
        return jsonify({"message": "Admin access is required."}), 403

    report_timezone = ZoneInfo("America/New_York")
    requested_week_start = str(request.args.get("weekStart", "")).strip()
    if requested_week_start:
        try:
            requested_date = date.fromisoformat(requested_week_start)
        except ValueError:
            return jsonify({"message": "weekStart must use YYYY-MM-DD format."}), 400
        report_week_date = requested_date - timedelta(days=requested_date.weekday())
    else:
        local_today = _utcnow().astimezone(report_timezone).date()
        current_week_start = local_today - timedelta(days=local_today.weekday())
        report_week_date = current_week_start - timedelta(days=7)

    report_start_local = datetime.combine(report_week_date, time.min, tzinfo=report_timezone)
    report_end_local = report_start_local + timedelta(days=7)
    comparison_start_local = report_start_local - timedelta(days=7)
    report_start = report_start_local.astimezone(timezone.utc)
    report_end = report_end_local.astimezone(timezone.utc)
    comparison_start = comparison_start_local.astimezone(timezone.utc)

    users = User.query.filter(User.role != "admin").order_by(User.created_at.asc(), User.id.asc()).all()
    display_code_map = _build_display_code_map(User.query.order_by(User.created_at.asc(), User.id.asc()).all())
    report_metrics = _weekly_period_metrics(report_start, report_end)
    comparison_metrics = _weekly_period_metrics(comparison_start, report_start)

    lifetime_rows = (
        db.session.query(
            UsageActivity.user_id,
            func.count(UsageActivity.id),
            func.min(UsageActivity.created_at),
            func.max(UsageActivity.created_at),
        )
        .group_by(UsageActivity.user_id)
        .all()
    )
    lifetime_by_user = {
        user_id: {
            "actions": int(actions or 0),
            "firstUsedAt": _coerce_utc_datetime(first_used_at),
            "lastUsedAt": _coerce_utc_datetime(last_used_at),
        }
        for user_id, actions, first_used_at, last_used_at in lifetime_rows
    }
    tracking_started_at = _coerce_utc_datetime(
        db.session.query(func.min(UsageActivity.created_at)).scalar()
    )

    serialized_users = []
    for user in users:
        current = report_metrics.get(user.id, {})
        previous = comparison_metrics.get(user.id, {})
        lifetime = lifetime_by_user.get(user.id, {})
        current_actions = int(current.get("actions") or 0)
        previous_actions = int(previous.get("actions") or 0)
        first_observed_at = lifetime.get("firstUsedAt")

        if first_observed_at is None:
            average_weekly_actions = 0
        else:
            observation_start = max(first_observed_at, tracking_started_at or first_observed_at)
            observed_weeks = max(1.0, (_utcnow() - observation_start).total_seconds() / 604800)
            average_weekly_actions = round(int(lifetime.get("actions") or 0) / observed_weeks, 2)

        serialized_users.append(
            {
                "id": user.id,
                "displayCode": display_code_map.get(user.id, 0),
                "fullName": user.full_name,
                "email": user.email,
                "registeredAt": user.created_at.isoformat() if user.created_at else None,
                "lifetimeActionsSinceTracking": int(lifetime.get("actions") or 0),
                "averageWeeklyActionsSinceTracking": average_weekly_actions,
                "reportWeek": _serialize_week_metrics(current),
                "previousWeekActions": previous_actions,
                "weekOverWeekChangePercent": (
                    round(((current_actions - previous_actions) / previous_actions) * 100, 2)
                    if previous_actions
                    else None
                ),
            }
        )

    serialized_users.sort(
        key=lambda item: (
            -item["reportWeek"]["actions"],
            -item["lifetimeActionsSinceTracking"],
            item["displayCode"],
        )
    )
    total_actions = sum(item["reportWeek"]["actions"] for item in serialized_users)
    total_successful = sum(item["reportWeek"]["successful"] for item in serialized_users)
    previous_total_actions = sum(item["previousWeekActions"] for item in serialized_users)

    return jsonify(
        {
            "timezone": "America/New_York",
            "trackingStartedAt": tracking_started_at.isoformat() if tracking_started_at else None,
            "period": {
                "start": report_start_local.date().isoformat(),
                "endExclusive": report_end_local.date().isoformat(),
                "comparisonStart": comparison_start_local.date().isoformat(),
            },
            "summary": {
                "registeredUsers": len(serialized_users),
                "activeUsers": sum(1 for item in serialized_users if item["reportWeek"]["actions"] > 0),
                "inactiveUsers": sum(1 for item in serialized_users if item["reportWeek"]["actions"] == 0),
                "totalActions": total_actions,
                "previousWeekActions": previous_total_actions,
                "weekOverWeekChangePercent": (
                    round(((total_actions - previous_total_actions) / previous_total_actions) * 100, 2)
                    if previous_total_actions
                    else None
                ),
                "successRate": round((total_successful / total_actions) * 100, 2) if total_actions else None,
            },
            "users": serialized_users,
        }
    )


@auth_blueprint.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    admin_user = _get_admin_user()
    if admin_user is None:
        return jsonify({"message": "Admin access is required."}), 403

    target_user = User.query.filter_by(id=user_id).first()

    if target_user is None:
        return jsonify({"message": "User not found."}), 404

    if target_user.role == "admin":
        return jsonify({"message": "Admin accounts cannot be deleted from this panel."}), 400

    admin_email = getattr(admin_user, "email", None) if not isinstance(admin_user, dict) else admin_user.get("email")
    if target_user.email == admin_email:
        return jsonify({"message": "You cannot delete your own admin account."}), 400

    db.session.delete(target_user)
    db.session.commit()

    return jsonify({"message": f"Deleted user {target_user.email}."})


@auth_blueprint.route("/users/<int:user_id>/status", methods=["PATCH"])
def update_user_status(user_id):
    admin_user = _get_admin_user()
    if admin_user is None:
        return jsonify({"message": "Admin access is required."}), 403

    payload = request.get_json(silent=True) or {}
    disable_user = bool(payload.get("isDisabled"))
    disabled_reason = _sanitize_text(payload.get("disabledReason", ""), max_length=255) or None

    target_user = User.query.filter_by(id=user_id).first()

    if target_user is None:
        return jsonify({"message": "User not found."}), 404

    if target_user.role == "admin":
        return jsonify({"message": "Admin accounts cannot be disabled from this panel."}), 400

    admin_email = getattr(admin_user, "email", None) if not isinstance(admin_user, dict) else admin_user.get("email")
    if target_user.email == admin_email:
        return jsonify({"message": "You cannot disable your own admin account."}), 400

    target_user.is_disabled = disable_user
    target_user.disabled_at = _utcnow() if disable_user else None
    target_user.disabled_reason = disabled_reason if disable_user else None
    db.session.commit()

    return jsonify(
        {
            "message": (
                f"Disabled user {target_user.email}."
                if disable_user
                else f"Re-enabled user {target_user.email}."
            ),
            "user": _serialize_user(target_user),
        }
    )


@auth_blueprint.route("/users/<int:user_id>/reset-password", methods=["PATCH"])
def admin_reset_user_password(user_id):
    admin_user = _get_admin_user()
    if admin_user is None:
        return jsonify({"message": "Admin access is required."}), 403

    payload = request.get_json(silent=True) or {}
    new_password = str(payload.get("newPassword", ""))

    if not new_password:
        return jsonify({"message": "Please enter a new password."}), 400

    password_error = _validate_password_rules(new_password)
    if password_error:
        return jsonify({"message": password_error}), 400

    target_user = User.query.filter_by(id=user_id).first()

    if target_user is None:
        return jsonify({"message": "User not found."}), 404

    if target_user.role == "admin":
        return jsonify({"message": "Admin account passwords cannot be reset from this panel."}), 400

    admin_email = getattr(admin_user, "email", None) if not isinstance(admin_user, dict) else admin_user.get("email")
    if target_user.email == admin_email:
        return jsonify({"message": "You cannot reset your own admin password from this panel."}), 400

    target_user.password_hash = _generate_compatible_password_hash(new_password)
    db.session.commit()
    current_app.logger.info("Admin reset password for user %s", target_user.email)

    return jsonify({"message": f"Password reset for {target_user.email} was successful."})
