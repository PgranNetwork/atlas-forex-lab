from datetime import datetime, timezone
import pytest
from research.walk_forward import Bar, evaluate


def make_bars(closes):
    return [Bar("EURUSD", datetime(2026, 1, 1, 0, i, tzinfo=timezone.utc), close) for i, close in enumerate(closes)]


def test_walk_forward_uses_future_only_as_outcome_and_costs_reduce_returns():
    bars = make_bars([1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
    free = evaluate(bars, lookback=1, horizon=1, spread_bps=0, slippage_bps=0)
    costly = evaluate(bars, lookback=1, horizon=1, spread_bps=1, slippage_bps=1)
    assert free["forecast_count"] == 4
    assert free["mean_net_return_bps"] > costly["mean_net_return_bps"]
    assert free["research_only"] is True


def test_invalid_costs_rejected():
    with pytest.raises(ValueError):
        evaluate(make_bars([1, 2, 3]), spread_bps=-1)


def test_not_enough_bars_returns_empty_metrics():
    result = evaluate(make_bars([1.0, 1.1]), lookback=2, horizon=1)
    assert result["forecast_count"] == 0
    assert result["mean_net_return_bps"] is None
