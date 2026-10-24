from atlas_forex_lab.telegram_bot.config import BotConfig

def test_empty_config_has_no_token_or_broker_links(monkeypatch):
    monkeypatch.delenv("ATLAS_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ATLAS_BROKER_LINKS", raising=False)
    config = BotConfig.from_env()
    assert config.token == ""
    assert config.broker_links == ()

def test_parses_https_broker_links(monkeypatch):
    monkeypatch.setenv("ATLAS_BROKER_LINKS", "demo|Example Broker|https://example.com/ref")
    config = BotConfig.from_env()
    assert config.broker_links == (("Example Broker", "https://example.com/ref"),)
