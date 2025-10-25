-- Migration: Create historical data tables for regression testing
-- These tables store historical bar data fetched from Databento for backtesting

-- 1. Create historical_bars table (stores fetched historical 1-min OHLCV data)
CREATE TABLE IF NOT EXISTS historical_bars (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10, 4) NOT NULL,
    high DECIMAL(10, 4) NOT NULL,
    low DECIMAL(10, 4) NOT NULL,
    close DECIMAL(10, 4) NOT NULL,
    volume BIGINT DEFAULT 0,
    trade_count INTEGER DEFAULT 0,

    -- Metadata for tracking data source
    data_source VARCHAR(50) DEFAULT 'databento_historical', -- databento_historical, manual_import, etc.
    fetch_date TIMESTAMPTZ DEFAULT NOW(), -- When this data was fetched
    dataset VARCHAR(50) DEFAULT 'EQUS.MINI', -- Which Databento dataset
    schema_type VARCHAR(50) DEFAULT 'trades', -- trades, mbp-1, ohlcv-1m, etc.

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create composite index for fast queries (symbol + time range)
CREATE INDEX IF NOT EXISTS idx_historical_bars_symbol_timestamp
    ON historical_bars(symbol, timestamp DESC);

-- 3. Create index for time-based queries
CREATE INDEX IF NOT EXISTS idx_historical_bars_timestamp
    ON historical_bars(timestamp DESC);

-- 4. Ensure unique bars (one bar per symbol per minute)
CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_bars_unique
    ON historical_bars(symbol, timestamp);

-- 5. Index for data source filtering
CREATE INDEX IF NOT EXISTS idx_historical_bars_source
    ON historical_bars(data_source, symbol);

-- Comments for documentation
COMMENT ON TABLE historical_bars IS 'Historical 1-minute OHLCV bars fetched from Databento for regression testing and backtesting. Separate from live price_bars table.';
COMMENT ON COLUMN historical_bars.timestamp IS 'Bar timestamp (start of 1-minute period, aligned to minute boundary)';
COMMENT ON COLUMN historical_bars.data_source IS 'Where this data came from (databento_historical, manual_import, etc.)';
COMMENT ON COLUMN historical_bars.fetch_date IS 'When this historical data was fetched/imported';
COMMENT ON COLUMN historical_bars.dataset IS 'Databento dataset name (EQUS.MINI, etc.)';
COMMENT ON COLUMN historical_bars.schema_type IS 'Databento schema used (trades, mbp-1, ohlcv-1m, etc.)';

-- 6. Create historical_symbols table to track what we've fetched
CREATE TABLE IF NOT EXISTS historical_symbols (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    bar_count INTEGER DEFAULT 0,
    data_source VARCHAR(50) DEFAULT 'databento_historical',
    dataset VARCHAR(50) DEFAULT 'EQUS.MINI',
    schema_type VARCHAR(50) DEFAULT 'trades',
    status VARCHAR(20) DEFAULT 'pending', -- pending, fetching, completed, failed
    error_message TEXT,
    fetch_started_at TIMESTAMPTZ,
    fetch_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Ensure unique symbol+date range combinations
CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_symbols_unique
    ON historical_symbols(symbol, start_date, end_date);

-- 8. Index for status queries
CREATE INDEX IF NOT EXISTS idx_historical_symbols_status
    ON historical_symbols(status);

COMMENT ON TABLE historical_symbols IS 'Tracks which symbols have historical data fetched and their date ranges';

-- 9. View for quick statistics
CREATE OR REPLACE VIEW historical_data_summary AS
SELECT
    hs.symbol,
    hs.start_date,
    hs.end_date,
    hs.bar_count as expected_bars,
    COUNT(hb.id) as actual_bars,
    hs.status,
    hs.fetch_completed_at,
    MIN(hb.timestamp) as first_bar,
    MAX(hb.timestamp) as last_bar,
    CASE
        WHEN hs.bar_count > 0 THEN ROUND((COUNT(hb.id)::numeric / hs.bar_count) * 100, 2)
        ELSE 0
    END as completeness_pct
FROM historical_symbols hs
LEFT JOIN historical_bars hb ON hs.symbol = hb.symbol
    AND hb.timestamp >= hs.start_date
    AND hb.timestamp <= hs.end_date
GROUP BY hs.symbol, hs.start_date, hs.end_date, hs.bar_count, hs.status, hs.fetch_completed_at;

COMMENT ON VIEW historical_data_summary IS 'Summary of historical data completeness per symbol';

-- 10. Trigger to update updated_at on historical_symbols
CREATE OR REPLACE FUNCTION update_historical_symbols_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_historical_symbols_updated_at
    BEFORE UPDATE ON historical_symbols
    FOR EACH ROW
    EXECUTE FUNCTION update_historical_symbols_updated_at();
