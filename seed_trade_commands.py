#!/usr/bin/env python3
"""
Seed trade commands, aliases, phrases, and controller mappings to Supabase.
"""

import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from shared.database import supabase

load_dotenv()

def seed_commands():
    """Seed all trade commands."""
    commands = [
        # Position Management
        {
            'command': '/trade flatten',
            'category': 'position_management',
            'description': 'Immediately closes all positions at market price',
            'is_ai_assisted': False,
            'is_implemented': False,
            'handler_function': 'flatten_position'
        },
        {
            'command': '/trade flatten-smart',
            'category': 'position_management',
            'description': 'AI-assisted flatten with limit orders and timing',
            'is_ai_assisted': True,
            'is_implemented': False,
            'handler_function': 'flatten_position_smart'
        },
        {
            'command': '/trade close',
            'category': 'position_management',
            'description': 'Alias for flatten - closes all positions',
            'is_ai_assisted': False,
            'is_implemented': True,
            'handler_function': 'close_position'
        },
        {
            'command': '/trade position',
            'category': 'position_inquiry',
            'description': 'Shows current position with P&L',
            'is_ai_assisted': False,
            'is_implemented': True,
            'handler_function': 'get_position_status'
        },
        {
            'command': '/trade reset',
            'category': 'session_management',
            'description': 'Clears session P&L and starts fresh',
            'is_ai_assisted': False,
            'is_implemented': False,
            'handler_function': 'reset_session_pnl'
        },
        # Entry
        {
            'command': '/trade long',
            'category': 'entry',
            'description': 'Opens long position at market or specified price',
            'is_ai_assisted': False,
            'is_implemented': True,
            'handler_function': 'open_long_position'
        },
        {
            'command': '/trade short',
            'category': 'entry',
            'description': 'Opens short position at market or specified price',
            'is_ai_assisted': False,
            'is_implemented': True,
            'handler_function': 'open_short_position'
        },
        {
            'command': '/trade accumulate',
            'category': 'gradual_entry',
            'description': 'Gradually builds position over time (scale in)',
            'is_ai_assisted': False,
            'is_implemented': False,
            'handler_function': 'accumulate_position'
        },
        # Exit
        {
            'command': '/trade scaleout',
            'category': 'gradual_exit',
            'description': 'Gradually exits position in chunks',
            'is_ai_assisted': False,
            'is_implemented': False,
            'handler_function': 'scale_out_position'
        },
        # Reversal
        {
            'command': '/trade reverse',
            'category': 'reversal',
            'description': 'Instantly flips position (long to short or vice versa)',
            'is_ai_assisted': False,
            'is_implemented': False,
            'handler_function': 'reverse_position'
        },
        {
            'command': '/trade reverse-smart',
            'category': 'reversal',
            'description': 'AI-assisted reversal with safety checks',
            'is_ai_assisted': True,
            'is_implemented': False,
            'handler_function': 'reverse_position_smart'
        },
        # Risk Management
        {
            'command': '/trade stop',
            'category': 'risk_management',
            'description': 'Sets stop loss for current position',
            'is_ai_assisted': False,
            'is_implemented': False,
            'handler_function': 'set_stop_loss'
        },
        {
            'command': '/trade bracket',
            'category': 'risk_management',
            'description': 'Creates bracket order (entry + stop + target)',
            'is_ai_assisted': False,
            'is_implemented': False,
            'handler_function': 'create_bracket_order'
        },
        # Market Data
        {
            'command': '/trade price',
            'category': 'market_data',
            'description': 'Gets current price',
            'is_ai_assisted': False,
            'is_implemented': True,
            'handler_function': 'get_current_price'
        },
        {
            'command': '/trade volume',
            'category': 'market_data',
            'description': 'Gets current volume',
            'is_ai_assisted': False,
            'is_implemented': True,
            'handler_function': 'get_current_volume'
        },
        {
            'command': '/trade range',
            'category': 'market_data',
            'description': 'Gets today''s high/low range',
            'is_ai_assisted': False,
            'is_implemented': True,
            'handler_function': 'get_price_range'
        },
    ]
    
    result = supabase.table('trade_commands').insert(commands).execute()
    print(f"✅ Inserted {len(result.data)} commands")
    return {cmd['command']: cmd['id'] for cmd in result.data}

def seed_aliases(command_map):
    """Seed command aliases."""
    aliases = [
        # Flatten
        ('/trade flatten', ['flat', 'exit', 'close', 'closeposition', 'exitposition', 'sell all']),
        # Flatten-smart
        ('/trade flatten-smart', ['flatassist', 'flat ai', 'flatten-ai', 'smart exit']),
        # Long
        ('/trade long', ['buy']),
        # Short
        ('/trade short', ['sell']),
        # Position
        ('/trade position', ['pos', 'positions', 'status']),
        # Reverse-smart
        ('/trade reverse-smart', ['reverse-ai', 'reverse safe', 'smart reverse', 'safereverse']),
        # Stop
        ('/trade stop', ['sl', 'stoploss']),
        # Price
        ('/trade price', ['last', 'now', 'current']),
        # Volume
        ('/trade volume', ['vol']),
        # Range
        ('/trade range', ['high', 'low']),
        # Accumulate
        ('/trade accumulate', ['legin']),
        # Scaleout
        ('/trade scaleout', ['legout']),
    ]
    
    alias_records = []
    for cmd, alias_list in aliases:
        cmd_id = command_map.get(cmd)
        if cmd_id:
            for alias in alias_list:
                alias_records.append({
                    'command_id': cmd_id,
                    'alias': alias,
                    'is_primary': alias == alias_list[0] if alias_list else False
                })
    
    result = supabase.table('trade_aliases').insert(alias_records).execute()
    print(f"✅ Inserted {len(result.data)} aliases")

