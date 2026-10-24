# EQ Options Telegram webhook

This Cloudflare Worker is the public Telegram webhook edge. It does not execute trades and does not fabricate live forecasts. The Python research package remains the separate forecasting component.

## Required Worker secrets

Set these in Cloudflare Dashboard → Workers & Pages → `eq-options-telegram` → Settings → Variables and Secrets:

- `TELEGRAM_BOT_TOKEN`: token from @BotFather. Never commit or share it.
- `TELEGRAM_WEBHOOK_SECRET`: random 1–256 character string using only A–Z, a–z, 0–9, underscore, and hyphen. Telegram requires 1–256 characters in this allowed set for its webhook secret header.

## Configure Telegram webhook

After deploying and adding both secrets, call Telegram's `setWebhook` method from a trusted environment with:
- `url`: `https://eq-options-telegram.<your-workers-subdomain>.workers.dev/telegram`
- `secret_token`: exactly the value configured as `TELEGRAM_WEBHOOK_SECRET`
- `allowed_updates`: `["message"]`

Do not put the bot token in GitHub, browser URLs, issue reports, or public messages. Avoid sharing the setWebhook URL that contains the token. Use a trusted terminal or secret manager to call Telegram's Bot API.

Health endpoint: `GET /health`. It reports only whether required secrets are configured, never their values.

## Commands

- `/start`, `/help`, `/forecast`, `/brokers`, `/referral_status`

The forecast command explicitly states when live data/validated forecasts are unavailable. Broker links and referral verification remain disabled until verified integrations exist.
