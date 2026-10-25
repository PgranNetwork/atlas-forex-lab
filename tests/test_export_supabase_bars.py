import csv
from pathlib import Path

import pytest

from research import export_supabase_bars as exporter


def test_export_uses_fixed_snapshot_and_paginates(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    calls = []

    def fake_fetch_page(base_url, key, offset, limit, snapshot):
        calls.append((base_url, key, offset, limit, snapshot))
        if offset == 0:
            return [
                {"instrument": "EURUSD", "open_time": "2026-01-01T00:00:00+00:00", "open_price": "1.0", "high_price": "1.2", "low_price": "0.9", "close_price": "1.1"},
                {"instrument": "GBPUSD", "open_time": "2026-01-01T00:00:00+00:00", "open_price": "1.1", "high_price": "1.3", "low_price": "1.0", "close_price": "1.2"},
            ]
        return [
            {"instrument": "USDJPY", "open_time": "2026-01-01T00:00:00+00:00", "open_price": "149.8", "high_price": "150.2", "low_price": "149.7", "close_price": "150.0"}
        ]

    monkeypatch.setattr(exporter, "fetch_page", fake_fetch_page)
    output = tmp_path / "candles.csv"
    count = exporter.export_bars(output, page_size=2)

    assert count == 3
    assert [call[2] for call in calls] == [0, 2]
    assert calls[0][4] == calls[1][4]
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    assert rows[0]["instrument"] == "EURUSD"


def test_export_requires_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Set SUPABASE_URL"):
        exporter.export_bars(tmp_path / "candles.csv")


def test_export_rejects_page_size_out_of_range(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    with pytest.raises(ValueError, match="page_size"):
        exporter.export_bars(tmp_path / "candles.csv", page_size=1001)


def test_export_rejects_invalid_ohlc(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setattr(exporter, "fetch_page", lambda *args: [
        {"instrument": "EURUSD", "open_time": "2026-01-01T00:00:00+00:00",
         "open_price": "1.2", "high_price": "1.1", "low_price": "1.0", "close_price": "1.05"}
    ])
    with pytest.raises(RuntimeError, match="invalid OHLC"):
        exporter.export_bars(tmp_path / "bad.csv")