def seed_phrases(command_map):
    """Seed natural language phrases."""
    phrases = [
        # Flatten
        ('/trade flatten', [
            'get me out', 'sell everything', 'close my trade', 'exit my position',
            'flatten it', 'liquidate', 'take me out'
        ]),
        # Flatten-smart
        ('/trade flatten-smart', [
            'ease me out', 'close me out smart', 'exit gradually',
            'get out over time', 'scale out smart', 'trail me out'
        ]),
        # Long
        ('/trade long', [
            'buy me', 'go long', 'enter long', 'open a long trade',
            'get in long', 'take a long position', 'i want to buy'
        ]),
        # Short
        ('/trade short', [
            'sell me', 'go short', 'enter short', 'open a short',
            'i think it''s going down', 'let''s short'
        ]),
        # Position
        ('/trade position', [
            'what''s my position', 'show me my current trade', 'do i have anything open',
            'am i long or short', 'how much am i down', 'tell me my pnl',
            'check positions', 'where am i in the market'
        ]),
        # Reverse
        ('/trade reverse', [
            'reverse the trade', 'flip my position', 'go the other way',
            'turn this around', 'flip to long', 'flip to short'
        ]),
        # Reverse-smart
        ('/trade reverse-smart', [
            'reverse safely', 'smart flip me',
            'wait and reverse if it''s smart', 'flip if it makes sense'
        ]),
        # Accumulate
        ('/trade accumulate', [
            'leg me in slowly', 'start building a position', 'ease in',
            'scale in', 'accumulate into dip', 'start entering little by little'
        ]),
        # Scaleout
        ('/trade scaleout', [
            'take profits', 'start selling some', 'sell half',
            'scale out gradually', 'sell in chunks', 'partial exit'
        ]),
        # Stop
        ('/trade stop', [
            'add a stop loss', 'set my stop', 'protect this trade',
            'place a trailing stop', 'put a stop below'
        ]),
        # Bracket
        ('/trade bracket', [
            'bracket this trade', 'give me a tp and sl',
            'full risk management', 'build me a bracket'
        ]),
        # Price
        ('/trade price', [
            'what''s the price', 'show me current price', 'where''s it trading'
        ]),
        # Volume
        ('/trade volume', [
            'how''s volume', 'what''s the volume', 'show me volume'
        ]),
        # Range
        ('/trade range', [
            'is it high or low today', 'where''s the range',
            'what''s today''s range', 'show me high and low'
        ]),
    ]
    
    phrase_records = []
    for cmd, phrase_list in phrases:
        cmd_id = command_map.get(cmd)
        if cmd_id:
            for phrase in phrase_list:
                phrase_records.append({
                    'command_id': cmd_id,
                    'phrase': phrase,
                    'confidence_score': 1.0
                })
    
    result = supabase.table('trade_phrases').insert(phrase_records).execute()
    print(f"✅ Inserted {len(result.data)} phrases")

def seed_controller_mappings(command_map):
    """Seed Xbox controller mappings."""
    mappings = [
        {'button': 'LT', 'action_label': 'spray_buy', 'command': '/trade long', 'mode': 'spray', 
         'description': 'Rapid-fire market buys (1 unit per hold)'},
        {'button': 'LB', 'action_label': 'buy', 'command': '/trade long', 'mode': 'single',
         'description': 'Buys 1 unit per click'},
        {'button': 'RT', 'action_label': 'spray_sell', 'command': '/trade short', 'mode': 'spray',
         'description': 'Rapid-fire market sells (1 unit per hold)'},
        {'button': 'RB', 'action_label': 'sell', 'command': '/trade short', 'mode': 'single',
         'description': 'Sells 1 unit per click'},
        {'button': 'Y', 'action_label': 'flatten', 'command': '/trade flatten', 'mode': 'default',
         'description': 'Instant position close'},
        {'button': 'X', 'action_label': 'reverse', 'command': '/trade reverse', 'mode': 'default',
         'description': 'Instant reversal of position'},
        {'button': 'B', 'action_label': 'status', 'command': '/trade position', 'mode': 'default',
         'description': 'Shows current position & P&L'},
        {'button': 'A', 'action_label': 'smart_stop', 'command': '/trade stop', 'mode': 'ai',
         'description': 'Adds AI-generated stop-loss'},
        {'button': 'View', 'action_label': 'toggle_ai_assist', 'command': None, 'mode': 'toggle',
         'description': 'Turns AI assist mode on or off'},
        {'button': 'Menu', 'action_label': 'flatten_smart', 'command': '/trade flatten-smart', 'mode': 'eject',
         'description': 'Smart flatten over time'},
    ]
    
    mapping_records = []
    for mapping in mappings:
        cmd_id = command_map.get(mapping['command']) if mapping['command'] else None
        mapping_records.append({
            'button': mapping['button'],
            'action_label': mapping['action_label'],
            'command_id': cmd_id,
            'mode': mapping['mode'],
            'description': mapping['description']
        })
    
    result = supabase.table('controller_mappings').insert(mapping_records).execute()
    print(f"✅ Inserted {len(result.data)} controller mappings")

if __name__ == '__main__':
    print("🌱 Seeding trade commands...")
    command_map = seed_commands()
    seed_aliases(command_map)
    seed_phrases(command_map)
    seed_controller_mappings(command_map)
    print("✅ All trade commands seeded successfully!")
