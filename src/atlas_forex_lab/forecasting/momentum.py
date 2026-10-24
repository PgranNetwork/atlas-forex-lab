"""Transparent technical baseline; not an AI model or validated trading signal."""
from __future__ import annotations
from datetime import datetime, timezone
from math import isfinite
from atlas_forex_lab.contracts.market import MarketObservation, ObservationType, Timeframe
from atlas_forex_lab.forecasting.contracts import Direction, ForecastSignal
class ForecastInputError(ValueError):
    """Raised when bar series is unsuitable for a baseline forecast."""
class MomentumBaseline:
    """Deterministic heuristic; its score is not a probability or claim of profitability."""
    model_id = "momentum-baseline-v0"
    def __init__(self, *, minimum_bars: int = 20, neutral_threshold: float = 0.08) -> None:
        if minimum_bars < 5:
            raise ValueError("minimum_bars must be at least 5")
        if not 0 <= neutral_threshold < 1:
            raise ValueError("neutral_threshold must be in [0, 1)")
        self.minimum_bars = minimum_bars
        self.neutral_threshold = neutral_threshold
    def predict(self, bars: list[MarketObservation], *, horizon_bars: int = 1, generated_at: datetime | None = None) -> ForecastSignal:
        if not 1 <= horizon_bars <= 5:
            raise ForecastInputError("horizon_bars must be between 1 and 5")
        if len(bars) < self.minimum_bars:
            raise ForecastInputError(f"need at least {self.minimum_bars} bars; received {len(bars)}")
        ordered = sorted(bars, key=lambda bar: bar.timestamp)
        latest = ordered[-1]
        if any(bar.observation_type != ObservationType.BAR for bar in ordered):
            raise ForecastInputError("all observations must be OHLC bars")
        if any(bar.timeframe != Timeframe.M1 for bar in ordered):
            raise ForecastInputError("this baseline currently requires M1 bars")
        if any(not bar.is_closed for bar in ordered):
            raise ForecastInputError("open/in-progress bars are not accepted")
        if len({bar.timestamp for bar in ordered}) != len(ordered):
            raise ForecastInputError("duplicate bar timestamps are not accepted")
        if len({bar.instrument for bar in ordered}) != 1 or len({bar.provider for bar in ordered}) != 1:
            raise ForecastInputError("all bars must use one instrument and provider")
        if any(bar.close is None or not isfinite(bar.close) or bar.close <= 0 for bar in ordered):
            raise ForecastInputError("all bars must have valid close prices")
        closes = [float(bar.close) for bar in ordered[-20:]]
        price = closes[-1]
        short_return = price / closes[-4] - 1.0
        medium_return = price / closes[-11] - 1.0
        long_return = price / closes[0] - 1.0
        mean = sum(closes) / len(closes)
        scale = sum(abs(closes[i] / closes[i - 1] - 1.0) for i in range(1, len(closes))) / (len(closes) - 1)
        if scale <= 1e-12:
            score = 0.0
        else:
            location_return = (price / mean - 1.0) / 10.0
            raw = (0.45 * short_return / 3 + 0.35 * medium_return / 10 + 0.10 * long_return / 19 + 0.10 * location_return) / scale
            score = max(-1.0, min(1.0, raw))
        direction = Direction.NEUTRAL if abs(score) < self.neutral_threshold else (Direction.UP if score > 0 else Direction.DOWN)
        return ForecastSignal(instrument=latest.instrument, source_provider=latest.provider, timeframe=Timeframe.M1,
            horizon_bars=horizon_bars, generated_at=generated_at or datetime.now(timezone.utc), last_bar_at=latest.timestamp,
            reference_price=price, direction=direction, score=score, model_id=self.model_id,
            rationale=[f"3-bar return: {short_return * 100:.4f}%", f"10-bar return: {medium_return * 100:.4f}%",
                       f"19-bar return: {long_return * 100:.4f}%", "Score is heuristic strength, not a calibrated probability."])
