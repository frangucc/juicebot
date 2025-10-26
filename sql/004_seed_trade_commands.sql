-- Seed data for trade commands system
-- Populates commands, aliases, natural language phrases, and controller mappings

-- ============================================================================
-- TRADE COMMANDS
-- ============================================================================

-- Position Management Commands
INSERT INTO trade_commands (command, category, description, is_ai_assisted, is_implemented, handler_function) VALUES
('/trade flatten', 'position_management', 'Immediately closes all positions at market price', false, false, 'flatten_position'),
('/trade flatten-smart', 'position_management', 'AI-assisted flatten with limit orders and timing', true, false, 'flatten_position_smart'),
('/trade close', 'position_management', 'Alias for flatten - closes all positions', false, true, 'close_position'),
('/trade position', 'position_inquiry', 'Shows current position with P&L', false, true, 'get_position_status'),
('/trade reset', 'session_management', 'Clears session P&L and starts fresh', false, false, 'reset_session_pnl');

-- Entry Commands
INSERT INTO trade_commands (command, category, description, is_ai_assisted, is_implemented, handler_function) VALUES
('/trade long', 'entry', 'Opens long position at market or specified price', false, true, 'open_long_position'),
('/trade short', 'entry', 'Opens short position at market or specified price', false, true, 'open_short_position'),
('/trade accumulate', 'gradual_entry', 'Gradually builds position over time (scale in)', false, false, 'accumulate_position'),
('/trade legin', 'gradual_entry', 'Alias for accumulate - legs into position', false, false, 'accumulate_position');

-- Exit Commands  
INSERT INTO trade_commands (command, category, description, is_ai_assisted, is_implemented, handler_function) VALUES
('/trade scaleout', 'gradual_exit', 'Gradually exits position in chunks', false, false, 'scale_out_position'),
('/trade legout', 'gradual_exit', 'Alias for scaleout - legs out of position', false, false, 'scale_out_position');

-- Reversal Commands
INSERT INTO trade_commands (command, category, description, is_ai_assisted, is_implemented, handler_function) VALUES
('/trade reverse', 'reversal', 'Instantly flips position (long to short or vice versa)', false, false, 'reverse_position'),
('/trade reverse-smart', 'reversal', 'AI-assisted reversal with safety checks', true, false, 'reverse_position_smart'),
('/trade safereverse', 'reversal', 'Alias for reverse-smart', true, false, 'reverse_position_smart');

-- Risk Management
INSERT INTO trade_commands (command, category, description, is_ai_assisted, is_implemented, handler_function) VALUES
('/trade stop', 'risk_management', 'Sets stop loss for current position', false, false, 'set_stop_loss'),
('/trade stoploss', 'risk_management', 'Alias for stop', false, false, 'set_stop_loss'),
('/trade bracket', 'risk_management', 'Creates bracket order (entry + stop + target)', false, false, 'create_bracket_order');

-- Market Data
INSERT INTO trade_commands (command, category, description, is_ai_assisted, is_implemented, handler_function) VALUES
('/trade price', 'market_data', 'Gets current price', false, true, 'get_current_price'),
('/trade volume', 'market_data', 'Gets current volume', false, true, 'get_current_volume'),
('/trade range', 'market_data', 'Gets today''s high/low range', false, true, 'get_price_range');

-- ============================================================================
-- TRADE ALIASES
-- ============================================================================

-- Flatten aliases
INSERT INTO trade_aliases (command_id, alias, is_primary) 
SELECT id, 'flat', true FROM trade_commands WHERE command = '/trade flatten';

INSERT INTO trade_aliases (command_id, alias, is_primary) 
SELECT id, alias, false FROM trade_commands WHERE command = '/trade flatten'
CROSS JOIN (VALUES ('exit'), ('close'), ('closeposition'), ('exitposition'), ('sell all')) AS t(alias);

-- Flatten-smart aliases
INSERT INTO trade_aliases (command_id, alias, is_primary) 
SELECT id, alias, false FROM trade_commands WHERE command = '/trade flatten-smart'
CROSS JOIN (VALUES ('flatassist'), ('flat ai'), ('flatten-ai'), ('smart exit')) AS t(alias);

-- Long aliases
INSERT INTO trade_aliases (command_id, alias, is_primary) 
SELECT id, 'buy', false FROM trade_commands WHERE command = '/trade long';

-- Short aliases
INSERT INTO trade_aliases (command_id, alias, is_primary) 
SELECT id, 'sell', false FROM trade_commands WHERE command = '/trade short';

