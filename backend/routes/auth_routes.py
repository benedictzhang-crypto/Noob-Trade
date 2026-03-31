from datetime import datetime, timedelta
import html
import secrets

from flask import Blueprint, current_app, jsonify, request, session
from extensions import db
from models.auth import LoginActivity, LoginVerificationCode, User
from services.email_service import EmailService
from services.security_service import hash_secret, needs_rehash, verify_secret

auth_blueprint = Blueprint("auth", __name__, url_prefix="/api/auth")
auth_legacy_blueprint = Blueprint("auth_legacy", __name__, url_prefix="/api")


TEMP_USERS = {
    "zzzzhly@126.com": {
        "password": "Happy20252026",
        "full_name": "Noob Trade Admin",
        "risk_profile": "Balanced",
        "membership": "Administrator",
        "role": "admin",
        "email_verified": True,
    },
    "690991780@qq.com": {
        "password": "mmd750114",
        "full_name": "Noob Trade Admin 2",
        "risk_profile": "Balanced",
        "membership": "Administrator",
        "role": "admin",
        "email_verified": True,
    },
    "user1@example.com": {
        "password": "user12345",
        "full_name": "Demo User",
        "risk_profile": "Balanced",
        "membership": "Regular User",
        "role": "user",
        "email_verified": True,
    },
}


def _utcnow():
    return datetime.utcnow()


def _serialize_user(user):
    return {
        "id": user.id,
        "fullName": user.full_name,
        "email": user.email,
        "riskProfile": user.risk_profile,
        "membership": user.membership,
        "joinedAt": user.created_at.strftime("%B %Y") if user.created_at else "Recent",
        "role": user.role,
        "isAdmin": user.role == "admin",
        "emailVerified": bool(getattr(user, "email_verified", False)),
    }


def _sanitize_text(value, max_length=255):
    return html.escape(str(value or "").strip())[:max_length]


def _serialize_temp_user(email, temp_user, user_id=None):
    role = temp_user.get("role", "user")
    return {
        "id": user_id if user_id is not None else abs(hash(email)) % 1000000,
        "fullName": temp_user.get("full_name", email.split("@")[0]),
        "email": email,
        "riskProfile": temp_user.get("risk_profile", "Balanced"),
        "membership": temp_user.get("membership", "Regular User"),
        "joinedAt": "Local Session",
        "role": role,
        "isAdmin": role == "admin",
        "emailVerified": temp_user.get("email_verified", True),
    }


def _get_admin_user():
    admin_email = str(session.get("user_email", "")).strip().lower()

    if not admin_email:
        return None

    if not current_app.config.get("DB_AVAILABLE", True):
        temp_user = _temp_user_for_email(admin_email)
        if temp_user and temp_user.get("role") == "admin":
            return {"email": admin_email, "role": "admin"}
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

    if not current_app.config.get("DB_AVAILABLE", True):
        temp_user = _temp_user_for_email(session_email)
        if temp_user is None:
            return None
        return _serialize_temp_user(session_email, temp_user)

    user = _find_user_by_email(session_email)
    if user is None:
        return None

    return _serialize_user(user)


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


def _temp_user_for_email(email):
    return TEMP_USERS.get(email)


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
    if not current_app.config.get("DB_AVAILABLE", True):
        return jsonify({"message": "Registration is temporarily unavailable because the database is offline."}), 503

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
    if not current_app.config.get("DB_AVAILABLE", True):
        return jsonify({"message": "Email verification is temporarily unavailable because the database is offline."}), 503

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
    if not current_app.config.get("DB_AVAILABLE", True):
        return jsonify({"message": "Email verification is temporarily unavailable because the database is offline."}), 503

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
    if not current_app.config.get("DB_AVAILABLE", True):
        return jsonify({"message": "Password reset is temporarily unavailable because the database is offline."}), 503

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
    if not current_app.config.get("DB_AVAILABLE", True):
        return jsonify({"message": "Password reset is temporarily unavailable because the database is offline."}), 503

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

    if not current_app.config.get("DB_AVAILABLE", True):
        temp_user = _temp_user_for_email(email)

        if temp_user is None or temp_user.get("password") != password:
            return jsonify({"message": "Incorrect email or password."}), 401

        message = f"Welcome back, {temp_user['full_name']}."

        return jsonify(
            {
                "code": 200,
                "message": message,
                "emailNoticeSent": False,
                "emailNoticeMessage": None,
                "user": _serialize_temp_user(email, temp_user),
                "csrfToken": _issue_csrf_token(),
            }
        ), 200

    user = _find_user_by_email(email)

    if user is None or not verify_secret(user.password_hash, password):
        return jsonify({"message": "Incorrect email or password."}), 401

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

    return jsonify(
        {
            "code": 200,
            "message": message,
            "emailNoticeSent": notice_sent,
            "emailNoticeMessage": notice_error,
            "user": _serialize_user(user),
            "csrfToken": _issue_csrf_token(),
        }
    )


@auth_blueprint.route("/csrf-token", methods=["GET"])
def csrf_token():
    return jsonify({"csrfToken": session.get("csrf_token") or _issue_csrf_token()})


@auth_blueprint.route("/session", methods=["GET"])
def auth_session():
    user_payload = _session_response_payload()

    if user_payload is None:
        return jsonify({"authenticated": False, "user": None}), 401

    return jsonify(
        {
            "authenticated": True,
            "user": user_payload,
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


@auth_legacy_blueprint.route("/login", methods=["POST"])
def login_legacy():
    return _login_impl()


@auth_legacy_blueprint.route("/session", methods=["GET"])
def auth_session_legacy():
    return auth_session()


@auth_blueprint.route("/users", methods=["GET"])
def list_users():
    admin_user = _get_admin_user()
    if admin_user is None:
        return jsonify({"message": "Admin access is required."}), 403

    if not current_app.config.get("DB_AVAILABLE", True):
        return jsonify(
            {
                "users": [
                    {
                        **_serialize_temp_user(email, temp_user, index),
                        "createdAt": None,
                    }
                    for index, (email, temp_user) in enumerate(TEMP_USERS.items())
                ]
            }
        )

    users = User.query.order_by(User.created_at.asc()).all()
    return jsonify(
        {
            "users": [
                {
                    **_serialize_user(user),
                    "createdAt": user.created_at.isoformat() if user.created_at else None,
                }
                for user in users
            ]
        }
    )


@auth_blueprint.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    admin_user = _get_admin_user()
    if admin_user is None:
        return jsonify({"message": "Admin access is required."}), 403

    if not current_app.config.get("DB_AVAILABLE", True):
        temp_items = list(TEMP_USERS.items())

        if user_id < 0 or user_id >= len(temp_items):
            return jsonify({"message": "User not found."}), 404

        email, temp_user = temp_items[user_id]

        if temp_user.get("role") == "admin":
            return jsonify({"message": "Admin accounts cannot be deleted from this panel."}), 400

        del TEMP_USERS[email]
        return jsonify({"message": f"Deleted user {email}."})

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
