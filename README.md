# EQ Options

Open-source, research-only Telegram assistant for forex and gold market analysis. The public-facing product is **EQ Options** (@Eqoptions_bot); the source repository remains named `atlas-forex-lab`. It is intended for short-horizon research and does not place trades or promise profitable signals.

## Current implementation

- Typed market-data contract with validation for timestamps, OHLC bars and quotes.
- Twelve Data REST adapter for forex and XAU/USD candles with strict response validation.
- Server-side Supabase REST writer for market bars and data-source health telemetry.
- Deployed Cloudflare Worker scheduled ingestion every five minutes for EUR/USD, GBP/USD, USD/JPY and XAU/USD; each poll requests the latest ten M1 candles and ignores duplicate inserts.
- Telegram Markets menu reads stored M1 snapshots and labels candle age; a public ingestion-status endpoint reports secret presence, candle coverage and data-source health.
- `atlas ingest-live` command that fetches real provider data and persists it only after validation.
- Deterministic synthetic data provider for demos and tests.
- Transparent momentum heuristic for 1–5 one-minute bars ahead.
- Optional Telegram command layer with /start, /help, /brokers and /referral_status.
- Environment-based configuration; broker links must be explicitly configured.
- GitHub Actions test workflow.

Not yet implemented: broker-specific affiliate conversion adapter, persistent production referral service, trained AI model, and forecast-to-Telegram integration. A basic research-only walk-forward evaluator is available in `research/walk_forward.py`; it is not a trained model and should not be treated as evidence of predictive edge. The production Worker currently ingests M1 candles on a five-minute schedule; monitor provider quotas, freshness, and missing-minute gaps before relying on this history for evaluation. The provider adapter requires a valid Twelve Data API key; the database writer requires server-side Supabase credentials.

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

### Live market ingestion

Configure `TWELVEDATA_API_KEY`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` in the trusted server environment only. Use the Supabase service-role key only in a private backend; never expose it in Telegram, a browser, a public repository, or a client app. Then run:

    atlas ingest-live --instrument EURUSD --timeframe M1 --bars 100
    atlas ingest-live --instrument XAUUSD --timeframe M1 --bars 100

The command fails closed if credentials are missing, the provider errors, or candles fail validation. Provider availability, subscription limits, instrument coverage, and timestamps must be checked against the provider account before scheduling ingestion. This command is an ingestion primitive, not a continuous production scheduler.

## Engineering principles

1. Validate any apparent edge using chronological walk-forward evaluation.
2. Account for spread, commission, slippage, latency and missing/stale data.
3. Only claim referral verification from authoritative broker evidence.
4. Never request broker passwords, OTPs or API secrets from end users.
5. Keep live order placement out of scope.

## License

MIT. See LICENSE.


### Walk-forward baseline evaluation

For a reproducible export of stored M1 candles, set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in your trusted local environment, then run:

```bash
python -m research.export_supabase_bars candles.csv
python -m research.walk_forward candles.csv --lookback 3 --horizon 1 --spread-bps 1 --commission-bps 0 --slippage-bps 1 --out report.json
```

The exporter reads credentials only from environment variables, uses a fixed receive-time cutoff for a consistent pagination boundary, exports full OHLC candles, and rejects non-finite, non-positive or inconsistent price rows. It never prints secret values. Keep the exported CSV private if your data licence requires it.

The exporter writes `instrument,open_time,open_price,high_price,low_price,close_price`; the evaluator requires `instrument,open_time,close_price` and safely ignores the additional OHLC columns:

```bash
python -m research.walk_forward candles.csv --lookback 3 --horizon 1 --spread-bps 1 --commission-bps 0 --slippage-bps 1 --out report.json
```

This evaluates a transparent rolling-momentum baseline in chronological order. Signals at each origin use only information available at that origin; the later close is used only as the outcome. The evaluator rejects duplicate timestamps and requires each instrument's bars to be strictly chronological. Its sample status stays exploratory until aggregate holdout counts, per-instrument coverage (at least 100 forecasts and 20 active signals per instrument), and at least 20 days of history per instrument meet the minimum gates. Meeting these gates is not proof of statistical validity. Cost assumptions are simplified basis-point estimates and must be replaced with instrument- and broker-specific estimates before drawing conclusions. Do not interpret this report as a live signal or evidence of future profitability. The baseline must be compared against a no-signal/naive benchmark and tested on a genuinely held-out period before any forecasts are exposed to users.
