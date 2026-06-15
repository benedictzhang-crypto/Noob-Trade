# NoobTrade Handoff: 王级策略 OKX Pre-Live Implementation

This file is the handoff package for the Codex thread pinned as `NoobTrade`.

## Direct Prompt For The NoobTrade Codex Window

Please implement the pre-live backend preparation for the crypto `王级策略` inside the NoobTrade repo. Do not place secrets in code, do not connect live OKX trading yet, and do not place real orders. Build the backend scaffolding needed for data ingestion, indicator reproduction, Generate scanning, paper-mode order planning, logs, database records, and ProTrade visibility.

Primary repo:

`/Users/benedict/Desktop/Noob-Trade`

Final strategy package:

`/Users/benedict/Desktop/AmpliLab Crypto 回测/crypto9/王级策略`

Read these first:

- `/Users/benedict/Desktop/AmpliLab Crypto 回测/crypto9/王级策略/README.md`
- `/Users/benedict/Desktop/AmpliLab Crypto 回测/crypto9/王级策略/01_backtest_process.md`
- `/Users/benedict/Desktop/AmpliLab Crypto 回测/crypto9/王级策略/wangji_strategy_config.json`
- `/Users/benedict/Desktop/AmpliLab Crypto 回测/crypto9/王级策略/02_okx_live_readiness_checklist.md`

Goal: create the backend foundation so ProTrade can show 王级策略 state, latest 12h candles, generated signals, intended paper orders, positions, logs, and risk status. Execution should be paper/simulation first.

## Final Strategy

- Name: 王级策略
- Strategy ID: `wangji-crypto9-12h-rank1-15pct-6pos`
- Source experiment: `crypto9 scale-native factor factory`
- Timeframe: `12h`
- Symbols: `BTC`, `ETH`
- Direction: long-only
- Entry: next 12h bar open after Generate buy signal
- Exit: TP `6.0%`, SL `0.6%`, or time expiry
- Position sizing: `15%` equity per position, cash-capped
- Max open positions: `6`
- Max new positions per 12h bar: `2`
- Initial capital used in research: `$1,000,000`
- Research costs: fee `0.0%`, slippage `0.0%`, funding `0.0%`

Final blind-test evidence:

- Final capital: `$38,851,767.99`
- Total return: `+3785.1768%`
- Max drawdown: `11.3201%`
- Return/drawdown: `334.376`
- Average exposure: `42.4158%`
- Max exposure: `91.5967%`
- Average cash: `57.5842%`
- Opened/closed trades: `4502 / 4502`
- BTC trades: `1901`
- ETH trades: `2601`

Factor weights:

- `OI`: `34.9`
- `OBV`: `3.9`
- `MACD`: `0.1`
- `MA`, `EMA`, `BOLL`, `RSI`, `VOL`, `KDJ`: `0.0`

Scoring profile:

- `profileId`: `indicator90_path10_thr88`
- `indicatorFitWeight`: `0.9`
- `pathWeight`: `0.1`
- `buyThreshold`: `88.0`
- `matchTarget`: `20`
- `lookbackPathBars`: `20`
- `horizonBars`: `10`
- `successUpPct`: `1.0`

## Data Locations

Primary crypto historical DB:

`/Users/benedict/Desktop/Crypto History Data/noobtrade_crypto_history.sqlite`

Tables:

- `crypto_assets`
- `crypto_interval_prices`
- `crypto_interval_indicators`
- `crypto_minute_prices`
- `crypto_minute_indicators`

Main table schemas:

`crypto_interval_prices`

- `asset_id`
- `interval`
- `exchange`
- `venue_symbol`
- `bar_time`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `quote_volume`
- `trade_count`
- `taker_buy_base_volume`
- `taker_buy_quote_volume`
- unique `(asset_id, interval, exchange, venue_symbol, bar_time)`

`crypto_interval_indicators`

