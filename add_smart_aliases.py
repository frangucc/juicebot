"""
Add even more smart aliases for natural trading commands
"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from shared.database import supabase

def add_smart_aliases():
    """Add smart aliases for natural language trading"""

    # Get command_id mapping
    commands = supabase.table('trade_commands').select('id, command').execute()
    command_map = {cmd['command']: cmd['id'] for cmd in commands.data}

    # Define new smart aliases
    new_aliases = [
        # Exit variations
        ('/trade flatten', ['out', 'exit', 'getout', 'done', 'close', 'closeall']),

        # Scale out variations
        ('/trade scaleout', ['sellsome', 'sellpart', 'partial', 'trim', 'lighten']),

        # Market data variations
        ('/trade price', ['p', 'px', 'where', 'wheresit', 'level']),
        ('/trade position', ['mypos', 'holding', 'whatdo ihave']),

        # Quick actions
        ('/trade long', ['l', 'buyit', 'getlong']),
        ('/trade short', ['s', 'shortit', 'getshort']),
    ]

    added_count = 0
    skipped_count = 0

    for command, aliases in new_aliases:
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
                'is_primary': False
            }).execute()

            print(f"✅ Added alias: '{alias}' → {command}")
            added_count += 1

    print(f"\n{'=' * 50}")
    print(f"✓ Added {added_count} new smart aliases")
    print(f"⏭️  Skipped {skipped_count} existing aliases")
    print(f"{'=' * 50}")

if __name__ == '__main__':
    add_smart_aliases()
