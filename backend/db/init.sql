BEGIN;

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    risk_profile VARCHAR(40) NOT NULL DEFAULT 'Balanced',
    membership VARCHAR(40) NOT NULL DEFAULT 'Regular User',
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    is_disabled BOOLEAN NOT NULL DEFAULT FALSE,
    disabled_at TIMESTAMPTZ,
    disabled_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email
ON users(email);

CREATE TABLE IF NOT EXISTS login_verification_codes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    code_hash TEXT NOT NULL,
    purpose VARCHAR(32) NOT NULL DEFAULT 'admin_login',
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_login_verification_codes_email
ON login_verification_codes(email, created_at DESC);

CREATE TABLE IF NOT EXISTS referral_codes (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    code VARCHAR(16) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_referral_codes_code
ON referral_codes(code);

CREATE TABLE IF NOT EXISTS referrals (
    id BIGSERIAL PRIMARY KEY,
    referrer_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referred_user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    referral_code VARCHAR(16) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'pending',
    qualified_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    rejection_reason VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_referrals_not_self CHECK (referrer_user_id <> referred_user_id)
);

CREATE INDEX IF NOT EXISTS idx_referrals_referrer_status
ON referrals(referrer_user_id, status);

CREATE TABLE IF NOT EXISTS referral_reward_claims (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reward_type VARCHAR(48) NOT NULL DEFAULT 'amplialpha_tshirt',
    qualified_referrals_required INTEGER NOT NULL DEFAULT 10,
    shirt_size VARCHAR(8) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'submitted',
    admin_note VARCHAR(255),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    shipped_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_referral_reward_claim_user_type UNIQUE (user_id, reward_type)
);

CREATE INDEX IF NOT EXISTS idx_referral_reward_claims_status
ON referral_reward_claims(status);

CREATE TABLE IF NOT EXISTS symbols (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL UNIQUE,
    company_name TEXT,
    sector TEXT,
    industry TEXT,
    exchange VARCHAR(32),
    market_cap NUMERIC(20, 2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_prices (
    id BIGSERIAL PRIMARY KEY,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    trade_date DATE NOT NULL,
    open NUMERIC(18, 6) NOT NULL,
    high NUMERIC(18, 6) NOT NULL,
    low NUMERIC(18, 6) NOT NULL,
    close NUMERIC(18, 6) NOT NULL,
    adjusted_close NUMERIC(18, 6),
    volume BIGINT,
    source VARCHAR(32) NOT NULL DEFAULT 'duke_api',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol_id, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date
ON daily_prices(symbol_id, trade_date DESC);

CREATE TABLE IF NOT EXISTS daily_indicators (
    id BIGSERIAL PRIMARY KEY,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    trade_date DATE NOT NULL,
    ma_5 NUMERIC(18, 6),
    ma_10 NUMERIC(18, 6),
    ma_20 NUMERIC(18, 6),
    ma_60 NUMERIC(18, 6),
    ema_5 NUMERIC(18, 6),
    ema_10 NUMERIC(18, 6),
    ema_12 NUMERIC(18, 6),
    ema_20 NUMERIC(18, 6),
    ema_26 NUMERIC(18, 6),
    ema_60 NUMERIC(18, 6),
    macd NUMERIC(18, 6),
    macd_signal NUMERIC(18, 6),
    macd_hist NUMERIC(18, 6),
    rsi_14 NUMERIC(10, 4),
    boll_mid NUMERIC(18, 6),
    boll_upper NUMERIC(18, 6),
    boll_lower NUMERIC(18, 6),
    kdj_k NUMERIC(10, 4),
    kdj_d NUMERIC(10, 4),
    kdj_j NUMERIC(10, 4),
    vol_ma_5 NUMERIC(18, 6),
    vol_ma_20 NUMERIC(18, 6),
    oi NUMERIC(18, 6),
    pbv NUMERIC(18, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol_id, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_indicators_symbol_date
ON daily_indicators(symbol_id, trade_date DESC);

CREATE TABLE IF NOT EXISTS pattern_windows (
    id BIGSERIAL PRIMARY KEY,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    timeframe VARCHAR(16) NOT NULL,
    window_size INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    return_pct NUMERIC(12, 6),
    avg_return NUMERIC(12, 6),
    max_drawdown NUMERIC(12, 6),
    volatility NUMERIC(12, 6),
    probability_score NUMERIC(12, 6),
    ma_slope NUMERIC(12, 6),
    ema_slope NUMERIC(12, 6),
    macd_trend NUMERIC(12, 6),
    rsi_avg NUMERIC(12, 6),
    rsi_min NUMERIC(12, 6),
    rsi_max NUMERIC(12, 6),
    volume_change_ratio NUMERIC(12, 6),
    feature_vector JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol_id, timeframe, window_size, end_date)
);

CREATE INDEX IF NOT EXISTS idx_pattern_windows_lookup
ON pattern_windows(symbol_id, timeframe, window_size, end_date DESC);

CREATE INDEX IF NOT EXISTS idx_pattern_windows_timeframe_window
ON pattern_windows(timeframe, window_size, end_date DESC);

CREATE TABLE IF NOT EXISTS intraday_prices (
    id BIGSERIAL PRIMARY KEY,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    interval VARCHAR(16) NOT NULL,
    bar_time TIMESTAMPTZ NOT NULL,
    open NUMERIC(18, 6) NOT NULL,
    high NUMERIC(18, 6) NOT NULL,
    low NUMERIC(18, 6) NOT NULL,
    close NUMERIC(18, 6) NOT NULL,
    volume BIGINT,
    source VARCHAR(64) NOT NULL DEFAULT 'crypto_exchange',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol_id, interval, bar_time)
);

CREATE INDEX IF NOT EXISTS idx_intraday_prices_symbol_interval_time
ON intraday_prices(symbol_id, interval, bar_time DESC);

CREATE TABLE IF NOT EXISTS intraday_indicators (
    id BIGSERIAL PRIMARY KEY,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    interval VARCHAR(16) NOT NULL,
    bar_time TIMESTAMPTZ NOT NULL,
    ma_5 NUMERIC(18, 6),
    ma_10 NUMERIC(18, 6),
    ma_20 NUMERIC(18, 6),
    ma_60 NUMERIC(18, 6),
    ema_5 NUMERIC(18, 6),
    ema_10 NUMERIC(18, 6),
    ema_12 NUMERIC(18, 6),
    ema_20 NUMERIC(18, 6),
    ema_26 NUMERIC(18, 6),
    ema_60 NUMERIC(18, 6),
    macd NUMERIC(18, 6),
    macd_signal NUMERIC(18, 6),
    macd_hist NUMERIC(18, 6),
    rsi_14 NUMERIC(10, 4),
    boll_mid NUMERIC(18, 6),
    boll_upper NUMERIC(18, 6),
    boll_lower NUMERIC(18, 6),
    kdj_k NUMERIC(10, 4),
    kdj_d NUMERIC(10, 4),
    kdj_j NUMERIC(10, 4),
    vol_ma_5 NUMERIC(18, 6),
    vol_ma_20 NUMERIC(18, 6),
    oi NUMERIC(18, 6),
    pbv NUMERIC(18, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol_id, interval, bar_time)
);

CREATE INDEX IF NOT EXISTS idx_intraday_indicators_symbol_interval_time
ON intraday_indicators(symbol_id, interval, bar_time DESC);

CREATE TABLE IF NOT EXISTS intraday_pattern_windows (
    id BIGSERIAL PRIMARY KEY,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    interval VARCHAR(16) NOT NULL,
    window_size INTEGER NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    return_pct NUMERIC(12, 6),
    avg_return NUMERIC(12, 6),
    max_drawdown NUMERIC(12, 6),
    volatility NUMERIC(12, 6),
    probability_score NUMERIC(12, 6),
    ma_slope NUMERIC(12, 6),
    ema_slope NUMERIC(12, 6),
    macd_trend NUMERIC(12, 6),
    rsi_avg NUMERIC(12, 6),
    rsi_min NUMERIC(12, 6),
    rsi_max NUMERIC(12, 6),
    volume_change_ratio NUMERIC(12, 6),
    feature_vector JSONB,
    source VARCHAR(64) NOT NULL DEFAULT 'crypto_exchange',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol_id, interval, window_size, end_time)
);

CREATE INDEX IF NOT EXISTS idx_intraday_pattern_windows_lookup
ON intraday_pattern_windows(symbol_id, interval, window_size, end_time DESC);

CREATE INDEX IF NOT EXISTS idx_intraday_pattern_windows_interval_window
ON intraday_pattern_windows(interval, window_size, end_time DESC);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id BIGSERIAL PRIMARY KEY,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    run_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    timeframe VARCHAR(16) NOT NULL,
    lookback_window INTEGER NOT NULL,
    indicators TEXT[] NOT NULL,
    probability_of_increase NUMERIC(12, 6),
    recommended_sell_price NUMERIC(18, 6),
    recommended_sell_date DATE,
    stop_loss_price NUMERIC(18, 6),
    avg_return NUMERIC(12, 6),
    max_drawdown NUMERIC(12, 6),
    request_payload JSONB,
    response_payload JSONB
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_symbol_date
ON analysis_runs(symbol_id, run_date DESC);

CREATE TABLE IF NOT EXISTS pattern_matches (
    id BIGSERIAL PRIMARY KEY,
    analysis_run_id BIGINT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    matched_window_id BIGINT NOT NULL REFERENCES pattern_windows(id) ON DELETE CASCADE,
    rank_no INTEGER NOT NULL,
    similarity_score NUMERIC(12, 6) NOT NULL,
    pattern_label TEXT,
    forward_return_5d NUMERIC(12, 6),
    forward_return_10d NUMERIC(12, 6),
    forward_return_20d NUMERIC(12, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pattern_matches_run_rank
ON pattern_matches(analysis_run_id, rank_no);

CREATE TABLE IF NOT EXISTS watchlists (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watchlist_items (
    id BIGSERIAL PRIMARY KEY,
    watchlist_id BIGINT NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(watchlist_id, symbol_id)
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id BIGSERIAL PRIMARY KEY,
    symbol_id BIGINT NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    side VARCHAR(8) NOT NULL,
    entry_price NUMERIC(18, 6) NOT NULL,
    stop_loss NUMERIC(18, 6),
    take_profit NUMERIC(18, 6),
    quantity NUMERIC(18, 6),
    status VARCHAR(16) NOT NULL DEFAULT 'open',
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

COMMIT;
