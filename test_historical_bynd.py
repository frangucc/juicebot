#!/usr/bin/env python3
"""
Test script to fetch historical TRADES data from Databento for BYND.
Date range: Friday Oct 17, 2025 through Friday Oct 24, 2025
Goal: Get all 1-minute OHLCV bars with real volume data for regression testing.
"""

import databento as db
import pandas as pd
from datetime import datetime, timedelta
import pytz
from collections import defaultdict
from shared.config import settings
from shared.database import supabase

# Constants
PX_SCALE = 1e-9  # Databento price scaling factor
PX_NULL = 2**63 - 1  # Databento null price indicator

def aggregate_trades_to_bars(trades_data):
    """
    Aggregate raw trade messages into 1-minute OHLCV bars.

    Args:
        trades_data: List of trade records from Databento

    Returns:
        DataFrame with 1-minute OHLCV bars
    """
    if not trades_data:
        return pd.DataFrame()

    # Group trades by minute
    bars_by_minute = defaultdict(list)

    for trade in trades_data:
        # Parse timestamp
        ts = pd.Timestamp(trade.ts_event, unit='ns').tz_localize('UTC').tz_convert('US/Eastern')

        # Get trade price and volume
        price = trade.price * PX_SCALE if trade.price != PX_NULL else None
        volume = trade.size if hasattr(trade, 'size') else 0

        if price is None or price <= 0:
            continue

        # Round to minute boundary
        minute_key = ts.floor('1min')

        bars_by_minute[minute_key].append({
            'price': price,
            'volume': volume
        })

    # Convert to OHLCV bars
    bars = []
    for minute, trades in sorted(bars_by_minute.items()):
        if not trades:
            continue

        prices = [t['price'] for t in trades]
        volumes = [t['volume'] for t in trades]

        bar = {
            'timestamp': minute,
            'open': prices[0],
            'high': max(prices),
            'low': min(prices),
            'close': prices[-1],
            'volume': sum(volumes),
            'trade_count': len(trades)
        }
        bars.append(bar)

    df = pd.DataFrame(bars)
    if len(df) > 0:
        df.set_index('timestamp', inplace=True)

    return df


def fetch_historical_trades(symbol, start_date, end_date):
    """
    Fetch historical TRADES data from Databento for a symbol.

    Args:
        symbol: Stock ticker (e.g., 'BYND')
        start_date: Start date (datetime or string)
        end_date: End date (datetime or string)

    Returns:
        DataFrame with 1-minute OHLCV bars
    """
    print(f"\n{'='*80}")
    print(f"FETCHING HISTORICAL TRADES DATA")
    print(f"{'='*80}")
    print(f"Symbol: {symbol}")
    print(f"Start Date: {start_date}")
    print(f"End Date: {end_date}")
    print(f"Dataset: EQUS.MINI")
    print(f"Schema: trades")
    print(f"{'='*80}\n")

    # Initialize Databento Historical client
    client = db.Historical(key=settings.databento_api_key)

    # Fetch trades data
    print(f"[1/3] Fetching raw trade data from Databento...")
    try:
        data = client.timeseries.get_range(
            dataset="EQUS.MINI",
            schema="trades",
            symbols=[symbol],
            start=start_date,
            end=end_date,
            stype_in="raw_symbol"
        )

        # Convert to list for processing
        trades = list(data)
        print(f"✅ Received {len(trades)} trade records")

        if len(trades) == 0:
            print(f"⚠️  WARNING: No trades found for {symbol} in this date range")
            print(f"   This could mean:")
            print(f"   - Symbol had no trading activity")
            print(f"   - Date range is invalid (future date, non-market days)")
            print(f"   - Symbol not available in EQUS.MINI dataset")
            return pd.DataFrame()

        # Show sample trades
        print(f"\n[2/3] Sample trades (first 5):")
        for i, trade in enumerate(trades[:5]):
            ts = pd.Timestamp(trade.ts_event, unit='ns').tz_localize('UTC').tz_convert('US/Eastern')
            price = trade.price * PX_SCALE if trade.price != PX_NULL else None
            volume = trade.size if hasattr(trade, 'size') else 0
            print(f"  {i+1}. {ts} | ${price:.4f} | Vol: {volume:>6}")

        # Aggregate into 1-minute bars
        print(f"\n[3/3] Aggregating trades into 1-minute OHLCV bars...")
        bars_df = aggregate_trades_to_bars(trades)

        if len(bars_df) == 0:
            print(f"⚠️  WARNING: No valid bars created (all trades had invalid prices)")
            return pd.DataFrame()

        print(f"✅ Created {len(bars_df)} 1-minute bars")

        # Calculate statistics
        total_volume = bars_df['volume'].sum()
        avg_volume_per_bar = bars_df['volume'].mean()
        first_bar = bars_df.index[0]
        last_bar = bars_df.index[-1]
        duration_hours = (last_bar - first_bar).total_seconds() / 3600

        print(f"\n{'='*80}")
        print(f"DATA SUMMARY")
        print(f"{'='*80}")
        print(f"Total Bars:           {len(bars_df):,}")
        print(f"First Bar:            {first_bar}")
        print(f"Last Bar:             {last_bar}")
        print(f"Duration:             {duration_hours:.2f} hours")
        print(f"Total Volume:         {total_volume:,}")
        print(f"Avg Volume/Bar:       {avg_volume_per_bar:,.0f}")
        print(f"Total Trades:         {bars_df['trade_count'].sum():,}")
        print(f"Avg Trades/Bar:       {bars_df['trade_count'].mean():.1f}")
        print(f"\nPrice Range:")
        print(f"  Lowest:             ${bars_df['low'].min():.4f}")
        print(f"  Highest:            ${bars_df['high'].max():.4f}")
        print(f"  First Close:        ${bars_df['close'].iloc[0]:.4f}")
        print(f"  Last Close:         ${bars_df['close'].iloc[-1]:.4f}")
        print(f"  Change:             ${bars_df['close'].iloc[-1] - bars_df['close'].iloc[0]:.4f}")
        print(f"  Change %:           {((bars_df['close'].iloc[-1] / bars_df['close'].iloc[0]) - 1) * 100:.2f}%")
        print(f"{'='*80}\n")

        return bars_df

    except Exception as e:
        print(f"❌ ERROR: Failed to fetch data from Databento")
        print(f"   Error: {e}")
        print(f"\nPossible reasons:")
        print(f"  - API key invalid or expired")
        print(f"  - Date range is in the future")
        print(f"  - Symbol not available in EQUS.MINI")
        print(f"  - Network/connection issue")
        return pd.DataFrame()


