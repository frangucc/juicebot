-- Murphy Test Sessions Schema
-- Records all signals (filtered and unfiltered) with multi-timeframe evaluation

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
        "correct_displayed": 0,
        "correct_filtered": 0,
        "accuracy_displayed": 0,
        "accuracy_filtered": 0,
        "avg_grade_displayed": 0,
        "avg_grade_filtered": 0
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
    price FLOAT NOT NULL,

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

    -- Price evaluation at multiple timeframes
    eval_2min JSONB, -- {price, change_pct, correct, evaluated_at}
    eval_5min JSONB,
    eval_10min JSONB,
    eval_30min JSONB,

    -- Final evaluation summary
    final_result TEXT, -- 'correct', 'wrong', 'pending', 'neutral'

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
    COUNT(sr.id) FILTER (WHERE sr.passed_filter = true AND sr.final_result = 'correct') as correct_displayed,
    COUNT(sr.id) FILTER (WHERE sr.passed_filter = false AND sr.final_result = 'correct') as correct_filtered,
    ROUND(
        100.0 * COUNT(sr.id) FILTER (WHERE sr.passed_filter = true AND sr.final_result = 'correct') /
        NULLIF(COUNT(sr.id) FILTER (WHERE sr.passed_filter = true AND sr.final_result IN ('correct', 'wrong')), 0),
        1
    ) as accuracy_displayed_pct,
    ROUND(
        100.0 * COUNT(sr.id) FILTER (WHERE sr.passed_filter = false AND sr.final_result = 'correct') /
        NULLIF(COUNT(sr.id) FILTER (WHERE sr.passed_filter = false AND sr.final_result IN ('correct', 'wrong')), 0),
        1
    ) as accuracy_filtered_pct,
    ROUND(AVG(sr.grade) FILTER (WHERE sr.passed_filter = true), 1) as avg_grade_displayed,
    ROUND(AVG(sr.grade) FILTER (WHERE sr.passed_filter = false), 1) as avg_grade_filtered
FROM murphy_test_sessions s
LEFT JOIN murphy_signal_records sr ON s.id = sr.session_id
GROUP BY s.id, s.symbol, s.started_at, s.ended_at, s.status;

-- Comments
COMMENT ON TABLE murphy_test_sessions IS 'Test sessions for Murphy classifier optimization - tracks configuration and performance metrics';
COMMENT ON TABLE murphy_signal_records IS 'Records every signal Murphy generates (filtered and displayed) with multi-timeframe evaluation';
COMMENT ON COLUMN murphy_signal_records.passed_filter IS 'TRUE if signal was displayed in UI, FALSE if filtered out';
COMMENT ON COLUMN murphy_signal_records.filter_reason IS 'Explanation of why signal was filtered (e.g., "below threshold: ** [6]", "weaker same direction")';
