"""Server-side persistence for validated market data in Supabase REST."""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from atlas_forex_lab.contracts.market import MarketObservation, ObservationType
from atlas_forex_lab.market_data.base import MarketDataError


class SupabaseMarketStore:
    """Persist normalized candles using a server-side key; never use an anon key."""

    def __init__(
        self,
        project_url: str | None = None,
        service_role_key: str | None = None,
        timeout_seconds: float = 12.0,
    ) -> None:
        self.project_url = (project_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.service_role_key = (service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
        self.timeout_seconds = timeout_seconds
        if not self.project_url or not self.service_role_key:
            raise MarketDataError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured server-side")
        if not self.project_url.startswith("https://"):
            raise MarketDataError("SUPABASE_URL must use HTTPS")

    def _post(self, table: str, rows: list[dict[str, object]], *, conflict: str | None = None) -> None:
        if not rows:
            return
        query = f"?{urlencode({'on_conflict': conflict})}" if conflict else ""
        url = f"{self.project_url}/rest/v1/{table}{query}"
        request = Request(
            url,
            data=json.dumps(rows, separators=(",", ":")).encode("utf-8"),
            method="POST",
            headers={
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=ignore-duplicates,return=minimal",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status not in (200, 201, 204):
                    raise MarketDataError(f"Supabase {table} insert returned HTTP {response.status}")
        except HTTPError as exc:
            # Never echo response bodies: database errors can include sensitive context.
            raise MarketDataError(f"Supabase {table} insert failed with HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise MarketDataError(f"Supabase {table} request failed: {type(exc).__name__}") from exc

    def save_bars(self, observations: list[MarketObservation]) -> int:
        rows: list[dict[str, object]] = []
        for item in observations:
            if item.observation_type != ObservationType.BAR or item.timeframe is None:
                raise MarketDataError("Only normalized OHLC bar observations can be persisted")
            assert item.open is not None and item.high is not None and item.low is not None and item.close is not None
            rows.append({
                "instrument": item.instrument,
                "timeframe": item.timeframe.value,
                "open_time": item.timestamp.isoformat(),
                "open_price": item.open,
                "high_price": item.high,
                "low_price": item.low,
                "close_price": item.close,
                "volume": item.tick_volume,
                "source": item.provider,
                "received_at": item.received_at.isoformat(),
            })
        self._post("market_bars", rows, conflict="instrument,timeframe,open_time,source")
        return len(rows)

    def save_health(
        self,
        *,
        source: str,
        instrument: str,
        healthy: bool,
        latency_ms: int | None,
        details: dict[str, object] | None = None,
    ) -> None:
        if latency_ms is not None and latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")
        self._post("data_source_health", [{
            "source": source,
            "instrument": instrument,
            "healthy": healthy,
            "latency_ms": latency_ms,
            "details": details or {},
        }])
