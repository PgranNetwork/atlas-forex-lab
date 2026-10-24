"""Deterministic synthetic provider for tests and local development only."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from atlas_forex_lab.contracts.market import MarketObservation, ObservationType, Timeframe
from atlas_forex_lab.market_data.base import MarketDataProvider
class SyntheticProvider(MarketDataProvider):
    name = "synthetic"
    def fetch_bars(self, instrument: str, timeframe: Timeframe, start: datetime, end: datetime, *, limit: int = 1000) -> list[MarketObservation]:
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")
        if end <= start or limit < 1:
            raise ValueError("end must be after start and limit must be positive")
        instrument = instrument.upper()
        step = timedelta(minutes=1 if timeframe == Timeframe.M1 else 5)
        seed = int.from_bytes(sha256(instrument.encode()).digest()[:4], "big")
        base = 2300.0 if instrument == "XAUUSD" else 1.0 + (seed % 1000) / 1000
        cursor = start.astimezone(timezone.utc).replace(second=0, microsecond=0)
        end_utc = end.astimezone(timezone.utc)
        observations = []
        index = 0
        while cursor < end_utc and len(observations) < limit:
            wave = ((seed + index * 17) % 101 - 50) / 100000
            open_price = base + wave
            close_price = open_price + (((seed + index * 29) % 21) - 10) / 100000
            high_price = max(open_price, close_price) + (0.02 if instrument == "XAUUSD" else 0.00002)
            low_price = min(open_price, close_price) - (0.02 if instrument == "XAUUSD" else 0.00002)
            observations.append(MarketObservation(provider=self.name, instrument=instrument, provider_symbol=f"SYNTH-{instrument}", timeframe=timeframe, observation_type=ObservationType.BAR, timestamp=cursor, received_at=cursor + timedelta(seconds=1), open=open_price, high=high_price, low=low_price, close=close_price, tick_volume=(seed + index) % 500, is_closed=True))
            cursor += step
            index += 1
        return observations
