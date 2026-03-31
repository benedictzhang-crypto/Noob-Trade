from extensions import db
from models.db_compat import COMPAT_BIGINT, StringListType


class AnalysisRun(db.Model):
    __tablename__ = "analysis_runs"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    symbol_id = db.Column(COMPAT_BIGINT, db.ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False)
    run_date = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    timeframe = db.Column(db.String(16), nullable=False)
    lookback_window = db.Column(db.Integer, nullable=False)
    indicators = db.Column(StringListType(), nullable=False)
    probability_of_increase = db.Column(db.Numeric(12, 6))
    recommended_sell_price = db.Column(db.Numeric(18, 6))
    recommended_sell_date = db.Column(db.Date)
    stop_loss_price = db.Column(db.Numeric(18, 6))
    avg_return = db.Column(db.Numeric(12, 6))
    max_drawdown = db.Column(db.Numeric(12, 6))
    request_payload = db.Column(db.JSON)
    response_payload = db.Column(db.JSON)


class PatternMatch(db.Model):
    __tablename__ = "pattern_matches"

    id = db.Column(COMPAT_BIGINT, primary_key=True, autoincrement=True)
    analysis_run_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    matched_window_id = db.Column(
        COMPAT_BIGINT,
        db.ForeignKey("pattern_windows.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank_no = db.Column(db.Integer, nullable=False)
    similarity_score = db.Column(db.Numeric(12, 6), nullable=False)
    pattern_label = db.Column(db.Text)
    forward_return_5d = db.Column(db.Numeric(12, 6))
    forward_return_10d = db.Column(db.Numeric(12, 6))
    forward_return_20d = db.Column(db.Numeric(12, 6))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
