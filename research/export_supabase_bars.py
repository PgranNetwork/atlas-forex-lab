#!/usr/bin/env python3
"""Export validated M1 candles from Supabase to CSV for offline research.

Credentials are read only from SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.
Never pass secrets on the command line or commit them to the repository.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FIELDS = ("instrument", "open_time", "close_price")


def fetch_page(base_url: str, key: str, offset: int, limit: int, snapshot: str) -> list[dict[str, str]]:
    params = {
        "select": ",".join(FIELDS),
        "timeframe": "eq.M1",
        "received_at": "lte." + snapshot,
        "order": "instrument.asc,open_time.asc",
        "limit": str(limit),
        "offset": str(offset),
    }
    url = base_url.rstrip("/") + "/rest/v1/market_bars?" + urlencode(params)
    request = Request(
        url,
        headers={
            "apikey": key,
            "Authorization": "Bearer " + key,
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            import json

            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Supabase request failed: {exc}") from exc
    if not isinstance(payload, list):
        raise RuntimeError("Supabase returned an unexpected response")
    return payload


def export_bars(output: Path, page_size: int = 1000) -> int:
    base_url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not base_url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment")
    if not 1 <= page_size <= 1000:
        raise ValueError("page_size must be between 1 and 1000")

    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    offset = 0
    snapshot = datetime.now(timezone.utc).isoformat()
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        while True:
            page = fetch_page(base_url, key, offset, page_size, snapshot)
            for row in page:
                if not all(field in row for field in FIELDS):
                    raise RuntimeError("Supabase row is missing required candle fields")
                writer.writerow({field: row[field] for field in FIELDS})
            count += len(page)
            if len(page) < page_size:
                break
            offset += len(page)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Destination CSV path")
    parser.add_argument("--page-size", type=int, default=1000, help="Rows per request (max 1000)")
    args = parser.parse_args()
    try:
        count = export_bars(args.output, args.page_size)
    except (RuntimeError, ValueError) as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 1
    print(f"Exported {count} M1 candles to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
