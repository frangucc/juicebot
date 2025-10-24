#!/usr/bin/env python3
"""
Quick test to check:
1. Current WGRX price right now (3:49 PM CST / 4:49 PM EST)
2. If we're getting after-hours data from Databento
3. What the cutoff time is for the data feed
"""

import databento as db
from datetime import datetime
import pytz
from shared.config import settings

API_KEY = settings.databento_api_key

print("=" * 80)
print("AFTER-HOURS DATA TEST - WGRX")
print("=" * 80)

central = pytz.timezone('America/Chicago')
eastern = pytz.timezone('America/New_York')
now = datetime.now(central)

print(f"\nCurrent time (CST): {now.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
print(f"Current time (EST): {now.astimezone(eastern).strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
print(f"\nRegular market hours: 8:30 AM - 3:00 PM CST (9:30 AM - 4:00 PM EST)")
print(f"After-hours: 3:00 PM - 7:00 PM CST (4:00 PM - 8:00 PM EST)")

if now.hour < 8 or (now.hour == 8 and now.minute < 30):
    print(f"\n⚠️  Pre-market - before 8:30 AM CST")
elif now.hour >= 19:
    print(f"\n⚠️  After-hours closed - after 7:00 PM CST")
elif 15 <= now.hour < 19:
    print(f"\n✅ Currently in AFTER-HOURS session")
elif 8 <= now.hour < 15:
    print(f"\n✅ Currently in REGULAR market hours")

print(f"\n{'-' * 80}")
print(f"Testing BOTH schemas for WGRX...")
print(f"{'-' * 80}\n")

# Test both schemas
for schema_name in ['mbp-1', 'trades']:
    print(f"\n{'='*60}")
    print(f"SCHEMA: {schema_name}")
    print(f"{'='*60}")

    client = db.Live(key=API_KEY)

    messages_received = []
    start_time = datetime.now()

    try:
        client.subscribe(
            dataset=settings.screener_dataset,
            schema=schema_name,
            symbols=['WGRX'],
            stype_in='raw_symbol'
        )

        print(f"Subscribed at {start_time.strftime('%I:%M:%S %p')}")
        print(f"Listening for 20 seconds...")

        for record in client:
            current_time = datetime.now()
            elapsed = (current_time - start_time).total_seconds()

            if elapsed > 20:
                break

            # Parse timestamp
            ts = record.ts_event
            dt = datetime.fromtimestamp(ts / 1_000_000_000, tz=pytz.UTC)
            dt_cst = dt.astimezone(central)

            if schema_name == 'mbp-1':
                # MBP-1: bid/ask
                bid = record.levels[0].bid_px / 1e9 if hasattr(record, 'levels') and len(record.levels) > 0 and record.levels[0].bid_px else None
                ask = record.levels[0].ask_px / 1e9 if hasattr(record, 'levels') and len(record.levels) > 0 and record.levels[0].ask_px else None
                mid = (bid + ask) / 2 if bid and ask else (bid or ask)

                messages_received.append({
                    'timestamp': dt_cst,
                    'price': mid,
                    'bid': bid,
                    'ask': ask,
                    'type': 'quote'
                })

                bid_str = f"${bid:.4f}" if bid else "N/A"
                ask_str = f"${ask:.4f}" if ask else "N/A"
                mid_str = f"${mid:.4f}" if mid else "N/A"
                print(f"  [{dt_cst.strftime('%I:%M:%S %p')}] Quote: Bid={bid_str} Ask={ask_str} Mid={mid_str}")

            else:
                # Trades: actual trade
                price = record.price / 1e9 if hasattr(record, 'price') else None
                size = record.size if hasattr(record, 'size') else 0
                side = record.side if hasattr(record, 'side') else 'N'

                messages_received.append({
                    'timestamp': dt_cst,
                    'price': price,
                    'size': size,
                    'side': side,
                    'type': 'trade'
                })

                side_str = "BUY" if side == 'B' else "SELL" if side == 'A' else "N/A"
                print(f"  [{dt_cst.strftime('%I:%M:%S %p')}] Trade: ${price:.4f} Size={size} Side={side_str}")

    except KeyboardInterrupt:
        print("\n[Interrupted]")
    finally:
        client.stop()

        print(f"\n{'-' * 60}")
        print(f"RESULTS FOR {schema_name}:")
        print(f"{'-' * 60}")

        if messages_received:
            print(f"✅ Received {len(messages_received)} messages")

            latest = messages_received[-1]
            print(f"\n📊 LATEST WGRX DATA:")
            print(f"   Time: {latest['timestamp'].strftime('%I:%M:%S %p %Z')}")

            if latest['price']:
                print(f"   Price: ${latest['price']:.4f}")
            else:
                print(f"   Price: N/A")

            if schema_name == 'mbp-1':
                if latest.get('bid'):
                    print(f"   Bid: ${latest['bid']:.4f}")
                else:
                    print(f"   Bid: N/A")

                if latest.get('ask'):
                    print(f"   Ask: ${latest['ask']:.4f}")
                else:
                    print(f"   Ask: N/A")
            else:
                print(f"   Size: {latest['size']}")
                print(f"   Side: {latest['side']}")

            # Check if data is from regular hours or after hours
            msg_hour = latest['timestamp'].hour
            msg_minute = latest['timestamp'].minute

            if msg_hour < 15 or (msg_hour == 15 and msg_minute == 0):
                print(f"   ⚠️  Data from REGULAR HOURS")
            elif msg_hour >= 15:
                print(f"   ✅ Data from AFTER-HOURS")

        else:
            print(f"❌ NO DATA received in 20 seconds")
            print(f"\nPossible reasons:")
            print(f"   1. WGRX not trading right now")
            print(f"   2. Data feed might not include after-hours")
            print(f"   3. Symbol not active in current session")

print(f"\n{'='*80}")
print(f"CONCLUSION:")
print(f"{'='*80}")
print(f"\nIf you see data timestamped AFTER 3:00 PM CST (4:00 PM EST),")
print(f"then the feed includes after-hours data.")
print(f"\nIf all data is from BEFORE 3:00 PM CST, then the feed")
print(f"only provides regular market hours data.")
print(f"{'='*80}")
