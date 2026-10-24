from datetime import datetime, timezone

import pytest

from atlas_forex_lab.contracts.market import MarketObservation, ObservationType, Timeframe
from atlas_forex_lab.market_data.base import MarketDataError
from atlas_forex_lab.market_data.supabase_store import SupabaseMarketStore


def test_store_requires_server_side_credentials(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(MarketDataError, match="SUPABASE_URL"):
        SupabaseMarketStore()


def test_store_rejects_http_url():
    with pytest.raises(MarketDataError, match="HTTPS"):
        SupabaseMarketStore("http://example.supabase.co", "test-key")


def test_save_bars_rejects_quotes():
    store = SupabaseMarketStore("https://example.supabase.co", "test-key")
    quote = MarketObservation(
        provider="test", instrument="EURUSD", provider_symbol="EUR/USD",
        observation_type=ObservationType.QUOTE, timestamp=datetime.now(timezone.utc),
        received_at=datetime.now(timezone.utc), bid=1.1, ask=1.2
    )
    with pytest.raises(MarketDataError, match="OHLC"):
        store.save_bars([quote])
