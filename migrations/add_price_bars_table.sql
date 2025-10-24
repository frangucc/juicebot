-- Migration: Add price_bars table for 1-minute OHLCV data
-- This runs ALONGSIDE existing tables - no breaking changes

-- 1. Create price_bars table (1-minute OHLCV bars for ALL symbols)
CREATE TABLE IF NOT EXISTS price_bars (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10, 4) NOT NULL,
    high DECIMAL(10, 4) NOT NULL,
    low DECIMAL(10, 4) NOT NULL,
    close DECIMAL(10, 4) NOT NULL,
    volume BIGINT DEFAULT 0,
    trade_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create composite index for fast queries (symbol + time range)
CREATE INDEX IF NOT EXISTS idx_price_bars_symbol_timestamp
    ON price_bars(symbol, timestamp DESC);

-- 3. Create index for time-based queries (cleanup, aggregations)
CREATE INDEX IF NOT EXISTS idx_price_bars_timestamp
    ON price_bars(timestamp DESC);

-- 4. Ensure unique bars (one bar per symbol per minute)
CREATE UNIQUE INDEX IF NOT EXISTS idx_price_bars_unique
    ON price_bars(symbol, timestamp);

-- 5. Add partition by date for performance (optional but recommended)
-- This allows efficient deletion of old data and faster queries
-- Uncomment when you're ready to enable partitioning:
-- ALTER TABLE price_bars PARTITION BY RANGE (timestamp);

COMMENT ON TABLE price_bars IS 'High-frequency 1-minute OHLCV bars for all symbols. Used for accurate baseline calculations and future algorithmic trading.';
COMMENT ON COLUMN price_bars.timestamp IS 'Bar timestamp (start of 1-minute period, aligned to minute boundary)';
COMMENT ON COLUMN price_bars.open IS 'First trade price in the 1-minute window';
COMMENT ON COLUMN price_bars.high IS 'Highest trade price in the 1-minute window';
COMMENT ON COLUMN price_bars.low IS 'Lowest trade price in the 1-minute window';
COMMENT ON COLUMN price_bars.close IS 'Last trade price in the 1-minute window';
COMMENT ON COLUMN price_bars.volume IS 'Total volume traded in the 1-minute window (if available)';
COMMENT ON COLUMN price_bars.trade_count IS 'Number of trades in the 1-minute window';
