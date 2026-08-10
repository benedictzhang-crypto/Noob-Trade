import unittest

from flask import Flask

from extensions import db
from models.auth import User, UserWatchlist
from routes.auth_routes import auth_blueprint


class WatchlistRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            SECRET_KEY="watchlist-test-secret",
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_BINDS={"app": "sqlite:///:memory:"},
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            ADMIN_ACCOUNTS=[],
        )
        db.init_app(self.app)
        self.app.register_blueprint(auth_blueprint)

        with self.app.app_context():
            db.create_all()
            db.session.add_all(
                [
                    User(
                        full_name="AlphaUser",
                        email="alpha@example.com",
                        password_hash="unused",
                        email_verified=True,
                    ),
                    User(
                        full_name="BetaUser",
                        email="beta@example.com",
                        password_hash="unused",
                        email_verified=True,
                    ),
                ]
            )
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

    def test_requires_an_authenticated_account(self):
        response = self.client.get("/api/auth/watchlists")

        self.assertEqual(response.status_code, 401)

    def test_first_load_seeds_defaults_once(self):
        self.sign_in_as("alpha@example.com")

        first_response = self.client.get("/api/auth/watchlists")
        second_response = self.client.get("/api/auth/watchlists")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(
            first_response.get_json()["watchlists"],
            {
                "crypto": ["BTC", "ETH", "SOL", "OKB"],
                "stock": ["AAPL", "NVDA", "TSLA"],
            },
        )
        self.assertEqual(second_response.get_json(), first_response.get_json())

        with self.app.app_context():
            self.assertEqual(UserWatchlist.query.count(), 2)

    def test_configured_admin_session_uses_its_own_saved_symbols(self):
        with self.client.session_transaction() as session_state:
            session_state.clear()
            session_state["user_email"] = "owner@example.com"
            session_state["user_role"] = "admin"
            session_state["user_snapshot"] = {
                "email": "owner@example.com",
                "fullName": "Owner",
                "role": "admin",
                "isAdmin": True,
            }

        response = self.client.get("/api/auth/watchlists")
        save_response = self.client.put(
            "/api/auth/watchlists/stock",
            json={"symbols": ["MSFT", "JPM"]},
        )
        reload_response = self.client.get("/api/auth/watchlists")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(reload_response.get_json()["watchlists"]["stock"], ["MSFT", "JPM"])

    def test_saved_symbols_are_separate_by_user_and_market(self):
        self.sign_in_as("alpha@example.com")
        self.client.get("/api/auth/watchlists")

        stock_response = self.client.put(
            "/api/auth/watchlists/stock",
            json={"symbols": ["aapl", "GE", "BRK.B", "GE"]},
        )
        crypto_response = self.client.put(
            "/api/auth/watchlists/crypto",
            json={"symbols": ["btc", "SUSHI"]},
        )

        self.assertEqual(stock_response.status_code, 200)
        self.assertEqual(stock_response.get_json()["symbols"], ["AAPL", "GE", "BRK.B"])
        self.assertEqual(crypto_response.get_json()["symbols"], ["BTC", "SUSHI"])

        self.sign_in_as("beta@example.com")
        beta_response = self.client.get("/api/auth/watchlists")
        self.assertEqual(beta_response.get_json()["watchlists"]["stock"], ["AAPL", "NVDA", "TSLA"])

        self.sign_in_as("alpha@example.com")
        alpha_response = self.client.get("/api/auth/watchlists")
        self.assertEqual(alpha_response.get_json()["watchlists"]["stock"], ["AAPL", "GE", "BRK.B"])
        self.assertEqual(alpha_response.get_json()["watchlists"]["crypto"], ["BTC", "SUSHI"])

    def test_empty_watchlist_remains_empty_after_reload(self):
        self.sign_in_as("alpha@example.com")
        self.client.get("/api/auth/watchlists")

        save_response = self.client.put("/api/auth/watchlists/stock", json={"symbols": []})
        reload_response = self.client.get("/api/auth/watchlists")

        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(reload_response.get_json()["watchlists"]["stock"], [])


if __name__ == "__main__":
    unittest.main()
