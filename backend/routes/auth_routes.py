from datetime import datetime, timedelta
import html
import secrets

from flask import Blueprint, current_app, jsonify, request, session
from extensions import db
from models.auth import LoginActivity, LoginVerificationCode, User
from services.email_service import EmailService
from services.security_service import hash_secret, needs_rehash, verify_secret

auth_blueprint = Blueprint("auth", __name__, url_prefix="/api/auth")


def _utcnow():
    return datetime.utcnow()


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


def _session_response_payload():
    session_email = str(session.get("user_email", "")).strip().lower()

    if not session_email:
        return None

    user = _find_user_by_email(session_email)
    if user is None:
        return None
    if bool(getattr(user, "is_disabled", False)):
        session.clear()
        return None

    if user.role == "admin":
        users = User.query.order_by(User.created_at.asc()).all()
        display_code_map = _build_display_code_map(users)
        return {
            "user": _serialize_user_with_display_code(user, display_code_map),
            "adminUsers": _serialize_admin_users_with_map(users, display_code_map),
        }

    return {
        "user": _serialize_user(user),
        "adminUsers": None,
    }


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


def _consume_security_code(user, purpose, code):
    recent_codes = LoginVerificationCode.query.filter_by(
        user_id=user.id,
        email=user.email,
        purpose=purpose,
        used_at=None,
    ).order_by(LoginVerificationCode.created_at.desc()).limit(5).all()

    now = _utcnow()

    for record in recent_codes:
        if record.expires_at and record.expires_at < now:
            continue

        if verify_secret(record.code_hash, code):
            record.used_at = now
            db.session.commit()
            return True

    return False


def _find_user_by_email(email):
    return User.query.filter_by(email=email).first()


def _validate_password_rules(password):
    if len(password) < 8:
        return "Please use a password with at least 8 characters."
    if password.isalnum():
        return "Please include at least one special symbol such as _, !, or # in your password."
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
        return jsonify({"message": "Please complete name, email, and password."}), 400

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

    code = _issue_security_code(
        user=user,
        purpose="email_verification",
        expiry_minutes=current_app.config.get("EMAIL_VERIFICATION_CODE_EXPIRY_MINUTES", 15),
    )

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

    code = _issue_security_code(
        user=user,
        purpose="email_verification",
        expiry_minutes=current_app.config.get("EMAIL_VERIFICATION_CODE_EXPIRY_MINUTES", 15),
    )

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

    code = _issue_security_code(
        user=user,
        purpose="password_reset",
        expiry_minutes=current_app.config.get("PASSWORD_RESET_CODE_EXPIRY_MINUTES", 15),
    )

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

    session.clear()
    session.update(_session_user_payload(user))

    message = f"Welcome back, {user.full_name}."
    notice_sent = False
    notice_error = None

    if user.role != "admin":
        notice_sent, notice_error = _send_login_notice(user)
        if notice_sent:
            message = f"Welcome back, {user.full_name}. A login notice was sent to {user.email}."
        elif notice_error:
            message = f"Welcome back, {user.full_name}. Login notice email is unavailable right now."

    serialized_user = _serialize_user(user)
    admin_users = None

    if user.role == "admin":
        users = User.query.order_by(User.created_at.asc()).all()
        display_code_map = _build_display_code_map(users)
        serialized_user = _serialize_user_with_display_code(user, display_code_map)
        admin_users = _serialize_admin_users_with_map(users, display_code_map)

    return jsonify(
        {
            "code": 200,
            "message": message,
            "emailNoticeSent": notice_sent,
            "emailNoticeMessage": notice_error,
            "user": serialized_user,
            "adminUsers": admin_users,
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

    if target_user.email == admin_user.email:
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
