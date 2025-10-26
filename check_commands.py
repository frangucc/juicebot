import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from shared.database import supabase

# Check what commands/aliases we have
print("=== Commands ===")
cmds = supabase.table('trade_commands').select('command, is_implemented').order('command').execute()
for c in cmds.data:
    status = "✅" if c['is_implemented'] else "❌"
    print(f"{status} {c['command']}")

print("\n=== Aliases ===")
aliases = supabase.table('trade_aliases').select('alias, trade_commands(command)').limit(20).execute()
for a in aliases.data:
    print(f"  '{a['alias']}' → {a['trade_commands']['command']}")

print("\n=== Testing match for 'price' ===")
# Check if 'price' exists as alias
price_alias = supabase.table('trade_aliases').select('*,trade_commands(command)').eq('alias', 'price').execute()
print(f"Found {len(price_alias.data)} matches for alias 'price'")
if price_alias.data:
    print(f"  → {price_alias.data[0]['trade_commands']['command']}")

# Check if '/trade price' exists as command
price_cmd = supabase.table('trade_commands').select('*').eq('command', '/trade price').execute()
print(f"Found {len(price_cmd.data)} matches for command '/trade price'")
