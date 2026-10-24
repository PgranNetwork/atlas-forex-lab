"""Research-only CLI; never places orders."""
from datetime import datetime, timedelta, timezone
import typer
from atlas_forex_lab.contracts.market import Timeframe
from atlas_forex_lab.market_data.base import MarketDataError
from atlas_forex_lab.market_data.synthetic import SyntheticProvider
from atlas_forex_lab.forecasting.momentum import ForecastInputError, MomentumBaseline
app = typer.Typer(no_args_is_help=True, help="Atlas Forex Lab research-only CLI")
@app.command("check-data")
def check_data(source: str = typer.Option("synthetic"), instrument: str = typer.Option("EURUSD"), timeframe: Timeframe = typer.Option(Timeframe.M1), bars: int = typer.Option(30, min=1, max=10000)) -> None:
    """Fetch a small sample and print data-quality summary."""
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    step = timedelta(minutes=1 if timeframe == Timeframe.M1 else 5)
    start = now - step * bars
    try:
        if source == "synthetic":
            provider = SyntheticProvider()
        elif source == "mt5":
            from atlas_forex_lab.market_data.mt5 import MT5Provider
            provider = MT5Provider()
        else:
            raise typer.BadParameter("source must be synthetic or mt5")
        records = provider.fetch_bars(instrument.upper(), timeframe, start, now, limit=bars)
    except (MarketDataError, ValueError) as exc:
        typer.echo(f"DATA CHECK FAILED: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if not records:
        typer.echo("DATA CHECK FAILED: provider returned zero bars", err=True)
        raise typer.Exit(code=1)
    timestamps = [r.timestamp for r in records]
    malformed = sum(1 for r in records if r.high is None or r.low is None or r.open is None or r.close is None or r.high < max(r.open, r.close, r.low) or r.low > min(r.open, r.close, r.high))
    typer.echo(f"source={source}\ninstrument={instrument.upper()} timeframe={timeframe.value}\nbars_received={len(records)} requested={bars}\nfirst_timestamp={records[0].timestamp.isoformat()}\nlast_timestamp={records[-1].timestamp.isoformat()}\nduplicate_timestamps={len(timestamps)-len(set(timestamps))}\nmalformed_bars={malformed}\nmode=RESEARCH_ONLY; order_placement=NOT_IMPLEMENTED")
    if len(timestamps) != len(set(timestamps)) or malformed:
        raise typer.Exit(code=1)
@app.command("forecast-demo")
def forecast_demo(instrument: str = typer.Option("EURUSD"), bars: int = typer.Option(30, min=20, max=10000), horizon: int = typer.Option(1, min=1, max=5)) -> None:
    """Run baseline on synthetic fixtures only; not live market data."""
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    observations = SyntheticProvider().fetch_bars(instrument.upper(), Timeframe.M1, now-timedelta(minutes=bars), now, limit=bars)
    try:
        signal = MomentumBaseline().predict(observations, horizon_bars=horizon, generated_at=now)
    except (ForecastInputError, ValueError) as exc:
        typer.echo(f"FORECAST DEMO FAILED: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"source=SYNTHETIC_FIXTURE instrument={signal.instrument}")
    typer.echo(f"horizon={signal.horizon_bars} minute_bar(s) direction={signal.direction.value}")
    typer.echo(f"heuristic_score={signal.score:.4f} calibrated_probability=NO")
    typer.echo(f"model={signal.model_id} research_only=YES live_trading=NOT_IMPLEMENTED")
    for item in signal.rationale:
        typer.echo(f"- {item}")
    typer.echo("Synthetic output is not market data and is not evidence of predictive performance.")
@app.command("ingest-live")
def ingest_live(
    instrument: str = typer.Option("EURUSD", help="Supported FX pair or XAUUSD."),
    timeframe: Timeframe = typer.Option(Timeframe.M1),
    bars: int = typer.Option(100, min=1, max=1000),
) -> None:
    """Fetch real Twelve Data candles and persist them to Supabase; never uses synthetic data."""
    import os
    from atlas_forex_lab.market_data.twelvedata import TwelveDataProvider
    from atlas_forex_lab.market_data.supabase_store import SupabaseMarketStore

    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    step = timedelta(minutes=1 if timeframe == Timeframe.M1 else 5)
    start = now - step * bars
    provider = None
    store = None
    try:
        provider = TwelveDataProvider()
        store = SupabaseMarketStore()
        records = provider.fetch_bars(instrument.upper(), timeframe, start, now, limit=bars)
        # Never persist data that failed basic chronology or OHLC checks.
        timestamps = [record.timestamp for record in records]
        if not records or len(timestamps) != len(set(timestamps)):
            raise MarketDataError("feed returned no bars or duplicate timestamps")
        for record in records:
            if record.high is None or record.low is None or record.open is None or record.close is None:
                raise MarketDataError("feed returned an incomplete OHLC bar")
            if record.high < max(record.open, record.close, record.low) or record.low > min(record.open, record.close, record.high):
                raise MarketDataError("feed returned an invalid OHLC range")
        saved = store.save_bars(records)
        latency = getattr(provider, "last_latency_ms", None)
        store.save_health(
            source=provider.name,
            instrument=instrument.upper(),
            healthy=True,
            latency_ms=latency,
            details={"timeframe": timeframe.value, "bars_received": len(records), "bars_submitted": saved},
        )
        typer.echo(
            f"source={provider.name}\\ninstrument={instrument.upper()} timeframe={timeframe.value}"
            f"\\nbars_received={len(records)}\\nbars_submitted={saved}"
            f"\\nfirst_timestamp={records[0].timestamp.isoformat()}"
            f"\\nlast_timestamp={records[-1].timestamp.isoformat()}"
            f"\\nprovider_latency_ms={latency}\\nmode=RESEARCH_ONLY; order_placement=NOT_IMPLEMENTED"
        )
    except (MarketDataError, ValueError) as exc:
        if store is not None:
            try:
                store.save_health(
                    source="twelvedata",
                    instrument=instrument.upper(),
                    healthy=False,
                    latency_ms=getattr(provider, "last_latency_ms", None) if provider else None,
                    details={"error_type": type(exc).__name__, "message": str(exc)[:160]},
                )
            except MarketDataError:
                pass
        typer.echo(f"LIVE INGEST FAILED: {exc}", err=True)
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
