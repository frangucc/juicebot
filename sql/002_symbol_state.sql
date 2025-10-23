-- Symbol State Tracking Table
-- This table maintains real-time state for all symbols being tracked
-- Updated on every MBP-1 tick from Databento

CREATE TABLE symbol_state (
    symbol VARCHAR(10) PRIMARY KEY,

    -- Current price data
    current_price DECIMAL(12, 4) NOT NULL,
    current_bid DECIMAL(12, 4),
    current_ask DECIMAL(12, 4),
    current_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Baseline prices for % calculations
    yesterday_close DECIMAL(12, 4),
    today_open DECIMAL(12, 4),
    price_15min_ago DECIMAL(12, 4),
    price_5min_ago DECIMAL(12, 4),

    -- Snapshot timestamps for rolling windows
    snapshot_15min_ts TIMESTAMP WITH TIME ZONE,
    snapshot_5min_ts TIMESTAMP WITH TIME ZONE,

    -- Current % moves from baselines
    pct_from_yesterday DECIMAL(8, 4),
    pct_from_open DECIMAL(8, 4),
    pct_from_15min DECIMAL(8, 4),
    pct_from_5min DECIMAL(8, 4),

    -- High of Day (HOD) tracking
    hod_price DECIMAL(12, 4),
    hod_pct DECIMAL(8, 4),  -- Peak % from yesterday's close
    hod_timestamp TIMESTAMP WITH TIME ZONE,

    -- Low of Day (LOD) tracking
    lod_price DECIMAL(12, 4),
    lod_pct DECIMAL(8, 4),  -- Lowest % from yesterday's close (negative)
    lod_timestamp TIMESTAMP WITH TIME ZONE,

    -- Spread tracking for quality control
    spread_pct DECIMAL(8, 4),

    -- Last update timestamp
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_symbol_state_pct_yesterday ON symbol_state(pct_from_yesterday DESC) WHERE pct_from_yesterday IS NOT NULL;
CREATE INDEX idx_symbol_state_pct_open ON symbol_state(pct_from_open DESC) WHERE pct_from_open IS NOT NULL;
CREATE INDEX idx_symbol_state_hod_pct ON symbol_state(hod_pct DESC) WHERE hod_pct IS NOT NULL;
CREATE INDEX idx_symbol_state_last_updated ON symbol_state(last_updated DESC);

-- Index for leaderboard queries (symbols above threshold)
CREATE INDEX idx_symbol_state_movers ON symbol_state(pct_from_yesterday DESC)
    WHERE pct_from_yesterday >= 1.0 OR pct_from_yesterday <= -1.0;

-- Time-series table for ML training data
-- Stores snapshots of symbol state at regular intervals
CREATE TABLE symbol_state_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Price data at this moment
    price DECIMAL(12, 4) NOT NULL,
    bid DECIMAL(12, 4),
    ask DECIMAL(12, 4),
    spread_pct DECIMAL(8, 4),

    -- Percentage moves at this moment
    pct_from_yesterday DECIMAL(8, 4),
    pct_from_open DECIMAL(8, 4),
    pct_from_15min DECIMAL(8, 4),
    pct_from_5min DECIMAL(8, 4),

    -- HOD/LOD at this moment
    hod_pct DECIMAL(8, 4),
    lod_pct DECIMAL(8, 4),

    -- Alert context (was there an active alert?)
    alert_active BOOLEAN DEFAULT false,
    alert_type VARCHAR(50),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for time-series queries
CREATE INDEX idx_symbol_state_history_symbol_ts ON symbol_state_history(symbol, timestamp DESC);
CREATE INDEX idx_symbol_state_history_timestamp ON symbol_state_history(timestamp DESC);

-- Partition by day for efficient storage (optional, for high-volume data)
-- CREATE INDEX idx_symbol_state_history_timestamp_brin ON symbol_state_history USING BRIN(timestamp);

-- View for leaderboard (symbols with significant moves)
CREATE OR REPLACE VIEW leaderboard_symbols AS
SELECT
    symbol,
    current_price,
    pct_from_yesterday,
    pct_from_open,
    pct_from_15min,
    pct_from_5min,
    hod_pct,
    lod_pct,
    hod_timestamp,
    lod_timestamp,
    spread_pct,
    last_updated,
    CASE
        WHEN ABS(pct_from_yesterday) >= 20 THEN '20%+'
        WHEN ABS(pct_from_yesterday) >= 10 THEN '10-20%'
        WHEN ABS(pct_from_yesterday) >= 1 THEN '1-10%'
        ELSE 'below_threshold'
    END as move_category
FROM symbol_state
WHERE pct_from_yesterday IS NOT NULL
ORDER BY ABS(pct_from_yesterday) DESC;

-- View for today's biggest movers
CREATE OR REPLACE VIEW top_movers_today AS
SELECT
    symbol,
    current_price,
    yesterday_close,
    pct_from_yesterday,
    hod_price,
    hod_pct,
    hod_timestamp,
    last_updated
FROM symbol_state
WHERE pct_from_yesterday IS NOT NULL
ORDER BY ABS(pct_from_yesterday) DESC
LIMIT 100;

-- Function to reset daily state (run at market open)
CREATE OR REPLACE FUNCTION reset_daily_state()
RETURNS void AS $$
BEGIN
    -- Archive yesterday's HOD/LOD data to history table before reset
    INSERT INTO symbol_state_history (
        symbol, timestamp, price, bid, ask, spread_pct,
        pct_from_yesterday, hod_pct, lod_pct, alert_active
    )
    SELECT
        symbol,
        NOW(),
        current_price,
        current_bid,
        current_ask,
        spread_pct,
        pct_from_yesterday,
        hod_pct,
        lod_pct,
        false
    FROM symbol_state
    WHERE pct_from_yesterday IS NOT NULL;

    -- Reset daily fields
    UPDATE symbol_state SET
        today_open = NULL,
        hod_price = NULL,
        hod_pct = NULL,
        hod_timestamp = NULL,
        lod_price = NULL,
        lod_pct = NULL,
        lod_timestamp = NULL,
        pct_from_open = NULL,
        price_15min_ago = NULL,
        price_5min_ago = NULL,
        pct_from_15min = NULL,
        pct_from_5min = NULL,
        snapshot_15min_ts = NULL,
        snapshot_5min_ts = NULL;

    -- Yesterday's close becomes today's reference
    -- (Scanner will update yesterday_close from daily bars at market open)
END;
$$ LANGUAGE plpgsql;
