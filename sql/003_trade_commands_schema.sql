-- Trade Commands System Schema
-- Stores all /trade commands, aliases, natural language phrases, and controller mappings

-- Main table for all trade commands
CREATE TABLE IF NOT EXISTS trade_commands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  command TEXT NOT NULL UNIQUE,                   -- e.g. '/trade flatten'
  category TEXT NOT NULL,                         -- e.g. 'position_management', 'entry', 'exit'
  description TEXT,                               -- explanation for help UI
  is_ai_assisted BOOLEAN DEFAULT false,           -- true for smart commands
  is_implemented BOOLEAN DEFAULT false,           -- true if backend exists
  handler_function TEXT,                          -- Python function name to call
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Aliases for each command
CREATE TABLE IF NOT EXISTS trade_aliases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  command_id UUID REFERENCES trade_commands(id) ON DELETE CASCADE,
  alias TEXT NOT NULL,                            -- e.g. 'close', 'exit', 'flat'
  is_primary BOOLEAN DEFAULT false,               -- flag one as the main alias
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (command_id, alias)
);

-- Natural language phrases mapped to a command
CREATE TABLE IF NOT EXISTS trade_phrases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  command_id UUID REFERENCES trade_commands(id) ON DELETE CASCADE,
  phrase TEXT NOT NULL,                           -- e.g. "get me out", "buy me 10 shares"
  confidence_score DECIMAL(3, 2) DEFAULT 1.0,     -- 0.0 to 1.0 for fuzzy matching
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (command_id, phrase)
);

-- Tags for filtering/UX (e.g. "flatten", "safe", "entry")
CREATE TABLE IF NOT EXISTS trade_tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  command_id UUID REFERENCES trade_commands(id) ON DELETE CASCADE,
  tag TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (command_id, tag)
);

-- Controller (gamepad) button mappings
CREATE TABLE IF NOT EXISTS controller_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  button TEXT NOT NULL,                           -- e.g. 'LT', 'RB', 'X', 'A'
  action_label TEXT NOT NULL,                     -- e.g. 'spray_buy', 'reverse'
  command_id UUID REFERENCES trade_commands(id),
  mode TEXT DEFAULT 'default',                    -- 'spray', 'single', 'toggle', 'ai'
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE (button, mode)
);

-- Session state tracking (for AI assist toggle, etc)
CREATE TABLE IF NOT EXISTS session_state (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT NOT NULL UNIQUE,
  user_id UUID,                                   -- nullable for now
  ai_assist_enabled BOOLEAN DEFAULT false,
  last_button_pressed TEXT,
  last_trade_command UUID REFERENCES trade_commands(id),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_trade_aliases_command ON trade_aliases(command_id);
CREATE INDEX IF NOT EXISTS idx_trade_phrases_command ON trade_phrases(command_id);
CREATE INDEX IF NOT EXISTS idx_trade_tags_command ON trade_tags(command_id);
CREATE INDEX IF NOT EXISTS idx_controller_mappings_button ON controller_mappings(button);
CREATE INDEX IF NOT EXISTS idx_session_state_session ON session_state(session_id);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_trade_commands_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_trade_commands_updated_at_trigger
BEFORE UPDATE ON trade_commands
FOR EACH ROW EXECUTE FUNCTION update_trade_commands_updated_at();

CREATE TRIGGER update_session_state_updated_at_trigger
BEFORE UPDATE ON session_state
FOR EACH ROW EXECUTE FUNCTION update_trade_commands_updated_at();

COMMENT ON TABLE trade_commands IS 'Registry of all /trade commands with metadata';
COMMENT ON TABLE trade_aliases IS 'Alternative command names (e.g. flat, close, exit for flatten)';
COMMENT ON TABLE trade_phrases IS 'Natural language phrases mapped to commands';
COMMENT ON TABLE controller_mappings IS 'Xbox/gamepad button to command mappings';
COMMENT ON TABLE session_state IS 'User session state (AI assist toggle, last command, etc)';
