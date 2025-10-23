-- Trading SMS Assistant - Initial Schema
-- Run this in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone VARCHAR(20) UNIQUE NOT NULL,
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    risk_tolerance VARCHAR(20) DEFAULT 'moderate', -- conservative, moderate, aggressive
    capital DECIMAL(12, 2),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Screener alerts table
CREATE TABLE screener_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- 'gap_up', 'volume_spike', 'pattern_break', etc.
    trigger_price DECIMAL(12, 4),
    trigger_time TIMESTAMP WITH TIME ZONE NOT NULL,
    conditions JSONB, -- Flexible storage for alert criteria
    metadata JSONB, -- Additional data like indicators, patterns
    sent_to_users UUID[], -- Array of user IDs who received this alert
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on symbol and trigger_time for fast queries
CREATE INDEX idx_screener_alerts_symbol ON screener_alerts(symbol);
CREATE INDEX idx_screener_alerts_trigger_time ON screener_alerts(trigger_time DESC);
CREATE INDEX idx_screener_alerts_active ON screener_alerts(active) WHERE active = true;

-- Trades table
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    alert_id UUID REFERENCES screener_alerts(id),
    symbol VARCHAR(10) NOT NULL,

    -- Entry
    entry_price DECIMAL(12, 4),
    entry_time TIMESTAMP WITH TIME ZONE,
    entry_confirmed BOOLEAN DEFAULT false,
    shares INTEGER,

    -- Risk management
    stop_loss DECIMAL(12, 4),
    take_profit DECIMAL(12, 4),

    -- Exit
    exit_price DECIMAL(12, 4),
    exit_time TIMESTAMP WITH TIME ZONE,
    exit_reason VARCHAR(50), -- 'stop_loss', 'take_profit', 'manual', 'timeout'

    -- P&L
    pnl DECIMAL(12, 2),
    pnl_percent DECIMAL(8, 4),

    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'entered', 'monitoring', 'exited'

    -- Chart data (store recent bars for analysis)
    bars_data JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for trades
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_entry_time ON trades(entry_time DESC);

-- SMS messages table
CREATE TABLE sms_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    trade_id UUID REFERENCES trades(id) ON DELETE SET NULL,
    direction VARCHAR(10) NOT NULL, -- 'inbound', 'outbound'
    body TEXT NOT NULL,
    parsed_data JSONB, -- AI-extracted structured data
    twilio_sid VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'delivered', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for SMS
CREATE INDEX idx_sms_user_id ON sms_messages(user_id);
CREATE INDEX idx_sms_created_at ON sms_messages(created_at DESC);

-- Market data cache (for recent bars and indicators)
CREATE TABLE market_data_cache (
    symbol VARCHAR(10) PRIMARY KEY,
    timeframe VARCHAR(10) NOT NULL, -- '1m', '5m', '1d', etc.
    bars JSONB NOT NULL, -- Array of OHLCV bars
    indicators JSONB, -- Computed indicators (RSI, VWAP, etc.)
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for market data
CREATE INDEX idx_market_data_last_updated ON market_data_cache(last_updated DESC);

-- Screener performance metrics
CREATE TABLE screener_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    symbols_scanned INTEGER,
    alerts_generated INTEGER,
    latency_ms INTEGER,
    errors INTEGER DEFAULT 0,
    metadata JSONB
);

-- Index for performance tracking
CREATE INDEX idx_screener_performance_timestamp ON screener_performance(timestamp DESC);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) - Enable for user-facing tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE sms_messages ENABLE ROW LEVEL SECURITY;

-- RLS Policies (users can only see their own data)
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can view own trades" ON trades
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own SMS" ON sms_messages
    FOR SELECT USING (auth.uid() = user_id);

-- Service role can do everything (for backend services)
-- No additional policies needed as service role key bypasses RLS

-- Create a view for active alerts with user counts
CREATE OR REPLACE VIEW active_alerts_summary AS
SELECT
    a.*,
    COALESCE(array_length(a.sent_to_users, 1), 0) as user_count,
    t.trade_count
FROM screener_alerts a
LEFT JOIN (
    SELECT alert_id, COUNT(*) as trade_count
    FROM trades
    GROUP BY alert_id
) t ON a.id = t.alert_id
WHERE a.active = true
ORDER BY a.trigger_time DESC;
