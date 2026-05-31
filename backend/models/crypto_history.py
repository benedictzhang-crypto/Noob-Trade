from extensions import db
from models.db_compat import COMPAT_BIGINT


class CryptoAsset(db.Model):
    __tablename__ = "crypto_assets"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    symbol = db.Column(db.String(16), nullable=False, unique=True)
    base_asset = db.Column(db.String(16), nullable=False)
    quote_asset = db.Column(db.String(16), nullable=False, default="USDT")
    venue_symbol = db.Column(db.String(32), nullable=False, unique=True)
    exchange = db.Column(db.String(32), nullable=False, default="binance")
    source = db.Column(db.String(80), nullable=False, default="binance_public_klines")
    first_bar_time = db.Column(db.DateTime(timezone=True))
    last_bar_time = db.Column(db.DateTime(timezone=True))
    row_count = db.Column(COMPAT_BIGINT, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())


class CryptoMinutePrice(db.Model):
    __tablename__ = "crypto_minute_prices"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    asset_id = db.Column(COMPAT_BIGINT, db.ForeignKey("crypto_assets.id", ondelete="CASCADE"), nullable=False)
    exchange = db.Column(db.String(32), nullable=False, default="binance")
    venue_symbol = db.Column(db.String(32), nullable=False)
    bar_time = db.Column(db.DateTime(timezone=True), nullable=False)
    open = db.Column(db.Numeric(24, 10), nullable=False)
    high = db.Column(db.Numeric(24, 10), nullable=False)
    low = db.Column(db.Numeric(24, 10), nullable=False)
    close = db.Column(db.Numeric(24, 10), nullable=False)
    volume = db.Column(db.Numeric(28, 10))
    quote_volume = db.Column(db.Numeric(28, 10))
    trade_count = db.Column(db.Integer)
    taker_buy_base_volume = db.Column(db.Numeric(28, 10))
    taker_buy_quote_volume = db.Column(db.Numeric(28, 10))
    source_file = db.Column(db.String(180), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("asset_id", "exchange", "venue_symbol", "bar_time", name="uq_crypto_minute_price_lookup"),
        db.Index("ix_crypto_minute_prices_asset_time", "asset_id", "bar_time"),
    )


class CryptoMinuteIndicator(db.Model):
    __tablename__ = "crypto_minute_indicators"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    asset_id = db.Column(COMPAT_BIGINT, db.ForeignKey("crypto_assets.id", ondelete="CASCADE"), nullable=False)
    exchange = db.Column(db.String(32), nullable=False, default="binance")
    venue_symbol = db.Column(db.String(32), nullable=False)
    bar_time = db.Column(db.DateTime(timezone=True), nullable=False)
    ma_5 = db.Column(db.Numeric(24, 10))
    ma_10 = db.Column(db.Numeric(24, 10))
    ma_20 = db.Column(db.Numeric(24, 10))
    ma_60 = db.Column(db.Numeric(24, 10))
    ema_5 = db.Column(db.Numeric(24, 10))
    ema_10 = db.Column(db.Numeric(24, 10))
    ema_12 = db.Column(db.Numeric(24, 10))
    ema_20 = db.Column(db.Numeric(24, 10))
    ema_26 = db.Column(db.Numeric(24, 10))
    ema_60 = db.Column(db.Numeric(24, 10))
    macd = db.Column(db.Numeric(24, 10))
    macd_signal = db.Column(db.Numeric(24, 10))
    macd_hist = db.Column(db.Numeric(24, 10))
    boll_mid = db.Column(db.Numeric(24, 10))
    boll_upper = db.Column(db.Numeric(24, 10))
    boll_lower = db.Column(db.Numeric(24, 10))
    rsi_14 = db.Column(db.Numeric(12, 6))
    kdj_k = db.Column(db.Numeric(12, 6))
    kdj_d = db.Column(db.Numeric(12, 6))
    kdj_j = db.Column(db.Numeric(12, 6))
    vol_ma_5 = db.Column(db.Numeric(28, 10))
    vol_ma_20 = db.Column(db.Numeric(28, 10))
    obv = db.Column(db.Numeric(32, 10))
    oi = db.Column(db.Numeric(28, 10))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("asset_id", "exchange", "venue_symbol", "bar_time", name="uq_crypto_minute_indicator_lookup"),
        db.Index("ix_crypto_minute_indicators_asset_time", "asset_id", "bar_time"),
    )


