-- EQ Options initial research schema.
-- All tables are RLS-protected with no public/anon policies by design.
-- Access must be performed by trusted server-side components only.

create extension if not exists pgcrypto;

create table public.market_bars (
  id bigint generated always as identity primary key,
  instrument text not null check (instrument ~ '^[A-Z]{3,12}([/_-][A-Z]{3,12})?$'),
  timeframe text not null check (timeframe in ('M1','M5','M15','M30','H1','H4','D1')),
  open_time timestamptz not null,
  open_price numeric(20,10) not null check (open_price > 0),
  high_price numeric(20,10) not null check (high_price > 0),
  low_price numeric(20,10) not null check (low_price > 0),
  close_price numeric(20,10) not null check (close_price > 0),
  volume numeric(24,8),
  source text not null,
  received_at timestamptz not null default now(),
  check (high_price >= greatest(open_price, close_price, low_price)),
  check (low_price <= least(open_price, close_price, high_price)),
  unique (instrument, timeframe, open_time, source)
);

create index market_bars_lookup_idx
  on public.market_bars (instrument, timeframe, open_time desc);

create table public.forecasts (
  id uuid primary key default gen_random_uuid(),
  instrument text not null,
  timeframe text not null check (timeframe in ('M1','M5','M15','M30','H1','H4','D1')),
  issued_at timestamptz not null default now(),
  input_last_bar_at timestamptz not null,
  horizon_bars smallint not null check (horizon_bars between 1 and 5),
  direction text not null check (direction in ('bullish','bearish','neutral')),
  predicted_return_bps numeric(12,5),
  model_name text not null,
  model_version text not null,
  forecast_payload jsonb not null default '{}'::jsonb,
  expires_at timestamptz,
  research_only boolean not null default true,
  created_at timestamptz not null default now()
);

create index forecasts_instrument_issued_idx
  on public.forecasts (instrument, issued_at desc);

create table public.forecast_evaluations (
  id uuid primary key default gen_random_uuid(),
  forecast_id uuid not null references public.forecasts(id) on delete cascade,
  evaluated_at timestamptz not null default now(),
  actual_return_bps numeric(12,5),
  directional_hit boolean,
  max_adverse_excursion_bps numeric(12,5),
  max_favorable_excursion_bps numeric(12,5),
  spread_bps numeric(12,5),
  commission_bps numeric(12,5),
  slippage_bps numeric(12,5),
  latency_ms integer check (latency_ms is null or latency_ms >= 0),
  evaluation_notes jsonb not null default '{}'::jsonb,
  unique (forecast_id)
);

create table public.data_source_health (
  id bigint generated always as identity primary key,
  source text not null,
  instrument text,
  checked_at timestamptz not null default now(),
  healthy boolean not null,
  latency_ms integer check (latency_ms is null or latency_ms >= 0),
  details jsonb not null default '{}'::jsonb
);

create index data_source_health_recent_idx
  on public.data_source_health (source, checked_at desc);

alter table public.market_bars enable row level security;
alter table public.forecasts enable row level security;
alter table public.forecast_evaluations enable row level security;
alter table public.data_source_health enable row level security;

comment on table public.market_bars is 'Validated market bars used for research. Not a trading execution feed.';
comment on table public.forecasts is 'Experimental research forecasts; not financial advice and not calibrated probabilities.';
comment on table public.forecast_evaluations is 'Chronological forecast outcomes and execution-cost-aware evaluation metrics.';
comment on table public.data_source_health is 'Market data source health and freshness telemetry.';
