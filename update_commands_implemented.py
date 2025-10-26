#!/usr/bin/env python3
"""
Update all trade commands to mark them as implemented.
"""

import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from shared.database import supabase

load_dotenv()

def update_all_commands_to_implemented():
    """Mark all commands as implemented in database."""

    # Get all commands
    result = supabase.table('trade_commands').select('id, command, is_implemented').execute()

    print(f"Found {len(result.data)} commands")

    # Update each to is_implemented = True
    updated = 0
    for cmd in result.data:
        if not cmd['is_implemented']:
            supabase.table('trade_commands').update({
                'is_implemented': True
            }).eq('id', cmd['id']).execute()

            print(f"✓ Marked {cmd['command']} as implemented")
            updated += 1
        else:
            print(f"→ {cmd['command']} already implemented")

    print(f"\n✅ Updated {updated} commands to implemented status")

if __name__ == '__main__':
    update_all_commands_to_implemented()
