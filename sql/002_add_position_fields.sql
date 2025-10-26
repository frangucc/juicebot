-- Add position tracking fields to trades table
-- These fields support the position tracking system

-- Add 'side' field (long/short)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS side VARCHAR(10);

-- Add 'quantity' field (alias for shares)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS quantity INTEGER;

-- Add 'entry_value' field (quantity * entry_price)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS entry_value DECIMAL(12, 2);

-- Add 'realized_pnl' field (cumulative P&L from previous trades)
ALTER TABLE trades ADD COLUMN IF NOT EXISTS realized_pnl DECIMAL(12, 2) DEFAULT 0.0;

-- Update existing trades: set quantity from shares, calculate entry_value
UPDATE trades
SET quantity = shares,
    entry_value = shares * entry_price
WHERE quantity IS NULL AND shares IS NOT NULL;

-- Create index on side for quick filtering
CREATE INDEX IF NOT EXISTS idx_trades_side ON trades(side);

-- Add 'open' as a valid status
-- Update status enum or just use existing status field
COMMENT ON COLUMN trades.status IS 'Status: pending, entered, monitoring, exited, open, closed';