class CryptoIntervalPrice(db.Model):
    __tablename__ = "crypto_interval_prices"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    asset_id = db.Column(COMPAT_BIGINT, db.ForeignKey("crypto_assets.id", ondelete="CASCADE"), nullable=False)
    interval = db.Column(db.String(16), nullable=False)
    exchange = db.Column(db.String(32), nullable=False, default="binance")
    venue_symbol = db.Column(db.String(32), nullable=False)
    bar_time = db.Column(db.DateTime(timezone=True), nullable=False)
    open = db.Column(db.Numeric(24, 10), nullable=False)
    high = db.Column(db.Numeric(24, 10), nullable=False)
    low = db.Column(db.Numeric(24, 10), nullable=False)
    close = db.Column(db.Numeric(24, 10), nullable=False)
    volume = db.Column(db.Numeric(28, 10))
    quote_volume = db.Column(db.Numeric(28, 10))
    trade_count = db.Column(db.Integer)
    taker_buy_base_volume = db.Column(db.Numeric(28, 10))
    taker_buy_quote_volume = db.Column(db.Numeric(28, 10))
    source_interval = db.Column(db.String(16), nullable=False, default="1m")
    source = db.Column(db.String(80), nullable=False, default="binance_public_klines_derived")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("asset_id", "interval", "exchange", "venue_symbol", "bar_time", name="uq_crypto_interval_price_lookup"),
        db.Index("ix_crypto_interval_prices_asset_interval_time", "asset_id", "interval", "bar_time"),
    )


class CryptoIntervalIndicator(db.Model):
    __tablename__ = "crypto_interval_indicators"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    asset_id = db.Column(COMPAT_BIGINT, db.ForeignKey("crypto_assets.id", ondelete="CASCADE"), nullable=False)
    interval = db.Column(db.String(16), nullable=False)
    exchange = db.Column(db.String(32), nullable=False, default="binance")
    venue_symbol = db.Column(db.String(32), nullable=False)
    bar_time = db.Column(db.DateTime(timezone=True), nullable=False)
    ma_5 = db.Column(db.Numeric(24, 10))
    ma_10 = db.Column(db.Numeric(24, 10))
    ma_20 = db.Column(db.Numeric(24, 10))
    ma_60 = db.Column(db.Numeric(24, 10))
    ema_5 = db.Column(db.Numeric(24, 10))
    ema_10 = db.Column(db.Numeric(24, 10))
    ema_12 = db.Column(db.Numeric(24, 10))
    ema_20 = db.Column(db.Numeric(24, 10))
    ema_26 = db.Column(db.Numeric(24, 10))
    ema_60 = db.Column(db.Numeric(24, 10))
    macd = db.Column(db.Numeric(24, 10))
    macd_signal = db.Column(db.Numeric(24, 10))
    macd_hist = db.Column(db.Numeric(24, 10))
    boll_mid = db.Column(db.Numeric(24, 10))
    boll_upper = db.Column(db.Numeric(24, 10))
    boll_lower = db.Column(db.Numeric(24, 10))
    rsi_14 = db.Column(db.Numeric(12, 6))
    kdj_k = db.Column(db.Numeric(12, 6))
    kdj_d = db.Column(db.Numeric(12, 6))
    kdj_j = db.Column(db.Numeric(12, 6))
    vol_ma_5 = db.Column(db.Numeric(28, 10))
    vol_ma_20 = db.Column(db.Numeric(28, 10))
    obv = db.Column(db.Numeric(32, 10))
    oi = db.Column(db.Numeric(28, 10))
    source_interval = db.Column(db.String(16), nullable=False, default="1m")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    __table_args__ = (
        db.UniqueConstraint("asset_id", "interval", "exchange", "venue_symbol", "bar_time", name="uq_crypto_interval_indicator_lookup"),
        db.Index("ix_crypto_interval_indicators_asset_interval_time", "asset_id", "interval", "bar_time"),
    )
