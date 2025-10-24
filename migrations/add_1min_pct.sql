-- Add 1-minute percentage and baseline price to symbol_state
-- This allows tracking % moves from 1 minute ago

ALTER TABLE symbol_state
ADD COLUMN IF NOT EXISTS min_1_price DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS pct_from_1min DECIMAL(10, 4);

-- Create index for querying by 1min percentage
CREATE INDEX IF NOT EXISTS idx_symbol_state_pct_1min ON symbol_state(pct_from_1min);

-- Comments
COMMENT ON COLUMN symbol_state.min_1_price IS 'Price snapshot from 1 minute ago';
COMMENT ON COLUMN symbol_state.pct_from_1min IS 'Percentage change from 1 minute ago';
