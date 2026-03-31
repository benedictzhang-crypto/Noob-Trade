from extensions import db
from models.db_compat import COMPAT_BIGINT


class Watchlist(db.Model):
    __tablename__ = "watchlists"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())


class WatchlistItem(db.Model):
    __tablename__ = "watchlist_items"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    watchlist_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("watchlists.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("watchlist_id", "symbol_id", name="uq_watchlist_items_watchlist_symbol"),
    )


class PaperTrade(db.Model):
    __tablename__ = "paper_trades"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    symbol_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=False,
    )
    side = db.Column(db.String(8), nullable=False)
    entry_price = db.Column(db.Numeric(18, 6), nullable=False)
    stop_loss = db.Column(db.Numeric(18, 6))
    take_profit = db.Column(db.Numeric(18, 6))
    quantity = db.Column(db.Numeric(18, 6))
    status = db.Column(db.String(16), nullable=False, default="open")
    opened_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    closed_at = db.Column(db.DateTime(timezone=True))
