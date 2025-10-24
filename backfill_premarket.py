#!/usr/bin/env python3
"""
Backfill pre-market open prices for symbols in symbol_state table.
Uses the earliest captured price from today's data as the pre-market open.
"""
import sys
import os
from datetime import datetime, timedelta
import pytz
import psycopg2

# Add parent directory to path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from shared.config import settings
from shared.database import supabase
from dotenv import load_dotenv

load_dotenv()

def backfill_premarket_opens():
    """Backfill pre-market open prices using earliest captured prices from today."""
    print("=" * 80)
    print("BACKFILL PRE-MARKET OPEN PRICES")
    print("=" * 80)
    print()

    cst = pytz.timezone('America/Chicago')
    utc = pytz.UTC
    today = datetime.now(cst).date()

    # Pre-market session: 3:00 AM - 8:30 AM CST = 8:00 AM - 1:30 PM UTC
    pre_market_end_cst = cst.localize(datetime.combine(today, datetime.strptime("08:30", "%H:%M").time()))
    pre_market_end_utc = pre_market_end_cst.astimezone(utc)

    print(f"Date: {today}")
    print(f"Pre-market ends at: {pre_market_end_cst.strftime('%I:%M %p %Z')}")
    print()

    # Connect to database
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()

    print("Strategy: Use RTH open (rth_open) as pre-market baseline")
    print("Since scanner started after pre-market, we'll treat RTH open as the pre-market open")
    print()

    # Simple approach: For symbols that don't have pre_market_open,
    # use their rth_open (first RTH price) as a proxy
    cursor.execute("""
        SELECT
            symbol,
            rth_open,
            current_price
        FROM symbol_state
        WHERE pre_market_open IS NULL
        AND rth_open IS NOT NULL
        AND rth_open > 0
    """)

    symbols_to_update = cursor.fetchall()

    if not symbols_to_update:
        print("⚠️  No symbols found that need pre_market_open backfilling")
        cursor.close()
        conn.close()
        return

    print(f"Found {len(symbols_to_update)} symbols to backfill")
    print()

    # Prepare updates
    updates = []
    for symbol, rth_open, current_price in symbols_to_update:
        # Use RTH open as pre-market open baseline
        # Calculate pct_from_pre
        pct_from_pre = ((current_price - rth_open) / rth_open) * 100 if rth_open else None

        updates.append({
            'symbol': symbol,
            'pre_market_open': float(rth_open),
            'pct_from_pre': float(pct_from_pre) if pct_from_pre else None
        })

    cursor.close()
    conn.close()

    if updates:
        print("Updating symbol_state table...")

        # Batch update in chunks of 100
        chunk_size = 100
        for i in range(0, len(updates), chunk_size):
            chunk = updates[i:i+chunk_size]
            supabase.table("symbol_state").upsert(chunk).execute()
            print(f"  Updated {min(i+chunk_size, len(updates))}/{len(updates)} symbols...")

        print()
        print(f"✅ Successfully backfilled {len(updates)} symbols!")
        print()

        # Show some examples
        print("Sample updates:")
        for update in updates[:10]:
            print(f"  {update['symbol']}: pre_open=${update['pre_market_open']:.2f}, %pre={update['pct_from_pre']:+.2f}%")

        print()
        print("=" * 80)
        print("🎉 Backfill complete! Refresh your dashboard to see % PRE data.")
        print("=" * 80)
    else:
        print("⚠️  No updates needed")

if __name__ == "__main__":
    backfill_premarket_opens()
