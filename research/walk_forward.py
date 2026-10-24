#!/usr/bin/env python3
"""Leakage-safe walk-forward evaluation for EQ Options research candles.

Input CSV columns: instrument,open_time,open_price,high_price,low_price,close_price.
Signals use only closes available before the forecast origin. PnL is a research
proxy, not executable trading performance; costs are charged on every round trip.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class Bar:
    instrument: str
    timestamp: datetime
    close: float


def load_bars(path: Path) -> list[Bar]:
    bars: list[Bar] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"instrument", "open_time", "close_price"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV must contain instrument, open_time, close_price")
        for line, row in enumerate(reader, start=2):
            try:
                timestamp = datetime.fromisoformat(row["open_time"].replace("Z", "+00:00"))
                close = float(row["close_price"])
                instrument = row["instrument"].strip().upper()
                if not instrument or not math.isfinite(close) or close <= 0:
                    raise ValueError
                if timestamp.tzinfo is None:
                    raise ValueError("timestamp must include timezone")
                bars.append(Bar(instrument, timestamp, close))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid candle at CSV line {line}") from exc
    bars.sort(key=lambda b: (b.instrument, b.timestamp))
    deduped: list[Bar] = []
    seen: set[tuple[str, datetime]] = set()
    for bar in bars:
        key = (bar.instrument, bar.timestamp)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(bar)
    return deduped


def evaluate(
    bars: Sequence[Bar],
    lookback: int = 3,
    horizon: int = 1,
    spread_bps: float = 1.0,
    commission_bps: float = 0.0,
    slippage_bps: float = 1.0,
) -> dict:
    if lookback < 1 or horizon < 1:
        raise ValueError("lookback and horizon must be positive")
    if min(spread_bps, commission_bps, slippage_bps) < 0:
        raise ValueError("cost assumptions cannot be negative")
    cost_bps = spread_bps + commission_bps + slippage_bps
    grouped: dict[str, list[Bar]] = {}
    for bar in bars:
        grouped.setdefault(bar.instrument, []).append(bar)
    outcomes: list[dict] = []
    for instrument, series in grouped.items():
        for origin in range(lookback, len(series) - horizon):
            # Only information up to and including origin is used to create the signal.
            prior = series[origin - lookback].close
            current = series[origin].close
            signal = 1 if current > prior else -1 if current < prior else 0
            future = series[origin + horizon].close
            gross_bps = (future / current - 1.0) * 10000.0 * signal
            net_bps = gross_bps - (cost_bps if signal else 0.0)
            outcomes.append({
                "instrument": instrument,
                "origin_time": series[origin].timestamp.isoformat(),
                "target_time": series[origin + horizon].timestamp.isoformat(),
                "signal": signal,
                "gross_return_bps": round(gross_bps, 5),
                "cost_bps": round(cost_bps if signal else 0.0, 5),
                "net_return_bps": round(net_bps, 5),
                "directional_hit": bool(signal and ((future > current and signal > 0) or (future < current and signal < 0))),
            })
    active = [o for o in outcomes if o["signal"]]
    net = [o["net_return_bps"] for o in active]
    gross = [o["gross_return_bps"] for o in active]
    wins = sum(v > 0 for v in net)
    return {
        "research_only": True,
        "strategy": "rolling_momentum_baseline",
        "lookback_bars": lookback,
        "horizon_bars": horizon,
        "assumed_round_trip_cost_bps": cost_bps,
        "forecast_count": len(outcomes),
        "active_signal_count": len(active),
        "directional_accuracy": round(sum(o["directional_hit"] for o in active) / len(active), 4) if active else None,
        "net_win_rate": round(wins / len(net), 4) if net else None,
        "mean_gross_return_bps": round(sum(gross) / len(gross), 5) if gross else None,
        "mean_net_return_bps": round(sum(net) / len(net), 5) if net else None,
        "total_net_return_bps_simple_sum": round(sum(net), 5) if net else None,
        "outcomes": outcomes,
        "warning": "Historical walk-forward research only; not a live signal or proof of future edge. Costs are simplified assumptions.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="CSV exported from trusted market_bars data")
    parser.add_argument("--lookback", type=int, default=3)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--spread-bps", type=float, default=1.0)
    parser.add_argument("--commission-bps", type=float, default=0.0)
    parser.add_argument("--slippage-bps", type=float, default=1.0)
    parser.add_argument("--out", type=Path, help="Optional JSON report output path")
    args = parser.parse_args()
    result = evaluate(load_bars(args.csv), args.lookback, args.horizon, args.spread_bps, args.commission_bps, args.slippage_bps)
    rendered = json.dumps(result, indent=2)
    if args.out:
        args.out.write_text(rendered + "\\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
