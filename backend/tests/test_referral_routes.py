import unittest
from unittest.mock import patch

from flask import Flask

from extensions import db
from models.auth import Referral, ReferralRewardClaim, User
from routes.auth_routes import auth_blueprint
from services.referral_service import ensure_referral_code
from services.security_service import hash_secret


class _EmailStub:
    def send_email_verification_code(self, email, code):
        del email, code


class ReferralRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            SECRET_KEY="referral-test-secret",
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_BINDS={"app": "sqlite:///:memory:"},
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            ADMIN_ACCOUNTS=[],
            PUBLIC_APP_URL="https://www.noobtrading.com",
        )
        db.init_app(self.app)
        self.app.register_blueprint(auth_blueprint)

        with self.app.app_context():
            db.create_all()
            referrer = User(
                full_name="InviterOne",
                email="inviter@example.com",
                password_hash=hash_secret("Password!1"),
                email_verified=True,
            )
            db.session.add(referrer)
            db.session.flush()
            self.referral_code = ensure_referral_code(referrer).code
            db.session.commit()

        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def sign_in_as(self, email):
        with self.client.session_transaction() as session_state:
            session_state.clear()
            session_state["user_email"] = email
            session_state["user_role"] = "user"

    def register_referred_user(self, email="friend@example.com"):
        with (
            patch("routes.auth_routes._email_delivery_available", return_value=True),
            patch("routes.auth_routes._issue_security_code_or_response", return_value=("123456", None)),
            patch("routes.auth_routes._email_service", return_value=_EmailStub()),
        ):
            return self.client.post(
                "/api/auth/register",
                json={
                    "fullName": "FriendOne",
                    "email": email,
                    "password": "Password!1",
                    "referralCode": self.referral_code,
                },
            )

    def test_register_creates_pending_referral_then_verification_qualifies_it(self):
        response = self.register_referred_user()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["referralCodeApplied"], self.referral_code)

        with self.app.app_context():
            referral = Referral.query.one()
            self.assertEqual(referral.status, "pending")

        with patch("routes.auth_routes._consume_security_code", return_value=True):
            verification_response = self.client.post(
                "/api/auth/verify-email/confirm",
                json={"email": "friend@example.com", "code": "123456"},
            )

        self.assertEqual(verification_response.status_code, 200)
        with self.app.app_context():
            referral = Referral.query.one()
            self.assertEqual(referral.status, "qualified")
            self.assertIsNotNone(referral.qualified_at)

    def test_invalid_referral_code_does_not_create_account(self):
        with patch("routes.auth_routes._email_delivery_available", return_value=True):
            response = self.client.post(
                "/api/auth/register",
                json={
                    "fullName": "FriendTwo",
                    "email": "friend2@example.com",
                    "password": "Password!1",
                    "referralCode": "NT-INVALID",
                },
            )

        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertIsNone(User.query.filter_by(email="friend2@example.com").first())

    def test_registration_without_referral_still_works(self):
        with (
            patch("routes.auth_routes._email_delivery_available", return_value=True),
            patch("routes.auth_routes._issue_security_code_or_response", return_value=("123456", None)),
            patch("routes.auth_routes._email_service", return_value=_EmailStub()),
        ):
            response = self.client.post(
                "/api/auth/register",
                json={
                    "fullName": "DirectUser",
                    "email": "direct@example.com",
                    "password": "Password!1",
                },
            )

        self.assertEqual(response.status_code, 201)
        with self.app.app_context():
            self.assertIsNotNone(User.query.filter_by(email="direct@example.com").first())
            self.assertEqual(Referral.query.count(), 0)

    def test_invite_dashboard_returns_code_link_and_progress(self):
        self.sign_in_as("inviter@example.com")
        response = self.client.get("/api/auth/referrals/me")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["code"], self.referral_code)
        self.assertEqual(payload["inviteLink"], f"https://www.noobtrading.com/r/{self.referral_code}")
        self.assertEqual(payload["reward"]["required"], 10)
        self.assertEqual(payload["reward"]["qualified"], 0)

    def test_tshirt_claim_unlocks_after_ten_qualified_referrals(self):
        with self.app.app_context():
            referrer = User.query.filter_by(email="inviter@example.com").one()
            for index in range(10):
                friend = User(
                    full_name=f"Friend{index}",
                    email=f"friend{index}@example.com",
                    password_hash="unused",
                    email_verified=True,
                )
                db.session.add(friend)
                db.session.flush()
                db.session.add(
                    Referral(
                        referrer_user_id=referrer.id,
                        referred_user_id=friend.id,
                        referral_code=self.referral_code,
                        status="qualified",
                    )
                )
            db.session.commit()

        self.sign_in_as("inviter@example.com")
        response = self.client.post("/api/auth/referrals/claim", json={"shirtSize": "M"})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["claim"]["shirtSize"], "M")
        with self.app.app_context():
            self.assertEqual(ReferralRewardClaim.query.count(), 1)

        duplicate_response = self.client.post("/api/auth/referrals/claim", json={"shirtSize": "L"})
        self.assertEqual(duplicate_response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(ReferralRewardClaim.query.count(), 1)

    def test_tshirt_claim_is_blocked_before_ten_qualified_referrals(self):
        self.sign_in_as("inviter@example.com")
        response = self.client.post("/api/auth/referrals/claim", json={"shirtSize": "M"})

        self.assertEqual(response.status_code, 403)
        with self.app.app_context():
            self.assertEqual(ReferralRewardClaim.query.count(), 0)


if __name__ == "__main__":
    unittest.main()
