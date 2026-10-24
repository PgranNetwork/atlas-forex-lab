from datetime import datetime, timedelta, timezone

import pytest

from atlas_forex_lab.contracts.market import Timeframe
from atlas_forex_lab.market_data.base import MarketDataError
from atlas_forex_lab.market_data.twelvedata import TwelveDataProvider


def test_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("TWELVEDATA_API_KEY", raising=False)
    with pytest.raises(MarketDataError, match="TWELVEDATA_API_KEY"):
        TwelveDataProvider()


@pytest.mark.parametrize(("instrument", "expected"), [
    ("EURUSD", "EUR/USD"),
    ("XAUUSD", "XAU/USD"),
    ("GBP/USD", "GBP/USD"),
])
def test_symbol_mapping(instrument, expected):
    assert TwelveDataProvider._symbol(instrument) == expected


def test_rejects_unknown_symbol():
    with pytest.raises(MarketDataError, match="Unsupported instrument"):
        TwelveDataProvider._symbol("XYZABC")


def test_rejects_naive_datetimes():
    provider = TwelveDataProvider(api_key="test-key")
    with pytest.raises(ValueError, match="timezone-aware"):
        provider.fetch_bars(
            "EURUSD", Timeframe.M1, datetime(2026, 1, 1),
            datetime(2026, 1, 1, 0, 1), limit=1
        )


def test_rejects_invalid_limit():
    provider = TwelveDataProvider(api_key="test-key")
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="limit"):
        provider.fetch_bars("EURUSD", Timeframe.M1, now, now + timedelta(minutes=1), limit=5001)
