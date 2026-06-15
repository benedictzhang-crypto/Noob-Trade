# Message For NoobTrade Codex

Please take over the NoobTrade backend implementation for 王级策略 OKX pre-live preparation.

Read this handoff first:

`/Users/benedict/Desktop/Noob-Trade/backend/docs/wangji_okx_handoff.md`

Also read the final strategy package:

`/Users/benedict/Desktop/AmpliLab Crypto 回测/crypto9/王级策略`

Main config:

`/Users/benedict/Desktop/AmpliLab Crypto 回测/crypto9/王级策略/wangji_strategy_config.json`

Primary repo:

`/Users/benedict/Desktop/Noob-Trade`

Do not place real OKX orders yet. Build the backend pre-live foundation:

1. Load 王级策略 config.
2. Add DB records for runtime status, signals, paper orders, positions, logs, risk events.
3. Build OKX public/private service skeletons without storing secrets in code.
4. Reproduce the 12h Generate scan for BTC/ETH.
5. Implement dry-run and paper-order planning.
6. Expose ProTrade API endpoints for status, signals, orders, positions, logs, pause/resume.
7. Keep `WANGJI_STRATEGY_ENABLED=false` and `OKX_TRADING_MODE=paper` by default.

Key strategy:

- Timeframe: 12h
- Symbols: BTC, ETH
- Long-only
- Factor weights: OI 34.9, OBV 3.9, MACD 0.1
- Scoring: indicator90_path10_thr88
- TP/SL: 6.0% / 0.6%
- Position sizing: 15% equity, max 6 positions, max 2 new positions per 12h bar
- Research result: final $38,851,767.99, return +3785.1768%, DD 11.3201%

