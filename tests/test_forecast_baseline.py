from datetime import datetime, timedelta, timezone
import pytest
from atlas_forex_lab.contracts.market import MarketObservation, ObservationType, Timeframe
from atlas_forex_lab.forecasting.contracts import Direction
from atlas_forex_lab.forecasting.momentum import ForecastInputError, MomentumBaseline

def bars(count=30):
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    result = []
    for i in range(count):
        price = 1.1 + i * 0.0001
        ts = now - timedelta(minutes=count-i)
        result.append(MarketObservation(provider="test", instrument="EURUSD", provider_symbol="EURUSD", timeframe=Timeframe.M1, observation_type=ObservationType.BAR, timestamp=ts, received_at=ts+timedelta(seconds=1), open=price, high=price+0.0002, low=price-0.0001, close=price+0.0001, is_closed=True))
    return result

def test_forecast_is_research_only_and_score_is_not_probability():
    signal = MomentumBaseline().predict(bars(), horizon_bars=3)
    assert signal.research_only is True
    assert signal.is_calibrated_probability is False
    assert signal.horizon_bars == 3
    assert signal.direction in (Direction.UP, Direction.DOWN, Direction.NEUTRAL)

def test_requires_minimum_history():
    with pytest.raises(ForecastInputError):
        MomentumBaseline().predict(bars(10))
