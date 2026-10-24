from datetime import datetime, timezone
import pytest
from research.walk_forward import Bar, evaluate


def make_bars(closes):
    return [Bar("EURUSD", datetime(2026, 1, 1, 0, i, tzinfo=timezone.utc), close) for i, close in enumerate(closes)]


def test_walk_forward_uses_future_only_as_outcome_and_costs_reduce_returns():
    bars = make_bars([1.0, 1.1, 1.2, 1.3, 1.4, 1.5])
    free = evaluate(bars, lookback=1, horizon=1, spread_bps=0, slippage_bps=0)
    costly = evaluate(bars, lookback=1, horizon=1, spread_bps=1, slippage_bps=1)
    assert free["forecast_count"] == 1  # only the final 20% holdout is scored
    assert free["mean_net_return_bps"] > costly["mean_net_return_bps"]
    assert free["research_only"] is True
    assert free["zero_signal_baseline_total_return_bps"] == 0.0


def test_invalid_costs_rejected():
    with pytest.raises(ValueError):
        evaluate(make_bars([1, 2, 3]), spread_bps=-1)


def test_not_enough_bars_returns_empty_metrics():
    result = evaluate(make_bars([1.0, 1.1]), lookback=2, horizon=1)
    assert result["forecast_count"] == 0
    assert result["mean_net_return_bps"] is None


def test_holdout_only_evaluates_later_period_and_reports_gaps():
    bars = make_bars([1.0 + i * 0.01 for i in range(30)])
    result = evaluate(bars, lookback=2, horizon=1, test_fraction=0.2)
    assert result["holdout_fraction"] == 0.2
    assert result["forecast_count"] > 0
    assert result["holdout_start_by_instrument"]["EURUSD"] > bars[0].timestamp.isoformat()
    assert result["gap_count_over_90_seconds_by_instrument"]["EURUSD"] == 0


def test_invalid_holdout_fraction_rejected():
    with pytest.raises(ValueError):
        evaluate(make_bars([1, 2, 3, 4]), test_fraction=1.0)


def test_non_finite_costs_rejected():
    with pytest.raises(ValueError):
        evaluate(make_bars([1, 2, 3, 4]), spread_bps=float("nan"))