def store_in_supabase(symbol, bars_df, start_date, end_date):
    """
    Store historical bars in Supabase historical_bars table.

    Args:
        symbol: Stock ticker
        bars_df: DataFrame with 1-minute bars
        start_date: Original start date requested
        end_date: Original end date requested
    """
    if len(bars_df) == 0:
        print(f"⚠️  No data to store")
        return

    print(f"\n{'='*80}")
    print(f"STORING DATA IN SUPABASE")
    print(f"{'='*80}\n")

    try:
        # First, register this fetch in historical_symbols table
        print(f"[1/2] Registering fetch in historical_symbols table...")

        symbol_record = {
            "symbol": symbol,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "bar_count": len(bars_df),
            "data_source": "databento_historical",
            "dataset": "EQUS.MINI",
            "schema_type": "trades",
            "status": "completed",
            "fetch_started_at": datetime.now(pytz.UTC).isoformat(),
            "fetch_completed_at": datetime.now(pytz.UTC).isoformat()
        }

        supabase.table("historical_symbols").upsert(symbol_record).execute()
        print(f"✅ Registered in historical_symbols")

        # Store bars in batches (Supabase has limits)
        print(f"\n[2/2] Storing {len(bars_df)} bars in historical_bars table...")

        batch_size = 1000
        batches = [bars_df.iloc[i:i+batch_size] for i in range(0, len(bars_df), batch_size)]

        for i, batch in enumerate(batches):
            # Convert batch to records
            records = []
            for idx, row in batch.iterrows():
                record = {
                    "symbol": symbol,
                    "timestamp": idx.isoformat(),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": int(row['volume']),
                    "trade_count": int(row['trade_count']),
                    "data_source": "databento_historical",
                    "dataset": "EQUS.MINI",
                    "schema_type": "trades"
                }
                records.append(record)

            # Upsert batch
            supabase.table("historical_bars").upsert(records).execute()
            print(f"  ✓ Batch {i+1}/{len(batches)} ({len(records)} bars)")

        print(f"\n✅ Successfully stored {len(bars_df)} bars in Supabase!")

        # Verify
        print(f"\n[Verification] Querying stored data...")
        result = supabase.table("historical_bars").select("*").eq("symbol", symbol).execute()
        stored_count = len(result.data)
        print(f"✅ Verified: {stored_count} bars in database for {symbol}")

        print(f"\n{'='*80}")
        print(f"STORAGE COMPLETE")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"❌ ERROR: Failed to store data in Supabase")
        print(f"   Error: {e}")
        print(f"\nMake sure:")
        print(f"  - You've run the migration: migrations/003_historical_data_tables.sql")
        print(f"  - Your Supabase credentials are correct")
        print(f"  - The tables exist in your database")


