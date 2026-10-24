# Architecture and current boundaries

Atlas Forex Lab is research-only. It must not place trades or imply that a forecast is guaranteed to win.

## Components
- contracts/market.py: typed market-data contracts and validation.
- market_data/synthetic.py: deterministic fixtures for tests and demos.
- market_data/mt5.py: optional historical-bar adapter for supported Windows/MetaTrader 5 setups.
- forecasting/momentum.py: transparent heuristic baseline, not a trained AI model.
- telegram_bot/: optional Telegram command layer.
- affiliates/: provider-neutral referral states and signed-webhook prototype; no live broker adapter is configured.

## Engineering gates
1. Store real licensed market data with source and timestamps.
2. Run chronological walk-forward tests with spread, commissions, slippage and latency.
3. Report calibration and uncertainty; do not present heuristic scores as probabilities.
4. Integrate broker conversion events only with official documentation and verified signatures.
5. Keep secrets in environment/deployment secret stores, never in source control.
