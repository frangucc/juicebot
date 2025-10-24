#!/usr/bin/env python3
"""
Backfill pre-market open prices using earliest alert from screener_alerts table.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from shared.database import supabase
from dotenv import load_dotenv

load_dotenv()

def backfill_from_alerts():
    """Backfill pre_market_open using earliest trigger_price from screener_alerts."""
    print("=" * 80)
    print("BACKFILL PRE-MARKET OPEN FROM SCREENER ALERTS")
    print("=" * 80)
    print()

    # Get all alerts from today using raw SQL to bypass Supabase limit
    print("Fetching all pre-market alerts (before 8:30 AM CST)...")
    import psycopg2
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    # Get alerts before 8:30 AM CST (13:30 UTC)
    cursor.execute("""
        SELECT DISTINCT ON (symbol) symbol, trigger_price
        FROM screener_alerts
        WHERE trigger_time < (CURRENT_DATE + INTERVAL '13 hours 30 minutes')
        ORDER BY symbol, trigger_time ASC
    """)

    alerts = [{'symbol': row[0], 'trigger_price': row[1]} for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    if not alerts:
        print("⚠️  No alerts found")
        return

    print(f"Found {len(alerts)} symbols with pre-market prices")

    # Find earliest price for each symbol
    earliest_by_symbol = {}
    for alert in alerts:
        symbol = alert['symbol']
        price = float(alert['trigger_price'])
        if symbol not in earliest_by_symbol or price < earliest_by_symbol[symbol]:
            earliest_by_symbol[symbol] = price

    print(f"Processing {len(earliest_by_symbol)} unique symbols")
    print()

    # Get all symbol states
    states_response = supabase.table("symbol_state").select("symbol,current_price,pre_market_open").execute()
    states = {s['symbol']: s for s in states_response.data}

    # Prepare updates
    updates = []
    for symbol, earliest_price in earliest_by_symbol.items():
        if symbol in states:
            state = states[symbol]
            # Only update if pre_market_open is NULL or 0
            if state.get('pre_market_open') is None or state.get('pre_market_open') == 0:
                current_price = state['current_price']
                pct_from_pre = ((current_price - earliest_price) / earliest_price) * 100

                updates.append({
                    'symbol': symbol,
                    'pre_market_open': earliest_price,
                    'pct_from_pre': pct_from_pre
                })

    if not updates:
        print("⚠️  No symbols need updating")
        return

    print(f"Updating {len(updates)} symbols...")

    # Update one by one using RPC or direct SQL
    print("Updating symbols...")
    import psycopg2
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    for update in updates:
        cursor.execute("""
            UPDATE symbol_state
            SET pre_market_open = %s,
                pct_from_pre = %s
            WHERE symbol = %s
        """, (update['pre_market_open'], update['pct_from_pre'], update['symbol']))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"  Completed!")

    print()
    print(f"✅ Updated {len(updates)} symbols with pre-market open prices")
    print()

    # Show sample updates
    print("Sample updates (first 20):")
    for update in updates[:20]:
        print(f"  {update['symbol']}: pre_open=${update['pre_market_open']:.4f}, %pre={update['pct_from_pre']:+.2f}%")

    print()
    print("=" * 80)
    print("🎉 Backfill complete!")
    print("=" * 80)

if __name__ == "__main__":
    backfill_from_alerts()
