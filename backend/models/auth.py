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
    is_disabled = db.Column(db.Boolean, nullable=False, default=False)
    disabled_at = db.Column(db.DateTime(timezone=True))
    disabled_reason = db.Column(db.String(255))
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


class UsageActivity(db.Model):
    __bind_key__ = "app"
    __tablename__ = "usage_activities"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = db.Column(db.String(32), nullable=False, index=True)
    market = db.Column(db.String(16), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now(), index=True)


class UserWatchlist(db.Model):
    __bind_key__ = "app"
    __tablename__ = "user_watchlists"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    owner_email = db.Column(db.String(255), nullable=False, index=True)
    market = db.Column(db.String(16), nullable=False)
    symbols = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    __table_args__ = (
        db.UniqueConstraint("owner_email", "market", name="uq_user_watchlists_owner_market"),
    )


class ReferralCode(db.Model):
    __bind_key__ = "app"
    __tablename__ = "referral_codes"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    code = db.Column(db.String(16), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())


class Referral(db.Model):
    __bind_key__ = "app"
    __tablename__ = "referrals"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    referrer_user_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referred_user_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    referral_code = db.Column(db.String(16), nullable=False, index=True)
    status = db.Column(db.String(24), nullable=False, default="pending", index=True)
    qualified_at = db.Column(db.DateTime(timezone=True))
    rejected_at = db.Column(db.DateTime(timezone=True))
    rejection_reason = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    __table_args__ = (
        db.CheckConstraint(
            "referrer_user_id <> referred_user_id",
            name="ck_referrals_not_self",
        ),
    )


class ReferralRewardClaim(db.Model):
    __bind_key__ = "app"
    __tablename__ = "referral_reward_claims"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reward_type = db.Column(db.String(48), nullable=False, default="amplialpha_tshirt")
    qualified_referrals_required = db.Column(db.Integer, nullable=False, default=10)
    shirt_size = db.Column(db.String(8), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="submitted", index=True)
    admin_note = db.Column(db.String(255))
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    approved_at = db.Column(db.DateTime(timezone=True))
    shipped_at = db.Column(db.DateTime(timezone=True))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "reward_type", name="uq_referral_reward_claim_user_type"),
    )


class AssistantIntentFeedback(db.Model):
    __bind_key__ = "app"
    __tablename__ = "assistant_intent_feedback"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    user_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    transcript = db.Column(db.Text, nullable=False)
    predicted_intent = db.Column(db.String(80), nullable=False, default="unknown")
    predicted_entities = db.Column(db.JSON)
    corrected_intent = db.Column(db.String(80))
    corrected_entities = db.Column(db.JSON)
    language = db.Column(db.String(12), nullable=False, default="en")
    source = db.Column(db.String(32), nullable=False, default="voice")
    context_payload = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
