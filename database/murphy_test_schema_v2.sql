-- Murphy Test Sessions Schema V2 - Enhanced with Heat/Gain Tracking
-- Records all signals with real-time peak gain, max heat, and duration tracking

-- Test Sessions table
CREATE TABLE IF NOT EXISTS murphy_test_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol TEXT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'active', -- 'active', 'completed', 'cancelled'
    notes TEXT,

    -- Filter configuration at session start
    config JSONB DEFAULT '{
        "min_stars": 3,
        "min_grade": 7,
        "min_confidence": 1.0,
        "sticky_direction": true,
        "require_flip_conviction": true
    }'::jsonb,

    -- Computed metrics (updated as session runs)
    metrics JSONB DEFAULT '{
        "total_signals_generated": 0,
        "signals_displayed": 0,
        "signals_filtered": 0,
        "win_count": 0,
        "loss_count": 0,
        "win_rate": 0,
        "avg_gain": 0,
        "avg_heat": 0,
        "avg_duration_seconds": 0
    }'::jsonb,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Signal Records table - stores every signal Murphy generates
CREATE TABLE IF NOT EXISTS murphy_signal_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES murphy_test_sessions(id) ON DELETE CASCADE,

    -- Signal metadata
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    entry_price FLOAT NOT NULL,
    bar_count_at_signal INTEGER, -- How many bars when signal fired (detect premature signals)

    -- Signal classification
    direction TEXT NOT NULL, -- 'BULLISH', 'BEARISH', 'NEUTRAL'
    stars INTEGER NOT NULL,
    grade INTEGER NOT NULL,
    confidence FLOAT NOT NULL,

    -- Murphy details
    rvol FLOAT,
    volume_efficiency FLOAT,
    body_ratio FLOAT,
    atr_ratio FLOAT,
    interpretation TEXT,

    -- V2 enhancements
    has_liquidity_sweep BOOLEAN DEFAULT FALSE,
    rejection_type TEXT,
    pattern TEXT,
    fvg_momentum TEXT,

    -- Filtering results
    passed_filter BOOLEAN NOT NULL, -- Did this signal make it to the UI?
    filter_reason TEXT, -- Why was it filtered? (if not passed)

    -- Signal lifecycle tracking
    signal_changed_at TIMESTAMP WITH TIME ZONE, -- When signal direction changed or ended
    duration_seconds INTEGER, -- How long signal was active

    -- Price movement tracking (THE IMPORTANT STUFF!)
    peak_price FLOAT, -- Best price in signal direction (highest for BULLISH, lowest for BEARISH)
    peak_gain_pct FLOAT, -- Max % gain in favorable direction
    peak_reached_at TIMESTAMP WITH TIME ZONE,

    worst_price FLOAT, -- Worst price against signal (lowest for BULLISH, highest for BEARISH)
    max_heat_pct FLOAT, -- Max % drawdown (how much it went against you)
    heat_reached_at TIMESTAMP WITH TIME ZONE,

    exit_price FLOAT, -- Price when signal changed/ended
    final_pnl_pct FLOAT, -- Net result at exit (entry -> exit)

    -- Final result
    final_result TEXT DEFAULT 'active', -- 'win', 'loss', 'neutral', 'active', 'premature'

    -- Raw signal data for debugging
    raw_data JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_murphy_sessions_symbol ON murphy_test_sessions(symbol);
CREATE INDEX IF NOT EXISTS idx_murphy_sessions_status ON murphy_test_sessions(status);
CREATE INDEX IF NOT EXISTS idx_murphy_sessions_started ON murphy_test_sessions(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_murphy_signals_session ON murphy_signal_records(session_id);
CREATE INDEX IF NOT EXISTS idx_murphy_signals_symbol ON murphy_signal_records(symbol);
CREATE INDEX IF NOT EXISTS idx_murphy_signals_timestamp ON murphy_signal_records(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_murphy_signals_passed ON murphy_signal_records(passed_filter);
CREATE INDEX IF NOT EXISTS idx_murphy_signals_result ON murphy_signal_records(final_result);
CREATE INDEX IF NOT EXISTS idx_murphy_signals_active ON murphy_signal_records(final_result) WHERE final_result = 'active';

-- View for quick session stats
CREATE OR REPLACE VIEW murphy_session_stats AS
SELECT
    s.id,
    s.symbol,
    s.started_at,
    s.ended_at,
    s.status,
    COUNT(sr.id) as total_signals,
    COUNT(sr.id) FILTER (WHERE sr.passed_filter = true) as displayed_signals,
    COUNT(sr.id) FILTER (WHERE sr.passed_filter = false) as filtered_signals,
    COUNT(sr.id) FILTER (WHERE sr.final_result = 'win') as wins,
    COUNT(sr.id) FILTER (WHERE sr.final_result = 'loss') as losses,
    CAST(ROUND(
        CAST(100.0 * COUNT(sr.id) FILTER (WHERE sr.final_result = 'win') /
        NULLIF(COUNT(sr.id) FILTER (WHERE sr.final_result IN ('win', 'loss')), 0) AS numeric),
        1
    ) AS numeric) as win_rate_pct,
    CAST(ROUND(CAST(AVG(sr.peak_gain_pct) FILTER (WHERE sr.peak_gain_pct IS NOT NULL) AS numeric), 2) AS numeric) as avg_peak_gain,
    CAST(ROUND(CAST(AVG(sr.max_heat_pct) FILTER (WHERE sr.max_heat_pct IS NOT NULL) AS numeric), 2) AS numeric) as avg_max_heat,
    CAST(ROUND(CAST(AVG(sr.final_pnl_pct) FILTER (WHERE sr.final_result IN ('win', 'loss')) AS numeric), 2) AS numeric) as avg_final_pnl,
    CAST(ROUND(CAST(AVG(sr.duration_seconds) FILTER (WHERE sr.duration_seconds IS NOT NULL) AS numeric), 0) AS numeric) as avg_duration_sec,
    CAST(ROUND(CAST(AVG(sr.grade) FILTER (WHERE sr.passed_filter = true) AS numeric), 1) AS numeric) as avg_grade_displayed,
    CAST(ROUND(CAST(AVG(sr.grade) FILTER (WHERE sr.passed_filter = false) AS numeric), 1) AS numeric) as avg_grade_filtered
FROM murphy_test_sessions s
LEFT JOIN murphy_signal_records sr ON s.id = sr.session_id
GROUP BY s.id, s.symbol, s.started_at, s.ended_at, s.status;

-- Comments
COMMENT ON TABLE murphy_test_sessions IS 'Test sessions for Murphy classifier optimization - tracks configuration and performance metrics';
COMMENT ON TABLE murphy_signal_records IS 'Records every signal Murphy generates with real-time heat/gain tracking';
COMMENT ON COLUMN murphy_signal_records.passed_filter IS 'TRUE if signal was displayed in UI, FALSE if filtered out';
COMMENT ON COLUMN murphy_signal_records.peak_gain_pct IS 'Maximum favorable price movement while signal was active';
COMMENT ON COLUMN murphy_signal_records.max_heat_pct IS 'Maximum adverse price movement (drawdown) while signal was active';
COMMENT ON COLUMN murphy_signal_records.bar_count_at_signal IS 'Number of bars when signal fired - signals with <20 bars marked as premature';
