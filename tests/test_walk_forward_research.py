from datetime import datetime, timedelta, timezone
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


def test_windows_crossing_missing_minutes_are_excluded():
    bars = make_bars([1.0 + i * 0.01 for i in range(12)])
    bars = [
        Bar(bar.instrument, bar.timestamp + (timedelta(minutes=10) if i >= 8 else timedelta()), bar.close)
        for i, bar in enumerate(bars)
    ]
    result = evaluate(bars, lookback=2, horizon=1, test_fraction=0.5)
    assert result["gap_count_over_90_seconds_by_instrument"]["EURUSD"] == 1
    assert result["skipped_gap_windows_by_instrument"]["EURUSD"] > 0


def test_invalid_holdout_fraction_rejected():
    with pytest.raises(ValueError):
        evaluate(make_bars([1, 2, 3, 4]), test_fraction=1.0)


def test_non_finite_costs_rejected():
    with pytest.raises(ValueError):
        evaluate(make_bars([1, 2, 3, 4]), spread_bps=float("nan"))


def test_small_sample_is_explicitly_marked_exploratory():
    result = evaluate(make_bars([1.0 + i * 0.001 for i in range(50)]), lookback=2, horizon=1)
    assert result["sample_status"] == "exploratory_insufficient_sample"
    assert result["bars_by_instrument"]["EURUSD"] == 50
    assert result["minimum_forecast_count_gate"] == 1000
    assert result["minimum_active_signal_count_gate"] == 200
    assert result["minimum_history_span_days_per_instrument_gate"] == 20
    assert result["history_gate_met"] is False


def test_duplicate_instrument_timestamp_is_rejected():
    timestamp = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    bars = [
        Bar("EURUSD", timestamp, 1.1),
        Bar("EURUSD", timestamp, 1.2),
    ]
    from research.walk_forward import load_bars
    from pathlib import Path
    import csv

    # Exercise the public CSV loader so duplicate rows cannot be hidden in preprocessing.
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "duplicates.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["instrument", "open_time", "close_price"])
            writer.writeheader()
            for bar in bars:
                writer.writerow({
                    "instrument": bar.instrument,
                    "open_time": bar.timestamp.isoformat(),
                    "close_price": bar.close,
                })
        with pytest.raises(ValueError, match="Duplicate timestamp"):
            load_bars(path)
