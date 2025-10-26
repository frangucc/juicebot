import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from shared.database import supabase

# Get current open position
result = supabase.table('trades').select('*').eq('symbol', 'BYND').eq('status', 'open').order('entry_time', desc=True).limit(1).execute()

if result.data and len(result.data) > 0:
    pos = result.data[0]
    print(f"\n✅ CURRENT POSITION:")
    print(f"   Side: {pos['side'].upper()}")
    print(f"   Quantity: {pos['quantity']}")
    print(f"   Entry: ${pos['entry_price']:.2f}")
    print(f"   Entry Time: {pos['entry_time']}")
    print(f"   Realized P&L: ${pos.get('realized_pnl', 0):.2f}")
    print(f"   Status: {pos['status']}")
else:
    print("\n⚠️  NO OPEN POSITION")

# Show recent trades
all_trades = supabase.table('trades').select('*').eq('symbol', 'BYND').order('entry_time', desc=True).limit(5).execute()
print(f"\n📊 RECENT TRADES (last 5):")
for t in all_trades.data:
    status_icon = "🟢" if t['status'] == 'open' else "⚪"
    print(f"   {status_icon} {t['side'].upper()} {t['quantity']} @ ${t['entry_price']:.2f} - {t['status']}")
