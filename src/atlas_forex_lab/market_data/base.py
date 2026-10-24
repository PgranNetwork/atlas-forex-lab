"""Provider adapter contract."""
from abc import ABC, abstractmethod
from datetime import datetime
from atlas_forex_lab.contracts.market import MarketObservation, Timeframe
class MarketDataError(RuntimeError):
    """Raised when a provider cannot supply valid market data."""
class MarketDataProvider(ABC):
    name: str
    @abstractmethod
    def fetch_bars(self, instrument: str, timeframe: Timeframe, start: datetime, end: datetime, *, limit: int = 1000) -> list[MarketObservation]:
        """Return normalized bars within [start, end), newest records last."""