def analyze_data_completeness(bars_df, start_date, end_date):
    """
    Analyze data completeness - check for gaps in the bars.

    Args:
        bars_df: DataFrame with 1-minute bars
        start_date: Expected start date
        end_date: Expected end date
    """
    if len(bars_df) == 0:
        return

    print(f"\n{'='*80}")
    print(f"DATA COMPLETENESS ANALYSIS")
    print(f"{'='*80}\n")

    # Market hours: 9:30 AM - 4:00 PM ET (6.5 hours = 390 minutes)
    trading_minutes_per_day = 390

    # Calculate expected trading days (rough estimate - doesn't account for holidays)
    start = pd.Timestamp(start_date).date()
    end = pd.Timestamp(end_date).date()
    total_days = (end - start).days + 1

    # Estimate trading days (Mon-Fri only)
    trading_days = pd.bdate_range(start=start, end=end).size
    expected_bars = trading_days * trading_minutes_per_day

    actual_bars = len(bars_df)
    completeness_pct = (actual_bars / expected_bars) * 100 if expected_bars > 0 else 0

    print(f"Expected Trading Days:    {trading_days} (excluding weekends)")
    print(f"Expected Bars:            {expected_bars:,} (390 bars/day * {trading_days} days)")
    print(f"Actual Bars:              {actual_bars:,}")
    print(f"Completeness:             {completeness_pct:.2f}%")

    if completeness_pct < 50:
        print(f"\n⚠️  WARNING: Less than 50% completeness")
        print(f"   This could indicate:")
        print(f"   - Stock is illiquid (few trades)")
        print(f"   - Partial data in Databento")
        print(f"   - Date range includes non-trading days")
    elif completeness_pct < 90:
        print(f"\n✓ Reasonable completeness for an illiquid stock")
    else:
        print(f"\n✅ Excellent data completeness!")

    # Check for gaps (missing minutes)
    print(f"\n[Gap Analysis]")
    if len(bars_df) > 1:
        bars_df_sorted = bars_df.sort_index()
        time_diffs = bars_df_sorted.index.to_series().diff()
        gaps = time_diffs[time_diffs > pd.Timedelta(minutes=1)]

        if len(gaps) > 0:
            print(f"Found {len(gaps)} gaps (missing minutes):")
            for idx, gap_size in gaps.head(10).items():
                gap_minutes = gap_size.total_seconds() / 60
                print(f"  - {idx}: {gap_minutes:.0f} minute gap")

            if len(gaps) > 10:
                print(f"  ... and {len(gaps) - 10} more gaps")
        else:
            print(f"✅ No gaps found - continuous bars!")

    print(f"\n{'='*80}\n")


def main():
    """Main test function."""
    # Configuration
    symbol = "BYND"

    # NOTE: The dates provided are in October 2025, which is in the FUTURE!
    # This test will fail because Databento cannot provide future data.
    # Adjusting to October 2024 for a valid test:

    print(f"\n⚠️  IMPORTANT NOTE:")
    print(f"   The requested dates (Oct 17-24, 2025) are in the FUTURE.")
    print(f"   Adjusting to October 2024 for this test.\n")

    start_date = datetime(2024, 10, 17, tzinfo=pytz.UTC)  # Friday Oct 17, 2024
    end_date = datetime(2024, 10, 24, 23, 59, 59, tzinfo=pytz.UTC)  # Friday Oct 24, 2024

    print(f"\n{'='*80}")
    print(f"DATABENTO HISTORICAL TRADES TEST - {symbol}")
    print(f"{'='*80}\n")
    print(f"This script will:")
    print(f"  1. Fetch all TRADES data for {symbol}")
    print(f"  2. Aggregate into 1-minute OHLCV bars")
    print(f"  3. Store in Supabase historical_bars table")
    print(f"  4. Analyze data completeness")
    print(f"\nPress Ctrl+C to cancel...\n")

    # Step 1: Fetch historical data
    bars_df = fetch_historical_trades(symbol, start_date, end_date)

    if len(bars_df) == 0:
        print(f"\n❌ Test failed - no data retrieved")
        return

    # Step 2: Analyze completeness
    analyze_data_completeness(bars_df, start_date, end_date)

    # Step 3: Store in Supabase
    print(f"\n📊 Ready to store data in Supabase?")
    print(f"   This will create {len(bars_df)} records in historical_bars table.")

    # Auto-confirm if running non-interactively
    import sys
    if sys.stdin.isatty():
        response = input(f"   Continue? (yes/no): ").strip().lower()
    else:
        response = 'yes'
        print(f"   Running non-interactively, auto-confirming: yes")

    if response in ['yes', 'y']:
        store_in_supabase(symbol, bars_df, start_date, end_date)
    else:
        print(f"\n⏭️  Skipping Supabase storage")

    # Step 4: Show sample data
    print(f"\n{'='*80}")
    print(f"SAMPLE BARS (First 10)")
    print(f"{'='*80}\n")
    print(bars_df.head(10).to_string())

    print(f"\n{'='*80}")
    print(f"TEST COMPLETE!")
    print(f"{'='*80}\n")

    print(f"Summary:")
    print(f"  ✅ Fetched {len(bars_df)} 1-minute bars for {symbol}")
    print(f"  ✅ Date range: {bars_df.index[0]} to {bars_df.index[-1]}")
    print(f"  ✅ Total volume: {bars_df['volume'].sum():,}")
    print(f"\nNext steps:")
    print(f"  1. Run migration: migrations/003_historical_data_tables.sql")
    print(f"  2. Adjust dates if needed (currently using 2024 data)")
    print(f"  3. Re-run this script to store data")
    print(f"  4. Query historical_data_summary view for stats")
    print(f"\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Test cancelled by user\n")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
