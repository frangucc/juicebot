-- Quick Create for symbol_state table
-- Copy and paste this into Supabase SQL Editor

CREATE TABLE symbol_state (
    symbol VARCHAR(10) PRIMARY KEY,
    current_price NUMERIC NOT NULL,
    current_bid NUMERIC,
    current_ask NUMERIC,
    current_timestamp TIMESTAMPTZ NOT NULL,
    yesterday_close NUMERIC,
    today_open NUMERIC,
    price_15min_ago NUMERIC,
    price_5min_ago NUMERIC,
    snapshot_15min_ts TIMESTAMPTZ,
    snapshot_5min_ts TIMESTAMPTZ,
    pct_from_yesterday NUMERIC,
    pct_from_open NUMERIC,
    pct_from_15min NUMERIC,
    pct_from_5min NUMERIC,
    hod_price NUMERIC,
    hod_pct NUMERIC,
    hod_timestamp TIMESTAMPTZ,
    lod_price NUMERIC,
    lod_pct NUMERIC,
    lod_timestamp TIMESTAMPTZ,
    spread_pct NUMERIC,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_symbol_state_pct_yesterday ON symbol_state(pct_from_yesterday DESC) WHERE pct_from_yesterday IS NOT NULL;
CREATE INDEX idx_symbol_state_last_updated ON symbol_state(last_updated DESC);
