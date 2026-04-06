from extensions import db
from models.db_compat import COMPAT_BIGINT


class User(db.Model):
    __bind_key__ = "app"
    __tablename__ = "users"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.Text, nullable=False)
    risk_profile = db.Column(db.String(40), nullable=False, default="Balanced")
    membership = db.Column(db.String(40), nullable=False, default="Regular User")
    role = db.Column(db.String(20), nullable=False, default="user")
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    verified_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())


class LoginVerificationCode(db.Model):
    __bind_key__ = "app"
    __tablename__ = "login_verification_codes"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    email = db.Column(db.String(255), nullable=False, index=True)
    code_hash = db.Column(db.Text, nullable=False)
    purpose = db.Column(db.String(32), nullable=False, default="admin_login")
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())


class LoginActivity(db.Model):
    __bind_key__ = "app"
    __tablename__ = "login_activities"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    email = db.Column(db.String(255), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=False)
    user_agent = db.Column(db.Text, nullable=False)
    device_label = db.Column(db.String(255), nullable=False)
    location_label = db.Column(db.String(255), nullable=False)
    is_new_device = db.Column(db.Boolean, nullable=False, default=False)
    is_new_location = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
