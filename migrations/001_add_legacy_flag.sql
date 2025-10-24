-- Migration: Add legacy flag for MBP-1 to TRADES transition
-- Date: 2025-10-24
-- Description: Mark existing bars as legacy before switching to TRADES schema

BEGIN;

-- Add columns if they don't exist
ALTER TABLE price_bars
    ADD COLUMN IF NOT EXISTS is_legacy BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS data_source VARCHAR(20) DEFAULT 'mbp-1',
    ADD COLUMN IF NOT EXISTS migrated_at TIMESTAMP DEFAULT NOW();

-- Mark all existing data as legacy from MBP-1
UPDATE price_bars
SET
    is_legacy = true,
    data_source = 'mbp-1',
    migrated_at = NOW()
WHERE is_legacy IS NULL OR is_legacy = false;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_price_bars_legacy ON price_bars(is_legacy);
CREATE INDEX IF NOT EXISTS idx_price_bars_source ON price_bars(data_source);
CREATE INDEX IF NOT EXISTS idx_price_bars_timestamp_legacy ON price_bars(timestamp, is_legacy);

-- Add comments
COMMENT ON COLUMN price_bars.is_legacy IS 'true = old MBP-1 data (volume=0), false = new TRADES data (real volume)';
COMMENT ON COLUMN price_bars.data_source IS 'mbp-1 = quotes, trades = executions';

-- Print summary
DO $$
DECLARE
    legacy_count INTEGER;
    new_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO legacy_count FROM price_bars WHERE is_legacy = true;
    SELECT COUNT(*) INTO new_count FROM price_bars WHERE is_legacy = false;

    RAISE NOTICE 'Migration complete!';
    RAISE NOTICE 'Legacy bars (MBP-1): %', legacy_count;
    RAISE NOTICE 'New bars (TRADES): %', new_count;
END $$;

COMMIT;