- `asset_id`
- `interval`
- `exchange`
- `venue_symbol`
- `bar_time`
- `ma_5`, `ma_10`, `ma_20`, `ma_60`
- `ema_5`, `ema_10`, `ema_12`, `ema_20`, `ema_26`, `ema_60`
- `macd`, `macd_signal`, `macd_hist`
- `boll_mid`, `boll_upper`, `boll_lower`
- `rsi_14`
- `kdj_k`, `kdj_d`, `kdj_j`
- `vol_ma_5`, `vol_ma_20`
- `obv`
- `oi`
- unique `(asset_id, interval, exchange, venue_symbol, bar_time)`

BTC/ETH coverage in the current local DB:

| Interval | BTC rows | ETH rows | Start | End |
| --- | ---: | ---: | --- | --- |
| 5m | 922441 | 922441 | 2017-08-17 04:00 UTC | 2026-05-30 23:55 UTC |
| 15m | 307486 | 307486 | 2017-08-17 04:00 UTC | 2026-05-30 23:45 UTC |
| 30m | 153750 | 153750 | 2017-08-17 04:00 UTC | 2026-05-30 23:30 UTC |
| 1h | 76885 | 76885 | 2017-08-17 04:00 UTC | 2026-05-30 23:00 UTC |
| 2h | 38454 | 38454 | 2017-08-17 04:00 UTC | 2026-05-30 22:00 UTC |
| 4h | 19236 | 19236 | 2017-08-17 04:00 UTC | 2026-05-30 20:00 UTC |
| 6h | 12830 | 12830 | 2017-08-17 00:00 UTC | 2026-05-30 18:00 UTC |
| 12h | 6417 | 6417 | 2017-08-17 00:00 UTC | 2026-05-30 12:00 UTC |
| 1d | 3209 | 3209 | 2017-08-17 00:00 UTC | 2026-05-30 00:00 UTC |
| 5d | 642 | 642 | 2017-08-17 00:00 UTC | 2026-05-27 00:00 UTC |

Note: The current historical DB source labels are mostly Binance-derived. The live connector will use OKX, so the implementation must explicitly handle source differences before any real capital.

## Strategy And Evidence Locations

Final package:

`/Users/benedict/Desktop/AmpliLab Crypto 回测/crypto9/王级策略`

Files:

- `README.md`
- `01_backtest_process.md`
- `02_okx_live_readiness_checklist.md`
- `wangji_strategy_config.json`
- `evidence/capital_utilization_top5_report.md`
- `evidence/crypto9_top5_capital_utilization_results.csv`
- `evidence/crypto9_12h_top30_max_return_vs_benchmark.png`
- `evidence/champion_12h_5_8m_strategy.json`

Broader crypto9 results:

`/Users/benedict/Desktop/AmpliLab Crypto 回测/crypto9`

Important files:

- `12h/top30_max_return.csv`
- `1d/top30_max_return.csv`
- `charts/crypto9_12h_top30_line_details.csv`
- `charts/crypto9_12h_top30_max_return_vs_benchmark.png`
- `capital_utilization_top5/crypto9_top5_capital_utilization_results.csv`
- `strategies/crypto9_top30_strategy_registry.json`

Ampli Lab scripts that produced the strategy:

`/Users/benedict/Desktop/Ampli Lab/lab/scripts`

Key scripts:

- `run_crypto9_scale_native_factor_factory.py`
- `build_crypto9_top30_curve_charts.py`
- `export_crypto9_strategy_pack.py`
- `run_crypto9_capital_utilization_top5.py`
- `run_crypto_single_scale_sweep.py`
- `run_crypto_daily_factory.py`

## NoobTrade Backend Context

Repo:

`/Users/benedict/Desktop/Noob-Trade`

Backend:

`/Users/benedict/Desktop/Noob-Trade/backend`

Existing useful files:

- `backend/app.py`
- `backend/config.py`
- `backend/extensions.py`
- `backend/models/trading.py`
- `backend/models/crypto_history.py`
- `backend/services/crypto_market_api_service.py`
- `backend/services/crypto_market_data_service.py`
- `backend/routes/`
- `backend/render.yaml`
- root `render.yaml`

Existing OKX public-data service:

`backend/services/crypto_market_api_service.py`

It already supports OKX public spot candles through:

- `OKX_DATA_BASE_URL`
- `/api/v5/market/history-candles`
- `/api/v5/public/instruments`