-- Position aliases
INSERT INTO trade_aliases (command_id, alias, is_primary) 
SELECT id, alias, false FROM trade_commands WHERE command = '/trade position'
CROSS JOIN (VALUES ('pos'), ('positions'), ('status')) AS t(alias);

-- Reverse-smart aliases
INSERT INTO trade_aliases (command_id, alias, is_primary) 
SELECT id, alias, false FROM trade_commands WHERE command = '/trade reverse-smart'
CROSS JOIN (VALUES ('reverse-ai'), ('reverse safe'), ('smart reverse')) AS t(alias);

-- Stop aliases
INSERT INTO trade_aliases (command_id, alias, is_primary) 
SELECT id, 'sl', false FROM trade_commands WHERE command = '/trade stop';

-- Price aliases
INSERT INTO trade_aliases (command_id, alias, is_primary) 
SELECT id, alias, false FROM trade_commands WHERE command = '/trade price'
CROSS JOIN (VALUES ('last'), ('now'), ('current')) AS t(alias);

-- Volume alias
INSERT INTO trade_aliases (command_id, alias, is_primary) 
SELECT id, 'vol', false FROM trade_commands WHERE command = '/trade volume';

-- Range aliases
INSERT INTO trade_aliases (command_id, alias, is_primary) 
SELECT id, alias, false FROM trade_commands WHERE command = '/trade range'
CROSS JOIN (VALUES ('high'), ('low')) AS t(alias);

-- ============================================================================
-- NATURAL LANGUAGE PHRASES
-- ============================================================================

-- Flatten phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade flatten'
CROSS JOIN (VALUES 
  ('get me out'),
  ('sell everything'),
  ('close my trade'),
  ('exit my position'),
  ('flatten it'),
  ('liquidate'),
  ('take me out')
) AS t(phrase);

-- Flatten-smart phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade flatten-smart'
CROSS JOIN (VALUES 
  ('ease me out'),
  ('close me out smart'),
  ('exit gradually'),
  ('get out over time'),
  ('scale out smart'),
  ('trail me out')
) AS t(phrase);

-- Long phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade long'
CROSS JOIN (VALUES 
  ('buy me'),
  ('go long'),
  ('enter long'),
  ('open a long trade'),
  ('get in long'),
  ('take a long position'),
  ('i want to buy')
) AS t(phrase);

-- Short phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade short'
CROSS JOIN (VALUES 
  ('sell me'),
  ('go short'),
  ('enter short'),
  ('open a short'),
  ('i think it''s going down'),
  ('let''s short')
) AS t(phrase);

-- Position phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade position'
CROSS JOIN (VALUES 
  ('what''s my position'),
  ('show me my current trade'),
  ('do i have anything open'),
  ('am i long or short'),
  ('how much am i down'),
  ('tell me my pnl'),
  ('check positions'),
  ('where am i in the market')
) AS t(phrase);

-- Reverse phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade reverse'
CROSS JOIN (VALUES 
  ('reverse the trade'),
  ('flip my position'),
  ('go the other way'),
  ('turn this around'),
  ('flip to long'),
  ('flip to short')
) AS t(phrase);

-- Reverse-smart phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade reverse-smart'
CROSS JOIN (VALUES 
  ('reverse safely'),
  ('smart flip me'),
  ('wait and reverse if it''s smart'),
  ('flip if it makes sense')
) AS t(phrase);

-- Accumulate phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade accumulate'
CROSS JOIN (VALUES 
  ('leg me in slowly'),
  ('start building a position'),
  ('ease in'),
  ('scale in'),
  ('accumulate into dip'),
  ('start entering little by little')
) AS t(phrase);

-- Scaleout phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade scaleout'
CROSS JOIN (VALUES 
  ('take profits'),
  ('start selling some'),
  ('sell half'),
  ('scale out gradually'),
  ('sell in chunks'),
  ('partial exit')
) AS t(phrase);

-- Stop loss phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade stop'
CROSS JOIN (VALUES 
  ('add a stop loss'),
  ('set my stop'),
  ('protect this trade'),
  ('place a trailing stop'),
  ('put a stop below')
) AS t(phrase);

-- Bracket phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade bracket'
CROSS JOIN (VALUES 
  ('bracket this trade'),
  ('give me a tp and sl'),
  ('full risk management'),
  ('build me a bracket')
) AS t(phrase);

