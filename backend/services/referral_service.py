import secrets
from datetime import datetime, timezone

from sqlalchemy import func

from extensions import db
from models.auth import Referral, ReferralCode, ReferralRewardClaim, User


REFERRAL_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
REFERRAL_CODE_PREFIX = "NT-"
REFERRAL_CODE_LENGTH = 8
REFERRAL_REWARD_THRESHOLD = 10
REFERRAL_REWARD_TYPE = "amplialpha_tshirt"
REFERRAL_STATUSES = {"pending", "qualified", "rejected"}
REWARD_CLAIM_STATUSES = {"submitted", "approved", "shipped", "rejected"}
SHIRT_SIZES = {"XS", "S", "M", "L", "XL", "2XL", "3XL"}


def _utcnow():
    return datetime.now(timezone.utc)


def normalize_referral_code(value):
    raw_value = str(value or "").strip().upper()
    if not raw_value:
        return ""
    if "/" in raw_value:
        raw_value = raw_value.rstrip("/").rsplit("/", 1)[-1]
    compact = "".join(character for character in raw_value if character.isalnum())
    if compact.startswith("NT"):
        compact = compact[2:]
    if len(compact) != REFERRAL_CODE_LENGTH:
        return ""
    if any(character not in REFERRAL_ALPHABET for character in compact):
        return ""
    return f"{REFERRAL_CODE_PREFIX}{compact}"


def ensure_referral_code(user):
    existing = ReferralCode.query.filter_by(user_id=user.id).first()
    if existing is not None:
        return existing

    for _ in range(20):
        random_part = "".join(secrets.choice(REFERRAL_ALPHABET) for _ in range(REFERRAL_CODE_LENGTH))
        code = f"{REFERRAL_CODE_PREFIX}{random_part}"
        if ReferralCode.query.filter_by(code=code).first() is None:
            record = ReferralCode(user_id=user.id, code=code)
            db.session.add(record)
            db.session.flush()
            return record

    raise RuntimeError("Could not create a unique referral code.")


def valid_referral_code_record(value):
    normalized = normalize_referral_code(value)
    if not normalized:
        return None

    record = ReferralCode.query.filter_by(code=normalized).first()
    if record is None:
        return None

    referrer = User.query.filter_by(id=record.user_id).first()
    if (
        referrer is None
        or not bool(referrer.email_verified)
        or bool(referrer.is_disabled)
        or referrer.role == "admin"
    ):
        return None
    return record


def attach_referral(referred_user, code_record):
    if code_record is None:
        return None

    existing = Referral.query.filter_by(referred_user_id=referred_user.id).first()
    if existing is not None:
        return existing
    if code_record.user_id == referred_user.id:
        raise ValueError("You cannot use your own referral code.")

    status = "qualified" if bool(referred_user.email_verified) else "pending"
    referral = Referral(
        referrer_user_id=code_record.user_id,
        referred_user_id=referred_user.id,
        referral_code=code_record.code,
        status=status,
        qualified_at=_utcnow() if status == "qualified" else None,
    )
    db.session.add(referral)
    return referral


def qualify_referral_for_user(referred_user):
    referral = Referral.query.filter_by(referred_user_id=referred_user.id).first()
    if referral is None or referral.status != "pending":
        return referral
    if not bool(referred_user.email_verified) or bool(referred_user.is_disabled):
        return referral

    referral.status = "qualified"
    referral.qualified_at = _utcnow()
    referral.rejected_at = None
    referral.rejection_reason = None
    return referral


def qualified_referral_count(user_id):
    return int(
        db.session.query(func.count(Referral.id))
        .filter(
            Referral.referrer_user_id == user_id,
            Referral.status == "qualified",
        )
        .scalar()
        or 0
    )


def serialize_reward_claim(claim):
    if claim is None:
        return None
    return {
        "id": claim.id,
        "rewardType": claim.reward_type,
        "shirtSize": claim.shirt_size,
        "status": claim.status,
        "adminNote": claim.admin_note,
        "submittedAt": claim.submitted_at.isoformat() if claim.submitted_at else None,
        "approvedAt": claim.approved_at.isoformat() if claim.approved_at else None,
        "shippedAt": claim.shipped_at.isoformat() if claim.shipped_at else None,
    }


def referral_dashboard(user, public_app_url):
    code_record = ensure_referral_code(user)
    referrals = (
        Referral.query.filter_by(referrer_user_id=user.id)
        .order_by(Referral.created_at.desc(), Referral.id.desc())
        .all()
    )
    referred_users = {
        referred_user.id: referred_user
        for referred_user in User.query.filter(
            User.id.in_([referral.referred_user_id for referral in referrals] or [-1])
        ).all()
    }
    status_counts = {status: 0 for status in sorted(REFERRAL_STATUSES)}
    serialized_referrals = []
    for referral in referrals:
        status_counts[referral.status] = status_counts.get(referral.status, 0) + 1
        referred_user = referred_users.get(referral.referred_user_id)
        serialized_referrals.append(
            {
                "id": referral.id,
                "friendName": referred_user.full_name if referred_user else "Invited friend",
                "status": referral.status,
                "createdAt": referral.created_at.isoformat() if referral.created_at else None,
                "qualifiedAt": referral.qualified_at.isoformat() if referral.qualified_at else None,
            }
        )

    qualified_count = status_counts.get("qualified", 0)
    claim = ReferralRewardClaim.query.filter_by(
        user_id=user.id,
        reward_type=REFERRAL_REWARD_TYPE,
    ).first()
    base_url = str(public_app_url or "https://www.noobtrading.com").strip().rstrip("/")

    return {
        "code": code_record.code,
        "inviteLink": f"{base_url}/r/{code_record.code}",
        "reward": {
            "name": "AmpliAlpha T-shirt",
            "required": REFERRAL_REWARD_THRESHOLD,
            "qualified": qualified_count,
            "remaining": max(0, REFERRAL_REWARD_THRESHOLD - qualified_count),
            "unlocked": qualified_count >= REFERRAL_REWARD_THRESHOLD,
            "eligibleToClaim": qualified_count >= REFERRAL_REWARD_THRESHOLD and claim is None,
        },
        "counts": status_counts,
        "referrals": serialized_referrals,
        "claim": serialize_reward_claim(claim),
        "shirtSizes": sorted(SHIRT_SIZES, key=lambda size: ["XS", "S", "M", "L", "XL", "2XL", "3XL"].index(size)),
    }


def submit_reward_claim(user, shirt_size):
    normalized_size = str(shirt_size or "").strip().upper()
    if normalized_size not in SHIRT_SIZES:
        raise ValueError("Please select a valid T-shirt size.")
    if qualified_referral_count(user.id) < REFERRAL_REWARD_THRESHOLD:
        raise PermissionError("Ten verified referrals are required before claiming this reward.")

    existing = ReferralRewardClaim.query.filter_by(
        user_id=user.id,
        reward_type=REFERRAL_REWARD_TYPE,
    ).first()
    if existing is not None:
        return existing, False

    claim = ReferralRewardClaim(
        user_id=user.id,
        reward_type=REFERRAL_REWARD_TYPE,
        qualified_referrals_required=REFERRAL_REWARD_THRESHOLD,
        shirt_size=normalized_size,
        status="submitted",
    )
    db.session.add(claim)
    db.session.flush()
    return claim, True
