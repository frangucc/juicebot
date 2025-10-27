-- Add bar_count tracking to symbol_state

ALTER TABLE symbol_state
ADD COLUMN IF NOT EXISTS bar_count INTEGER DEFAULT 0;

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_symbol_state_bar_count
ON symbol_state(symbol, bar_count);