-- Price phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade price'
CROSS JOIN (VALUES 
  ('what''s the price'),
  ('show me current price'),
  ('where''s it trading')
) AS t(phrase);

-- Volume phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade volume'
CROSS JOIN (VALUES 
  ('how''s volume'),
  ('what''s the volume'),
  ('show me volume')
) AS t(phrase);

-- Range phrases
INSERT INTO trade_phrases (command_id, phrase, confidence_score)
SELECT id, phrase, 1.0 FROM trade_commands WHERE command = '/trade range'
CROSS JOIN (VALUES 
  ('is it high or low today'),
  ('where''s the range'),
  ('what''s today''s range'),
  ('show me high and low')
) AS t(phrase);

-- ============================================================================
-- CONTROLLER MAPPINGS (Xbox Gamepad)
-- ============================================================================

-- LT = Spray buy (rapid-fire long entries)
INSERT INTO controller_mappings (button, action_label, command_id, mode, description)
SELECT 'LT', 'spray_buy', id, 'spray', 'Rapid-fire market buys (1 unit per hold)'
FROM trade_commands WHERE command = '/trade long';

-- LB = Single buy
INSERT INTO controller_mappings (button, action_label, command_id, mode, description)
SELECT 'LB', 'buy', id, 'single', 'Buys 1 unit per click'
FROM trade_commands WHERE command = '/trade long';

-- RT = Spray sell (rapid-fire short entries)
INSERT INTO controller_mappings (button, action_label, command_id, mode, description)
SELECT 'RT', 'spray_sell', id, 'spray', 'Rapid-fire market sells (1 unit per hold)'
FROM trade_commands WHERE command = '/trade short';

-- RB = Single sell
INSERT INTO controller_mappings (button, action_label, command_id, mode, description)
SELECT 'RB', 'sell', id, 'single', 'Sells 1 unit per click'
FROM trade_commands WHERE command = '/trade short';

-- Y = Flatten
INSERT INTO controller_mappings (button, action_label, command_id, mode, description)
SELECT 'Y', 'flatten', id, 'default', 'Instant position close'
FROM trade_commands WHERE command = '/trade flatten';

-- X = Reverse
INSERT INTO controller_mappings (button, action_label, command_id, mode, description)
SELECT 'X', 'reverse', id, 'default', 'Instant reversal of position'
FROM trade_commands WHERE command = '/trade reverse';

-- B = Position status
INSERT INTO controller_mappings (button, action_label, command_id, mode, description)
SELECT 'B', 'status', id, 'default', 'Shows current position & P&L'
FROM trade_commands WHERE command = '/trade position';

-- A = Smart stop loss
INSERT INTO controller_mappings (button, action_label, command_id, mode, description)
SELECT 'A', 'smart_stop', id, 'ai', 'Adds AI-generated stop-loss'
FROM trade_commands WHERE command = '/trade stop';

-- View = Toggle AI assist
INSERT INTO controller_mappings (button, action_label, command_id, mode, description)
VALUES ('View', 'toggle_ai_assist', NULL, 'toggle', 'Turns AI assist mode on or off');

-- Menu = Smart flatten (eject)
INSERT INTO controller_mappings (button, action_label, command_id, mode, description)
SELECT 'Menu', 'flatten_smart', id, 'eject', 'Smart flatten over time'
FROM trade_commands WHERE command = '/trade flatten-smart';

-- ============================================================================
-- TAGS
-- ============================================================================

INSERT INTO trade_tags (command_id, tag)
SELECT id, tag FROM trade_commands 
CROSS JOIN (
  SELECT '/trade flatten' as cmd, 'instant' as tag UNION ALL
  SELECT '/trade flatten', 'exit' UNION ALL
  SELECT '/trade flatten-smart', 'safe' UNION ALL
  SELECT '/trade flatten-smart', 'ai' UNION ALL
  SELECT '/trade flatten-smart', 'exit' UNION ALL
  SELECT '/trade long', 'entry' UNION ALL
  SELECT '/trade short', 'entry' UNION ALL
  SELECT '/trade reverse', 'instant' UNION ALL
  SELECT '/trade reverse', 'flip' UNION ALL
  SELECT '/trade reverse-smart', 'safe' UNION ALL
  SELECT '/trade reverse-smart', 'ai' UNION ALL
  SELECT '/trade accumulate', 'gradual' UNION ALL
  SELECT '/trade scaleout', 'gradual'
) AS t WHERE trade_commands.command = t.cmd;
