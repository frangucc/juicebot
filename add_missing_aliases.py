"""
Add missing critical aliases for trade commands
"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from shared.database import supabase

def add_missing_aliases():
    """Add critical missing aliases"""

    # First, get command_id mapping
    commands = supabase.table('trade_commands').select('id, command').execute()
    command_map = {cmd['command']: cmd['id'] for cmd in commands.data}

    # Define missing aliases
    missing_aliases = [
        # Entry commands
        ('/trade long', ['long', 'golong', 'buy']),
        ('/trade short', ['short', 'goshort', 'sell']),

        # Market data
        ('/trade price', ['price', 'last', 'current', 'now', 'quote']),
        ('/trade position', ['position']),  # Already has 'pos'
        ('/trade volume', ['volume', 'vol']),
        ('/trade range', ['range', 'high', 'low']),

        # Position management (add more variations)
        ('/trade accumulate', ['add', 'addto', 'increase']),
        ('/trade scaleout', ['scaleout', 'scale', 'reduce']),
        ('/trade reverse', ['reverse', 'flip', 'switch']),
    ]

    added_count = 0
    skipped_count = 0

    for command, aliases in missing_aliases:
        command_id = command_map.get(command)

        if not command_id:
            print(f"⚠️  Command not found: {command}")
            continue

        for alias in aliases:
            # Check if alias already exists
            existing = supabase.table('trade_aliases').select('*').eq('alias', alias).execute()

            if existing.data:
                print(f"⏭️  Skipping '{alias}' (already exists)")
                skipped_count += 1
                continue

            # Add alias
            supabase.table('trade_aliases').insert({
                'command_id': command_id,
                'alias': alias,
                'is_primary': alias in ['long', 'short', 'price', 'position', 'volume', 'range']
            }).execute()

            print(f"✅ Added alias: '{alias}' → {command}")
            added_count += 1

    print(f"\n{'=' * 50}")
    print(f"✓ Added {added_count} new aliases")
    print(f"⏭️  Skipped {skipped_count} existing aliases")
    print(f"{'=' * 50}")

if __name__ == '__main__':
    add_missing_aliases()
