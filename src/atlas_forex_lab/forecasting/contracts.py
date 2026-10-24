"""Forecast output contracts with explicit research-only semantics."""
from datetime import datetime, timezone
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from atlas_forex_lab.contracts.market import Timeframe
class Direction(StrEnum):
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"
class ForecastSignal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: str = "1.0"
    instrument: str
    source_provider: str
    timeframe: Timeframe
    horizon_bars: int = Field(ge=1, le=5)
    generated_at: datetime
    last_bar_at: datetime
    reference_price: float = Field(gt=0)
    direction: Direction
    score: float = Field(ge=-1, le=1)
    model_id: str
    model_kind: str = "heuristic_baseline"
    is_calibrated_probability: bool = False
    research_only: bool = True
    rationale: list[str] = Field(default_factory=list)
    @field_validator("generated_at", "last_bar_at")
    @classmethod
    def timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("forecast timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)
