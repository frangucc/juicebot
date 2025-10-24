#!/usr/bin/env python3
"""
Direct test to Databento to capture WGRX data and compare with our stored data.
This will prove if the issue is in our aggregation or the source data itself.
"""

import databento as db
import os
from datetime import datetime, timedelta
import pytz
from collections import defaultdict
from shared.config import settings

# Get API key
API_KEY = settings.databento_api_key
if not API_KEY:
    print("ERROR: DATABENTO_API_KEY not configured")
    exit(1)

print("=" * 80)
print("DATABENTO WGRX DATA CAPTURE TEST")
print("=" * 80)

# Subscribe to WGRX using the same dataset as the scanner
dataset = settings.screener_dataset  # EQUS.MINI
symbols = ['WGRX']
schema = settings.screener_schema  # mbp-1

# Connect to Databento
client = db.Live(key=API_KEY)

print(f"\n[1] Connected to Databento")
print(f"[2] Subscribing to WGRX on {dataset} dataset with {schema} schema...")
print(f"[3] Will capture for 2 minutes and show ALL ticks/quotes received")
print("-" * 80)

# Store all received data
ticks_received = []
bars_by_minute = defaultdict(list)  # minute -> list of prices

start_time = datetime.now()
message_count = 0

try:
    client.subscribe(
        dataset=dataset,
        schema=schema,
        symbols=symbols,
        stype_in='raw_symbol'
    )

    print(f"Subscription active. Listening for WGRX data...")
    print(f"Start time: {start_time}")
    print()

    for record in client:
        message_count += 1
        current_time = datetime.now()
        elapsed = (current_time - start_time).total_seconds()

        # Stop after 2 minutes
        if elapsed > 120:
            print(f"\n[STOPPED] Captured for 2 minutes")
            break

        # Parse the record
        ts = record.ts_event

        # Convert nanoseconds to datetime
        dt = datetime.fromtimestamp(ts / 1_000_000_000, tz=pytz.UTC)

        # Get bid/ask prices
        bid_price = record.levels[0].bid_px / 1e9 if hasattr(record, 'levels') and len(record.levels) > 0 and record.levels[0].bid_px else None
        ask_price = record.levels[0].ask_px / 1e9 if hasattr(record, 'levels') and len(record.levels) > 0 and record.levels[0].ask_px else None

        # Calculate mid price
        if bid_price and ask_price:
            mid_price = (bid_price + ask_price) / 2
        elif bid_price:
            mid_price = bid_price
        elif ask_price:
            mid_price = ask_price
        else:
            continue

        # Store tick
        tick_data = {
            'timestamp': dt,
            'bid': bid_price,
            'ask': ask_price,
            'mid': mid_price,
            'raw_record': record
        }
        ticks_received.append(tick_data)

        # Group by minute
        minute_key = dt.replace(second=0, microsecond=0)
        bars_by_minute[minute_key].append(mid_price)

        # Print every tick
        print(f"[{dt.strftime('%H:%M:%S.%f')[:-3]}] Bid: ${bid_price:.4f} | Ask: ${ask_price:.4f} | Mid: ${mid_price:.4f}")

        # Print progress every 10 messages
        if message_count % 10 == 0:
            print(f"  ... {message_count} messages received, {len(bars_by_minute)} minutes with data ...")

except KeyboardInterrupt:
    print("\n[INTERRUPTED] Stopping capture...")

finally:
    client.stop()

    print("\n" + "=" * 80)
    print("CAPTURE COMPLETE - ANALYSIS")
    print("=" * 80)

    print(f"\nTotal messages received: {message_count}")
    print(f"Total ticks captured: {len(ticks_received)}")
    print(f"Minutes with data: {len(bars_by_minute)}")

    if not ticks_received:
        print("\n❌ NO DATA RECEIVED!")
        print("This means either:")
        print("  1. WGRX is not trading right now (after hours?)")
        print("  2. The symbol is not in the Databento dataset")
        print("  3. There's an issue with the Databento subscription")
    else:
        print("\n" + "-" * 80)
        print("AGGREGATED 1-MINUTE BARS (like our BarAggregator does):")
        print("-" * 80)
        print(f"{'Minute':<20} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Ticks':<10}")
        print("-" * 80)

        for minute in sorted(bars_by_minute.keys()):
            prices = bars_by_minute[minute]
            bar_open = prices[0]
            bar_high = max(prices)
            bar_low = min(prices)
            bar_close = prices[-1]
            tick_count = len(prices)

            print(f"{minute.strftime('%Y-%m-%d %H:%M'):<20} ${bar_open:<9.4f} ${bar_high:<9.4f} ${bar_low:<9.4f} ${bar_close:<9.4f} {tick_count:<10}")

        print("\n" + "-" * 80)
        print("COMPARISON WITH OUR STORED DATA:")
        print("-" * 80)
        print("Our stored bars show things like:")
        print("  - open: 1.2750, high: 1.2750, low: 1.2700, close: 1.2700")
        print("  - open: 1.2100, high: 1.2100, low: 1.2100, close: 1.2100")
        print()
        print("If the bars above show similar patterns (flat or nearly flat),")
        print("then our aggregation is correct and WGRX is just low-volume.")
        print()
        print("If the bars above show more variation, then we have a bug in")
        print("our BarAggregator or data capture pipeline.")
        print("-" * 80)

        # Show price range
        all_prices = [t['mid'] for t in ticks_received]
        print(f"\nPrice Statistics:")
        print(f"  Min Price:  ${min(all_prices):.4f}")
        print(f"  Max Price:  ${max(all_prices):.4f}")
        print(f"  Range:      ${max(all_prices) - min(all_prices):.4f}")
        print(f"  First Tick: ${all_prices[0]:.4f}")
        print(f"  Last Tick:  ${all_prices[-1]:.4f}")