Current deployment config:

- Render root service: `type: web`, name `noobtrade`
- Backend-only render config also has `type: web`, name `noobtrade-backend`
- No dedicated worker/cron exists yet.

Existing trading model:

`backend/models/trading.py`

Currently includes:

- `Watchlist`
- `WatchlistItem`
- `PaperTrade`

This is too small for OKX pre-live execution; add specific Wangji/strategy execution models or generic execution models.

## Recommended Backend Architecture

Keep ProTrade frontend as cockpit only. The backend should execute/record everything.

Recommended modules:

- `backend/strategies/wangji_strategy.py`
- `backend/services/okx_private_api_service.py`
- `backend/services/wangji_signal_service.py`
- `backend/services/wangji_indicator_service.py`
- `backend/services/wangji_execution_service.py`
- `backend/workers/wangji_strategy_runner.py`
- `backend/routes/wangji_strategy_routes.py`

Recommended DB models:

- `StrategyRuntimeState`
- `StrategySignal`
- `StrategyPaperOrder`
- `StrategyPosition`
- `StrategyExecutionLog`
- `StrategyRiskEvent`
- `ExchangeCredentialStatus` or config-only credential health endpoint

Minimum endpoints for ProTrade:

- `GET /api/wangji/status`
- `GET /api/wangji/config`
- `GET /api/wangji/latest-candles`
- `GET /api/wangji/latest-signal`
- `GET /api/wangji/signals`
- `GET /api/wangji/paper-orders`
- `GET /api/wangji/positions`
- `GET /api/wangji/logs`
- `POST /api/wangji/pause`
- `POST /api/wangji/resume`
- `POST /api/wangji/dry-run-scan`

## Render Environment Variables

Add only as Render secret/env vars, not code:

- `OKX_API_KEY`
- `OKX_API_SECRET`
- `OKX_API_PASSPHRASE`
- `OKX_TRADING_MODE=paper`
- `WANGJI_STRATEGY_ENABLED=false`
- `WANGJI_ORDER_MODE=paper`
- `WANGJI_MAX_POSITIONS=6`
- `WANGJI_POSITION_FRACTION=0.15`
- `WANGJI_MAX_NEW_POSITIONS_PER_BAR=2`
- `WANGJI_KILL_SWITCH=false`

Do not enable live trading until paper mode works and fee/slippage/funding are re-simulated.

## Implementation Plan For NoobTrade

1. Load final config from `wangji_strategy_config.json` into backend-safe config.
2. Add DB tables for signals, paper orders, positions, logs, and runtime status.
3. Build an OKX public candle adapter for 12h BTC/ETH candles.
4. Build or reuse indicator calculation for OI, OBV, MACD and any fields needed by the exact Generate reproduction.
5. Reproduce Wangji Generate scoring:
   - 20-bar path
   - 90% indicator fit
   - 10% path similarity
   - top 20 historical matches
   - threshold 88
6. Implement a `dry-run-scan` that stores signal decisions but never orders.
7. Implement paper order planner:
   - 15% equity
   - max 6 positions
   - max 2 new positions per 12h bar
   - TP 6.0%
   - SL 0.6%
8. Add position reconciliation in paper mode.
9. Add ProTrade API endpoints.
10. Add Render worker/cron plan. For now, one safe path is a manual/dry-run endpoint; later add a scheduled job after UI visibility exists.

## Safety Requirements

- No real OKX order placement in first implementation.
- API keys must never be logged.
- Do not put API keys in GitHub.
- Keep `WANGJI_STRATEGY_ENABLED=false` by default.
- Keep `OKX_TRADING_MODE=paper` by default.
- Add a kill switch before any private API order method.
- First live-like run must be paper/demo.
- Re-run backtest with realistic OKX fees/slippage/funding before live.

## Important Caveat

王级策略 was researched on the local historical crypto DB. The current live plan is OKX. Before real capital, NoobTrade must check whether the live OKX candle/OI/volume definitions match the research DB closely enough. If OKX cannot provide equivalent OI for the chosen instrument mode, the strategy should stay in paper/research mode until an equivalent OI source is defined.

