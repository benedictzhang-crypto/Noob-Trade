from flask_sqlalchemy import SQLAlchemy

# A single shared SQLAlchemy object keeps setup simple across the app.
db = SQLAlchemy()
