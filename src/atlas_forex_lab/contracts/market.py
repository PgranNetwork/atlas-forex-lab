"""Canonical market-data contracts. Timestamps must be timezone-aware UTC."""
from datetime import datetime, timezone
from enum import StrEnum
from math import isfinite
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
class Timeframe(StrEnum):
    M1 = "M1"
    M5 = "M5"
class ObservationType(StrEnum):
    BAR = "bar"
    QUOTE = "quote"
class DataHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    DISCONNECTED = "disconnected"
class MarketObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1.0"] = "1.0"
    provider: str = Field(min_length=1, max_length=80)
    instrument: str = Field(pattern=r"^[A-Z0-9._-]{3,20}$")
    provider_symbol: str = Field(min_length=1, max_length=80)
    timeframe: Timeframe | None = None
    observation_type: ObservationType
    timestamp: datetime
    received_at: datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    tick_volume: int | None = Field(default=None, ge=0)
    bid: float | None = None
    ask: float | None = None
    spread_points: float | None = Field(default=None, ge=0)
    is_closed: bool | None = None
    @field_validator("timestamp", "received_at")
    @classmethod
    def require_timezone_and_normalize_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)
    @field_validator("open", "high", "low", "close", "bid", "ask")
    @classmethod
    def require_finite_positive_prices(cls, value: float | None) -> float | None:
        if value is not None and (not isfinite(value) or value <= 0):
            raise ValueError("prices must be finite and greater than zero")
        return value
    @model_validator(mode="after")
    def validate_shape(self) -> "MarketObservation":
        if self.observation_type == ObservationType.BAR:
            if self.timeframe is None:
                raise ValueError("bar observations require a timeframe")
            if any(p is None for p in (self.open, self.high, self.low, self.close)):
                raise ValueError("bar observations require OHLC prices")
            assert self.open is not None and self.high is not None and self.low is not None and self.close is not None
            if self.high < max(self.open, self.close, self.low):
                raise ValueError("high must be >= open, close and low")
            if self.low > min(self.open, self.close, self.high):
                raise ValueError("low must be <= open, close and high")
            if self.is_closed is None:
                raise ValueError("bar observations must declare is_closed")
        elif self.observation_type == ObservationType.QUOTE:
            if self.bid is None or self.ask is None:
                raise ValueError("quote observations require bid and ask")
            if self.ask < self.bid:
                raise ValueError("ask must be >= bid")
        return self
class DataHealth(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: str
    status: DataHealthStatus
    checked_at: datetime
    last_observation_at: datetime | None = None
    lag_seconds: float | None = Field(default=None, ge=0)
    reason_codes: list[str] = Field(default_factory=list)
    @field_validator("checked_at", "last_observation_at")
    @classmethod
    def require_timezone_and_normalize_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)
