-- Add missing simple command aliases
-- These allow typing "price", "position", "volume", "range" without /trade prefix

-- Insert aliases linking to existing commands
INSERT INTO trade_aliases (alias, command_id, description)
SELECT 'price', id, 'Get current price'
FROM trade_commands WHERE command = '/trade price'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO trade_aliases (alias, command_id, description)
SELECT 'position', id, 'Show current position'
FROM trade_commands WHERE command = '/trade position'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO trade_aliases (alias, command_id, description)
SELECT 'volume', id, 'Get current volume'
FROM trade_commands WHERE command = '/trade volume'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO trade_aliases (alias, command_id, description)
SELECT 'range', id, 'Get price range'
FROM trade_commands WHERE command = '/trade range'
ON CONFLICT (alias) DO NOTHING;
