"""Twelve Data REST adapter for normalized FX and gold candles.

Requires a provider API key in TWELVEDATA_API_KEY. Never use demo/synthetic
bars as a substitute for a missing live feed.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from atlas_forex_lab.contracts.market import MarketObservation, ObservationType, Timeframe
from atlas_forex_lab.market_data.base import MarketDataError, MarketDataProvider


class TwelveDataProvider(MarketDataProvider):
    """Fetch historical candles from Twelve Data using its time-series endpoint."""

    name = "twelvedata"
    endpoint = "https://api.twelvedata.com/time_series"

    def __init__(self, api_key: str | None = None, timeout_seconds: float = 12.0) -> None:
        self.api_key = (api_key or os.getenv("TWELVEDATA_API_KEY", "")).strip()
        self.timeout_seconds = timeout_seconds
        if not self.api_key:
            raise MarketDataError("TWELVEDATA_API_KEY is not configured")

    @staticmethod
    def _symbol(instrument: str) -> str:
        symbol = instrument.strip().upper().replace("_", "/").replace("-", "/")
        if symbol == "XAUUSD":
            return "XAU/USD"
        supported = {"XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "NZD/USD"}
        if len(symbol) == 6 and symbol.isalpha() and "/" not in symbol:
            symbol = f"{symbol[:3]}/{symbol[3:]}"
        if symbol not in supported:
            raise MarketDataError(f"Unsupported instrument mapping: {instrument}")
        return symbol

    def fetch_bars(
        self,
        instrument: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
        *,
        limit: int = 1000,
    ) -> list[MarketObservation]:
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")
        if end <= start or limit < 1 or limit > 5000:
            raise ValueError("end must follow start and limit must be between 1 and 5000")
        interval = {Timeframe.M1: "1min", Timeframe.M5: "5min"}[timeframe]
        params = urlencode({
            "symbol": self._symbol(instrument),
            "interval": interval,
            "start_date": start.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "end_date": end.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "outputsize": limit,
            "order": "ASC",
            "timezone": "UTC",
            "apikey": self.api_key,
        })
        request = Request(
            f"{self.endpoint}?{params}",
            headers={"Accept": "application/json", "User-Agent": "EQ-Options-Research/0.1"},
        )
        started = monotonic()
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise MarketDataError(f"Twelve Data HTTP error {exc.code}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise MarketDataError(f"Twelve Data request failed: {type(exc).__name__}") from exc
        if not isinstance(payload, dict):
            raise MarketDataError("Twelve Data returned an unexpected response")
        if payload.get("status") == "error" or "code" in payload and "values" not in payload:
            message = str(payload.get("message", "provider returned an error"))[:180]
            raise MarketDataError(f"Twelve Data error: {message}")
        values = payload.get("values")
        if not isinstance(values, list):
            raise MarketDataError("Twelve Data response did not include candle values")
        received_at = datetime.now(timezone.utc)
        symbol = self._symbol(instrument)
        records: list[MarketObservation] = []
        for row in values:
            try:
                timestamp = datetime.strptime(str(row["datetime"]), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                if not (start.astimezone(timezone.utc) <= timestamp < end.astimezone(timezone.utc)):
                    continue
                open_price = float(row["open"])
                high_price = float(row["high"])
                low_price = float(row["low"])
                close_price = float(row["close"])
                raw_volume = row.get("volume")
                volume = int(float(raw_volume)) if raw_volume not in (None, "", "null") else None
                records.append(MarketObservation(
                    provider=self.name,
                    instrument=instrument.strip().upper().replace("/", "").replace("-", "").replace("_", ""),
                    provider_symbol=symbol,
                    timeframe=timeframe,
                    observation_type=ObservationType.BAR,
                    timestamp=timestamp,
                    received_at=received_at,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    tick_volume=max(volume, 0) if volume is not None else None,
                    is_closed=True,
                ))
            except (KeyError, TypeError, ValueError) as exc:
                raise MarketDataError("Twelve Data returned a malformed candle") from exc
        records.sort(key=lambda item: item.timestamp)
        unique: dict[datetime, MarketObservation] = {}
        for item in records:
            unique[item.timestamp] = item
        if not unique:
            raise MarketDataError("Twelve Data returned no candles in the requested time range")
        # Expose request latency for callers that also record source health.
        self.last_latency_ms = int((monotonic() - started) * 1000)
        return list(unique.values())
