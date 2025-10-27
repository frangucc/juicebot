-- Multi-Timeframe Evaluation System
-- Adds bar-based evaluation columns to track signal accuracy at 5, 10, 20, 50 bars

-- Add multi-timeframe evaluation columns
ALTER TABLE murphy_signal_records
ADD COLUMN IF NOT EXISTS bars_elapsed INTEGER DEFAULT 0,

-- 5 bar evaluation
ADD COLUMN IF NOT EXISTS price_at_5_bars FLOAT,
ADD COLUMN IF NOT EXISTS pnl_at_5_bars FLOAT,
ADD COLUMN IF NOT EXISTS result_5_bars TEXT,  -- 'correct', 'wrong', 'neutral', 'pending'

-- 10 bar evaluation
ADD COLUMN IF NOT EXISTS price_at_10_bars FLOAT,
ADD COLUMN IF NOT EXISTS pnl_at_10_bars FLOAT,
ADD COLUMN IF NOT EXISTS result_10_bars TEXT,

-- 20 bar evaluation
ADD COLUMN IF NOT EXISTS price_at_20_bars FLOAT,
ADD COLUMN IF NOT EXISTS pnl_at_20_bars FLOAT,
ADD COLUMN IF NOT EXISTS result_20_bars TEXT,

-- 50 bar evaluation
ADD COLUMN IF NOT EXISTS price_at_50_bars FLOAT,
ADD COLUMN IF NOT EXISTS pnl_at_50_bars FLOAT,
ADD COLUMN IF NOT EXISTS result_50_bars TEXT,

-- Add index for bars_elapsed for efficient queries
ADD COLUMN IF NOT EXISTS evaluated_at_5_bars TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS evaluated_at_10_bars TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS evaluated_at_20_bars TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS evaluated_at_50_bars TIMESTAMP WITH TIME ZONE;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_murphy_signals_bars_elapsed
ON murphy_signal_records(bars_elapsed)
WHERE final_result IN ('active', 'premature');

-- View for signal performance by timeframe
CREATE OR REPLACE VIEW murphy_multiframe_performance AS
SELECT
    session_id,
    direction,
    stars,
    grade,
    passed_filter,

    -- 5 bar stats
    COUNT(CASE WHEN result_5_bars = 'correct' THEN 1 END) as correct_5_bars,
    COUNT(CASE WHEN result_5_bars IS NOT NULL THEN 1 END) as total_5_bars,
    CAST(ROUND(CAST(
        COUNT(CASE WHEN result_5_bars = 'correct' THEN 1 END)::numeric /
        NULLIF(COUNT(CASE WHEN result_5_bars IS NOT NULL THEN 1 END), 0) * 100
    AS numeric), 1) AS numeric) as accuracy_5_bars,

    -- 10 bar stats
    COUNT(CASE WHEN result_10_bars = 'correct' THEN 1 END) as correct_10_bars,
    COUNT(CASE WHEN result_10_bars IS NOT NULL THEN 1 END) as total_10_bars,
    CAST(ROUND(CAST(
        COUNT(CASE WHEN result_10_bars = 'correct' THEN 1 END)::numeric /
        NULLIF(COUNT(CASE WHEN result_10_bars IS NOT NULL THEN 1 END), 0) * 100
    AS numeric), 1) AS numeric) as accuracy_10_bars,

    -- 20 bar stats
    COUNT(CASE WHEN result_20_bars = 'correct' THEN 1 END) as correct_20_bars,
    COUNT(CASE WHEN result_20_bars IS NOT NULL THEN 1 END) as total_20_bars,
    CAST(ROUND(CAST(
        COUNT(CASE WHEN result_20_bars = 'correct' THEN 1 END)::numeric /
        NULLIF(COUNT(CASE WHEN result_20_bars IS NOT NULL THEN 1 END), 0) * 100
    AS numeric), 1) AS numeric) as accuracy_20_bars,

    -- 50 bar stats
    COUNT(CASE WHEN result_50_bars = 'correct' THEN 1 END) as correct_50_bars,
    COUNT(CASE WHEN result_50_bars IS NOT NULL THEN 1 END) as total_50_bars,
    CAST(ROUND(CAST(
        COUNT(CASE WHEN result_50_bars = 'correct' THEN 1 END)::numeric /
        NULLIF(COUNT(CASE WHEN result_50_bars IS NOT NULL THEN 1 END), 0) * 100
    AS numeric), 1) AS numeric) as accuracy_50_bars,

    -- Average P/L by timeframe
    CAST(ROUND(CAST(AVG(pnl_at_5_bars) AS numeric), 2) AS numeric) as avg_pnl_5_bars,
    CAST(ROUND(CAST(AVG(pnl_at_10_bars) AS numeric), 2) AS numeric) as avg_pnl_10_bars,
    CAST(ROUND(CAST(AVG(pnl_at_20_bars) AS numeric), 2) AS numeric) as avg_pnl_20_bars,
    CAST(ROUND(CAST(AVG(pnl_at_50_bars) AS numeric), 2) AS numeric) as avg_pnl_50_bars

FROM murphy_signal_records
GROUP BY session_id, direction, stars, grade, passed_filter;

-- View for "early but right" analysis
CREATE OR REPLACE VIEW murphy_early_signals AS
SELECT
    id,
    symbol,
    direction,
    stars,
    grade,
    entry_price,
    timestamp,
    passed_filter,

    -- Show progression
    result_5_bars as r5,
    result_10_bars as r10,
    result_20_bars as r20,
    result_50_bars as r50,

    -- Identify "early but right" signals
    CASE
        WHEN result_5_bars = 'wrong' AND result_20_bars = 'correct' THEN 'early_but_right'
        WHEN result_10_bars = 'wrong' AND result_50_bars = 'correct' THEN 'very_early_but_right'
        WHEN result_5_bars = 'correct' AND result_20_bars = 'wrong' THEN 'quick_win_then_failed'
        ELSE 'consistent'
    END as pattern,

    pnl_at_5_bars,
    pnl_at_10_bars,
    pnl_at_20_bars,
    pnl_at_50_bars

FROM murphy_signal_records
WHERE result_50_bars IS NOT NULL;

COMMENT ON VIEW murphy_early_signals IS 'Identifies signals that were wrong short-term but right long-term (or vice versa)';
