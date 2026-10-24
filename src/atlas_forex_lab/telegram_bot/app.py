"""Minimal EQ Options Telegram interface. No trading or unverified referral claims."""
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from atlas_forex_lab.telegram_bot.config import BotConfig

DISCLAIMER = ("EQ Options is a research tool, not financial advice. Forecasts are experimental, "
              "may be wrong, and are not calibrated probabilities. No live trading is available.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Welcome to EQ Options.\n\n" + DISCLAIMER + "\n\nCommands: /help /brokers /referral_status")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "/start — introduction\n/brokers — configured affiliate links\n/referral_status — explain verification status\n\n" + DISCLAIMER)

async def brokers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return
    config: BotConfig = context.application.bot_data["config"]
    if not config.broker_links:
        await update.effective_message.reply_text("No broker affiliate links are configured yet.")
        return
    lines = ["Broker links (EQ Options may earn commission from qualifying referrals):"]
    lines.extend(f"{label}: {url}" for label, url in config.broker_links)
    await update.effective_message.reply_text("\n".join(lines))

async def referral_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Referral verification is not connected to a live broker reporting API yet. "
            "A click or submitted account ID alone does not prove registration or qualification. "
            "No referral will be marked verified without authoritative broker evidence.")

def main() -> None:
    config = BotConfig.from_env()
    if not config.token:
        raise SystemExit("Set ATLAS_TELEGRAM_BOT_TOKEN in your environment before starting the bot.")
    app = Application.builder().token(config.token).build()
    app.bot_data["config"] = config
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("brokers", brokers))
    app.add_handler(CommandHandler("referral_status", referral_status))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
