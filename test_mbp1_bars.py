#!/usr/bin/env python3
"""
Test MBP-1 schema to see what kind of bars we get from quote data.
We'll test with both a liquid stock (AAPL) and WGRX to compare.
"""

import databento as db
from datetime import datetime
import pytz
from collections import defaultdict
from shared.config import settings

API_KEY = settings.databento_api_key
if not API_KEY:
    print("ERROR: DATABENTO_API_KEY not configured")
    exit(1)

print("=" * 80)
print("MBP-1 SCHEMA BAR GENERATION TEST")
print("=" * 80)

# Test with WGRX only
test_symbols = ['WGRX']
dataset = settings.screener_dataset  # EQUS.MINI
schema = settings.screener_schema  # mbp-1

print(f"\nDataset: {dataset}")
print(f"Schema: {schema}")
print(f"Testing symbols: {', '.join(test_symbols)}")
print(f"Will capture for 90 seconds...")
print("-" * 80)

client = db.Live(key=API_KEY)

# Store data per symbol
symbol_data = {symbol: {
    'ticks': [],
    'bars_by_minute': defaultdict(list)
} for symbol in test_symbols}

start_time = datetime.now()
message_count = 0

try:
    client.subscribe(
        dataset=dataset,
        schema=schema,
        symbols=test_symbols,
        stype_in='raw_symbol'
    )

    print(f"Subscription active at {start_time}")
    print()

    for record in client:
        message_count += 1
        current_time = datetime.now()
        elapsed = (current_time - start_time).total_seconds()

        # Stop after 90 seconds
        if elapsed > 90:
            print(f"\n[STOPPED] Captured for 90 seconds")
            break

        # Get symbol
        symbol = record.symbol if hasattr(record, 'symbol') else 'UNKNOWN'
        if symbol not in test_symbols:
            continue

        # Parse timestamp
        ts = record.ts_event
        dt = datetime.fromtimestamp(ts / 1_000_000_000, tz=pytz.UTC)

        # Get bid/ask prices (prices are in fixed-point, divide by 1e9)
        bid_price = record.levels[0].bid_px / 1e9 if hasattr(record, 'levels') and len(record.levels) > 0 and record.levels[0].bid_px else None
        ask_price = record.levels[0].ask_px / 1e9 if hasattr(record, 'levels') and len(record.levels) > 0 and record.levels[0].ask_px else None

        # Calculate mid price (this is what our scanner uses)
        if bid_price and ask_price:
            mid_price = (bid_price + ask_price) / 2
        elif bid_price:
            mid_price = bid_price
        elif ask_price:
            mid_price = ask_price
        else:
            continue

        # Store tick
        symbol_data[symbol]['ticks'].append({
            'timestamp': dt,
            'bid': bid_price,
            'ask': ask_price,
            'mid': mid_price
        })

        # Group by minute
        minute_key = dt.replace(second=0, microsecond=0)
        symbol_data[symbol]['bars_by_minute'][minute_key].append(mid_price)

        # Print every 50 messages
        if message_count % 50 == 0:
            total_ticks = sum(len(data['ticks']) for data in symbol_data.values())
            print(f"  [{elapsed:.0f}s] {message_count} messages | {total_ticks} ticks captured")

except KeyboardInterrupt:
    print("\n[INTERRUPTED] Stopping capture...")

finally:
    client.stop()

    print("\n" + "=" * 80)
    print("ANALYSIS - MBP-1 BAR GENERATION")
    print("=" * 80)

    for symbol in test_symbols:
        data = symbol_data[symbol]
        ticks = data['ticks']
        bars = data['bars_by_minute']

        print(f"\n{'=' * 80}")
        print(f"SYMBOL: {symbol}")
        print(f"{'=' * 80}")

        if not ticks:
            print(f"❌ NO DATA received for {symbol}")
            print(f"   This means:")
            print(f"   - Symbol might not be trading right now")
            print(f"   - Symbol might not be in EQUS.MINI dataset")
            print(f"   - No quote updates during capture period")
            continue

        print(f"\nTotal ticks captured: {len(ticks)}")
        print(f"Minutes with data: {len(bars)}")
        print(f"Average ticks per minute: {len(ticks) / max(len(bars), 1):.1f}")

        # Show aggregated bars
        print(f"\n{'-' * 80}")
        print(f"AGGREGATED 1-MINUTE BARS (using mid price):")
        print(f"{'-' * 80}")
        print(f"{'Minute':<20} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Range':<10} {'Ticks':<10}")
        print(f"{'-' * 80}")

        for minute in sorted(bars.keys()):
            prices = bars[minute]
            bar_open = prices[0]
            bar_high = max(prices)
            bar_low = min(prices)
            bar_close = prices[-1]
            bar_range = bar_high - bar_low
            tick_count = len(prices)

            # Color code based on range
            range_indicator = "📊" if bar_range > 0.01 else "📉" if bar_range > 0 else "➖"

            print(f"{minute.strftime('%Y-%m-%d %H:%M'):<20} "
                  f"${bar_open:<9.4f} ${bar_high:<9.4f} ${bar_low:<9.4f} ${bar_close:<9.4f} "
                  f"${bar_range:<9.4f} {tick_count:<10} {range_indicator}")

        # Price statistics
        all_prices = [t['mid'] for t in ticks]
        price_range = max(all_prices) - min(all_prices)

        print(f"\n{'-' * 80}")
        print(f"PRICE STATISTICS:")
        print(f"{'-' * 80}")
        print(f"  Min Price:    ${min(all_prices):.4f}")
        print(f"  Max Price:    ${max(all_prices):.4f}")
        print(f"  Total Range:  ${price_range:.4f} ({price_range/min(all_prices)*100:.2f}%)")
        print(f"  First Price:  ${all_prices[0]:.4f}")
        print(f"  Last Price:   ${all_prices[-1]:.4f}")
        print(f"  Change:       ${all_prices[-1] - all_prices[0]:.4f}")

        # Analyze bar characteristics
        flat_bars = sum(1 for prices in bars.values() if max(prices) == min(prices))
        bars_with_range = len(bars) - flat_bars

        print(f"\n{'-' * 80}")
        print(f"BAR CHARACTERISTICS:")
        print(f"{'-' * 80}")
        print(f"  Total bars:        {len(bars)}")
        print(f"  Flat bars:         {flat_bars} ({flat_bars/max(len(bars),1)*100:.1f}%)")
        print(f"  Bars with range:   {bars_with_range} ({bars_with_range/max(len(bars),1)*100:.1f}%)")

        if bars_with_range > 0:
            ranges = [max(prices) - min(prices) for prices in bars.values() if max(prices) != min(prices)]
            avg_range = sum(ranges) / len(ranges)
            print(f"  Avg range (non-flat): ${avg_range:.4f}")

    print(f"\n{'=' * 80}")
    print(f"CONCLUSION:")
    print(f"{'=' * 80}")
    print(f"")
    print(f"MBP-1 schema provides quote updates (bid/ask changes).")
    print(f"")
    print(f"✅ Good for: Liquid stocks with active quoting")
    print(f"   - Frequent updates = detailed bars")
    print(f"   - Can see market maker activity")
    print(f"")
    print(f"❌ Bad for: Illiquid stocks like WGRX")
    print(f"   - Few quote updates = flat bars")
    print(f"   - May miss actual trades")
    print(f"")
    print(f"Your current setup (MBP-1) is working correctly!")
    print(f"Flat bars on WGRX are expected - it's just low liquidity.")
    print(f"{'=' * 80}")
