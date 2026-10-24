# EQ Options

Open-source, research-only Telegram assistant for forex and gold market analysis. The public-facing product is **EQ Options** (@Eqoptions_bot); the source repository remains named `atlas-forex-lab`. It is intended for short-horizon research and does not place trades or promise profitable signals.

## Current implementation

- Typed market-data contract with validation for timestamps, OHLC bars and quotes.
- Deterministic synthetic data provider for demos and tests.
- Transparent momentum heuristic for 1–5 one-minute bars ahead.
- Optional Telegram command layer with /start, /help, /brokers and /referral_status.
- Environment-based configuration; broker links must be explicitly configured.
- GitHub Actions test workflow.

Not yet implemented in this repository: live market-data feed, broker-specific affiliate conversion adapter, persistent production referral service, trained AI model, walk-forward backtester, Supabase integration, Cloudflare deployment and live bot configuration.

IMPORTANT: synthetic-data demos are not evidence of forecasting skill. The baseline is a heuristic, not a trained AI model. Referral status remains unverified until authoritative broker reporting is integrated. Do not use this software as financial advice or for unattended live trading.

## Quick start

Use Python 3.11 or newer:

    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    pytest -q
    atlas check-data --source synthetic --instrument EURUSD --timeframe M1 --bars 30
    atlas forecast-demo --instrument EURUSD --bars 30 --horizon 3

To enable Telegram commands, install the optional dependency and configure the token in your local environment:

    pip install -e ".[telegram]"
    export ATLAS_TELEGRAM_BOT_TOKEN="your-token"
    atlas-telegram

On Windows PowerShell, set the variable with $env:ATLAS_TELEGRAM_BOT_TOKEN="your-token" instead of export.

Copy .env.example for reference, but do not commit actual tokens, API keys, broker credentials, or account identifiers.

## Engineering principles

1. Validate any apparent edge using chronological walk-forward evaluation.
2. Account for spread, commission, slippage, latency and missing/stale data.
3. Only claim referral verification from authoritative broker evidence.
4. Never request broker passwords, OTPs or API secrets from end users.
5. Keep live order placement out of scope.

## License

MIT. See LICENSE.
