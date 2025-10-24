-- Migration: Add session-specific baseline columns to symbol_state table
-- Date: 2025-10-24
-- Purpose: Track pre-market, RTH, and post-market baselines separately

-- Add baseline price columns
ALTER TABLE symbol_state
ADD COLUMN IF NOT EXISTS pre_market_open DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS rth_open DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS post_market_open DECIMAL(10, 4);

-- Add percentage move columns
ALTER TABLE symbol_state
ADD COLUMN IF NOT EXISTS pct_from_pre DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS pct_from_post DECIMAL(10, 4);

-- Add index on new columns for faster filtering
CREATE INDEX IF NOT EXISTS idx_symbol_state_pct_from_pre ON symbol_state(pct_from_pre);
CREATE INDEX IF NOT EXISTS idx_symbol_state_pct_from_post ON symbol_state(pct_from_post);

-- Add comment for documentation
COMMENT ON COLUMN symbol_state.pre_market_open IS 'First trade price captured in pre-market session (3:00-8:30 AM CST)';
COMMENT ON COLUMN symbol_state.rth_open IS 'First trade price captured in regular trading hours (8:30 AM-3:00 PM CST)';
COMMENT ON COLUMN symbol_state.post_market_open IS 'First trade price captured in post-market session (3:00-7:00 PM CST)';
COMMENT ON COLUMN symbol_state.pct_from_pre IS 'Percentage move from pre-market open baseline';
COMMENT ON COLUMN symbol_state.pct_from_post IS 'Percentage move from post-market open baseline';
