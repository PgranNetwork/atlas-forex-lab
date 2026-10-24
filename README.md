# Atlas Forex Lab

Open-source, research-only Telegram assistant for forex and gold market analysis. The project is designed to test short-horizon forecasts; it does not place trades or promise profitable signals.

## Current status

- Market-data contracts and deterministic synthetic data provider.
- Optional MetaTrader 5 historical-bar adapter (requires supported Windows environment and MT5 terminal).
- Baseline momentum forecast for 1–5 one-minute bars ahead.
- Telegram command layer (requires a bot token configured locally).
- Affiliate tracking interfaces and a generic signed-webhook prototype.
- Unit tests for contracts, forecast logic, referral state transitions and webhook signatures.

**Important:** synthetic-data demos are not evidence of forecasting skill. The baseline is a heuristic, not a trained AI model. No broker conversion adapter is live. Do not use this software as financial advice or for unattended live trading.

## Quick start

Python 3.11 or newer:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q
atlas --source synthetic --instrument EURUSD --timeframe M1 --bars 30
atlas forecast-demo --instrument EURUSD --bars 30 --horizon 3
```

Copy `.env.example` to `.env` for local configuration. Never commit real tokens, API keys, broker credentials, or account identifiers.

## Engineering principles

1. Validate any apparent edge using chronological walk-forward evaluation.
2. Account for spread, commission, slippage, latency and missing/stale data.
3. Keep broker integrations modular and only claim referral verification from authoritative broker evidence.
4. Never request broker passwords, OTPs or API secrets from end users.
5. Keep live order placement out of scope.

## License

MIT. See [LICENSE](LICENSE).