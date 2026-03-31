from extensions import db
from models.db_compat import COMPAT_BIGINT


class Symbol(db.Model):
    __tablename__ = "symbols"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    symbol = db.Column(db.String(16), unique=True, nullable=False)
    company_name = db.Column(db.Text)
    sector = db.Column(db.Text)
    industry = db.Column(db.Text)
    exchange = db.Column(db.String(32))
    market_cap = db.Column(db.Numeric(20, 2))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())


class DailyPrice(db.Model):
    __tablename__ = "daily_prices"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    symbol_id = db.Column(COMPAT_BIGINT, db.ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False)
    trade_date = db.Column(db.Date, nullable=False)
    open = db.Column(db.Numeric(18, 6), nullable=False)
    high = db.Column(db.Numeric(18, 6), nullable=False)
    low = db.Column(db.Numeric(18, 6), nullable=False)
    close = db.Column(db.Numeric(18, 6), nullable=False)
    adjusted_close = db.Column(db.Numeric(18, 6))
    volume = db.Column(db.BigInteger)
    source = db.Column(db.String(32), nullable=False, default="duke_api")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("symbol_id", "trade_date", name="uq_daily_prices_symbol_trade_date"),
    )


class DailyIndicator(db.Model):
    __tablename__ = "daily_indicators"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    symbol_id = db.Column(COMPAT_BIGINT, db.ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False)
    trade_date = db.Column(db.Date, nullable=False)
    ma_5 = db.Column(db.Numeric(18, 6))
    ma_10 = db.Column(db.Numeric(18, 6))
    ma_20 = db.Column(db.Numeric(18, 6))
    ma_60 = db.Column(db.Numeric(18, 6))
    ema_5 = db.Column(db.Numeric(18, 6))
    ema_10 = db.Column(db.Numeric(18, 6))
    ema_12 = db.Column(db.Numeric(18, 6))
    ema_20 = db.Column(db.Numeric(18, 6))
    ema_26 = db.Column(db.Numeric(18, 6))
    ema_60 = db.Column(db.Numeric(18, 6))
    macd = db.Column(db.Numeric(18, 6))
    macd_signal = db.Column(db.Numeric(18, 6))
    macd_hist = db.Column(db.Numeric(18, 6))
    rsi_14 = db.Column(db.Numeric(10, 4))
    boll_mid = db.Column(db.Numeric(18, 6))
    boll_upper = db.Column(db.Numeric(18, 6))
    boll_lower = db.Column(db.Numeric(18, 6))
    kdj_k = db.Column(db.Numeric(10, 4))
    kdj_d = db.Column(db.Numeric(10, 4))
    kdj_j = db.Column(db.Numeric(10, 4))
    vol_ma_5 = db.Column(db.Numeric(18, 6))
    vol_ma_20 = db.Column(db.Numeric(18, 6))
    oi = db.Column(db.Numeric(18, 6))
    pbv = db.Column(db.Numeric(18, 6))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("symbol_id", "trade_date", name="uq_daily_indicators_symbol_trade_date"),
    )


class PatternWindow(db.Model):
    __tablename__ = "pattern_windows"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    symbol_id = db.Column(COMPAT_BIGINT, db.ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False)
    timeframe = db.Column(db.String(16), nullable=False)
    window_size = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    return_pct = db.Column(db.Numeric(12, 6))
    avg_return = db.Column(db.Numeric(12, 6))
    max_drawdown = db.Column(db.Numeric(12, 6))
    volatility = db.Column(db.Numeric(12, 6))
    probability_score = db.Column(db.Numeric(12, 6))
    ma_slope = db.Column(db.Numeric(12, 6))
    ema_slope = db.Column(db.Numeric(12, 6))
    macd_trend = db.Column(db.Numeric(12, 6))
    rsi_avg = db.Column(db.Numeric(12, 6))
    rsi_min = db.Column(db.Numeric(12, 6))
    rsi_max = db.Column(db.Numeric(12, 6))
    volume_change_ratio = db.Column(db.Numeric(12, 6))
    feature_vector = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint(
            "symbol_id",
            "timeframe",
            "window_size",
            "end_date",
            name="uq_pattern_windows_lookup",
        ),
    )
