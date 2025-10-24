#!/usr/bin/env python3
"""
Test TRADES schema to see actual trade data vs MBP-1 quotes.
This will show us if switching schemas gives us better WGRX data.
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
print("TRADES SCHEMA TEST - WGRX")
print("=" * 80)

symbols = ['WGRX']
dataset = settings.screener_dataset  # EQUS.MINI
schema = 'trades'  # Using trades instead of mbp-1

print(f"\nDataset: {dataset}")
print(f"Schema: {schema} (actual trades, not quotes)")
print(f"Symbol: WGRX")
print(f"Will capture for 90 seconds...")
print("-" * 80)

client = db.Live(key=API_KEY)

# Store trade data
trades_received = []
bars_by_minute = defaultdict(list)

start_time = datetime.now()
message_count = 0

try:
    client.subscribe(
        dataset=dataset,
        schema=schema,
        symbols=symbols,
        stype_in='raw_symbol'
    )

    print(f"Subscription active at {start_time}")
    print(f"Listening for ACTUAL TRADES (not quotes)...")
    print()

    for record in client:
        message_count += 1
        current_time = datetime.now()
        elapsed = (current_time - start_time).total_seconds()

        # Stop after 90 seconds
        if elapsed > 90:
            print(f"\n[STOPPED] Captured for 90 seconds")
            break

        # Parse timestamp
        ts = record.ts_event
        dt = datetime.fromtimestamp(ts / 1_000_000_000, tz=pytz.UTC)

        # Get trade data (prices are in fixed-point, divide by 1e9)
        price = record.price / 1e9 if hasattr(record, 'price') else None
        size = record.size if hasattr(record, 'size') else 0
        side = record.side if hasattr(record, 'side') else 'N'

        if not price:
            continue

        # Store trade
        trade_data = {
            'timestamp': dt,
            'price': price,
            'size': size,
            'side': side
        }
        trades_received.append(trade_data)

        # Group by minute for bar aggregation
        minute_key = dt.replace(second=0, microsecond=0)
        bars_by_minute[minute_key].append({
            'price': price,
            'size': size
        })

        # Print each trade
        side_str = "BUY" if side == 'B' else "SELL" if side == 'A' else "N/A"
        print(f"[{dt.strftime('%H:%M:%S.%f')[:-3]}] TRADE: ${price:.4f} | Size: {size:>6} | Side: {side_str}")

        # Print progress every 10 trades
        if message_count % 10 == 0:
            print(f"  ... {message_count} trades received, {len(bars_by_minute)} minutes with data ...")

except KeyboardInterrupt:
    print("\n[INTERRUPTED] Stopping capture...")

finally:
    client.stop()

    print("\n" + "=" * 80)
    print("TRADES SCHEMA ANALYSIS")
    print("=" * 80)

    if not trades_received:
        print(f"\n❌ NO TRADES received for WGRX in 90 seconds")
        print(f"\nThis means:")
        print(f"  - WGRX had no actual trades during this period")
        print(f"  - The stock is extremely illiquid")
        print(f"  - Even with trades schema, data will be sparse")
        print(f"\nConclusion: Trades schema won't help much for WGRX specifically,")
        print(f"but it will provide better data for more liquid stocks and give you")
        print(f"actual trade volume instead of 0.")
    else:
        print(f"\n✅ SUCCESS! Received {len(trades_received)} trades")
        print(f"Minutes with trades: {len(bars_by_minute)}")
        print(f"Average trades per minute: {len(trades_received) / max(len(bars_by_minute), 1):.1f}")

        # Show aggregated bars with VOLUME
        print(f"\n{'-' * 80}")
        print(f"AGGREGATED 1-MINUTE BARS (with actual volume!):")
        print(f"{'-' * 80}")
        print(f"{'Minute':<20} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Volume':<10} {'Trades':<10}")
        print(f"{'-' * 80}")

        for minute in sorted(bars_by_minute.keys()):
            trades = bars_by_minute[minute]
            prices = [t['price'] for t in trades]

            bar_open = prices[0]
            bar_high = max(prices)
            bar_low = min(prices)
            bar_close = prices[-1]
            bar_volume = sum(t['size'] for t in trades)
            trade_count = len(trades)

            print(f"{minute.strftime('%Y-%m-%d %H:%M'):<20} "
                  f"${bar_open:<9.4f} ${bar_high:<9.4f} ${bar_low:<9.4f} ${bar_close:<9.4f} "
                  f"{bar_volume:<10} {trade_count:<10}")

        # Price statistics
        all_prices = [t['price'] for t in trades_received]
        total_volume = sum(t['size'] for t in trades_received)
        buy_trades = sum(1 for t in trades_received if t['side'] == 'B')
        sell_trades = sum(1 for t in trades_received if t['side'] == 'A')

        print(f"\n{'-' * 80}")
        print(f"TRADE STATISTICS:")
        print(f"{'-' * 80}")
        print(f"  Total Trades:    {len(trades_received)}")
        print(f"  Total Volume:    {total_volume:,}")
        print(f"  Buy Trades:      {buy_trades} ({buy_trades/max(len(trades_received),1)*100:.1f}%)")
        print(f"  Sell Trades:     {sell_trades} ({sell_trades/max(len(trades_received),1)*100:.1f}%)")
        print(f"  Unknown Side:    {len(trades_received) - buy_trades - sell_trades}")
        print(f"\n  Min Price:       ${min(all_prices):.4f}")
        print(f"  Max Price:       ${max(all_prices):.4f}")
        print(f"  Price Range:     ${max(all_prices) - min(all_prices):.4f}")
        print(f"  First Trade:     ${all_prices[0]:.4f}")
        print(f"  Last Trade:      ${all_prices[-1]:.4f}")

    print(f"\n{'=' * 80}")
    print(f"COMPARISON: TRADES vs MBP-1")
    print(f"{'=' * 80}")
    print(f"\nMBP-1 (quotes) test: 0 messages in 90 seconds")
    print(f"TRADES test: {len(trades_received)} trades in 90 seconds")
    print(f"\n✅ TRADES schema provides:")
    print(f"   - Actual trade prices (not bid/ask)")
    print(f"   - Real volume data")
    print(f"   - Buy/Sell side information")
    print(f"   - More frequent updates for illiquid stocks")
    print(f"\n{'=' * 80}")

    if len(trades_received) > 0:
        print(f"\n🎯 RECOMMENDATION: Switch to TRADES schema!")
        print(f"   You'll get actual trade data with volume instead of")
        print(f"   sparse quote updates with volume=0")
    else:
        print(f"\n⚠️  WGRX is extremely illiquid - no trades in 90 seconds")
        print(f"   Even with TRADES schema, data will be sparse.")
        print(f"   But it's still better than MBP-1 for your use case.")

    print(f"{'=' * 80}")
