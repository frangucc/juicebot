"""
Test script to validate TRADES schema for leaderboard stocks.

This script fetches recent trade data for top leaderboard stocks
to verify we can build proper OHLCV bars with volume.
"""

import databento as db
import pandas as pd
from datetime import datetime, timedelta
from shared.config import settings
from typing import Dict, List
import asyncio
import httpx


# Databento constants
PX_SCALE = 1e-9
PX_NULL = 2**63 - 1  # INT64_MAX = 9223372036854775807
UNDEF_PRICE = PX_NULL


def format_price(price_int: int) -> float:
    """Convert Databento fixed-precision price to decimal."""
    if price_int == UNDEF_PRICE:
        return None
    return price_int * PX_SCALE


def decode_side(side: str) -> str:
    """Decode trade side."""
    side_map = {
        'A': 'Sell Aggressor',
        'B': 'Buy Aggressor',
        'N': 'No Side Specified'
    }
    return side_map.get(side, side)


def decode_action(action: str) -> str:
    """Decode action type."""
    action_map = {
        'T': 'Trade',
        'A': 'Add',
        'M': 'Modify',
        'C': 'Cancel',
        'R': 'Clear',
        'F': 'Fill',
        'N': 'None'
    }
    return action_map.get(action, action)


def decode_flags(flags: int) -> List[str]:
    """Decode flags bitfield."""
    flag_names = []
    if flags & (1 << 7):
        flag_names.append('F_LAST')
    if flags & (1 << 6):
        flag_names.append('F_TOB')
    if flags & (1 << 5):
        flag_names.append('F_SNAPSHOT')
    if flags & (1 << 4):
        flag_names.append('F_MBP')
    if flags & (1 << 3):
        flag_names.append('F_BAD_TS_RECV')
    if flags & (1 << 2):
        flag_names.append('F_MAYBE_BAD_BOOK')
    if flags & (1 << 1):
        flag_names.append('F_PUBLISHER_SPECIFIC')
    return flag_names


class TradeBar:
    """Simple OHLCV bar built from trades."""

    def __init__(self, symbol: str, timestamp: pd.Timestamp, first_trade_price: float, first_trade_volume: int):
        self.symbol = symbol
        self.timestamp = timestamp
        self.open = first_trade_price
        self.high = first_trade_price
        self.low = first_trade_price
        self.close = first_trade_price
        self.volume = first_trade_volume
        self.trade_count = 1

    def add_trade(self, price: float, volume: int):
        """Update bar with new trade."""
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume
        self.trade_count += 1

    def __repr__(self):
        return (f"Bar({self.symbol} @ {self.timestamp.strftime('%H:%M')} | "
                f"O:{self.open:.4f} H:{self.high:.4f} L:{self.low:.4f} C:{self.close:.4f} | "
                f"Vol:{self.volume:,} Trades:{self.trade_count})")


async def fetch_top_leaderboard_symbols(limit: int = 10) -> List[str]:
    """Fetch top symbols from leaderboard."""
    API_URL = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{API_URL}/symbols/leaderboard",
            params={"threshold": 1.0, "baseline": "yesterday", "direction": "up"}
        )
        response.raise_for_status()
        data = response.json()

        # Get top stocks from 20%+ column
        symbols = [s["symbol"] for s in data.get("col_20_plus", [])[:limit]]

        # Also add some from 10-20% if not enough
        if len(symbols) < limit:
            symbols.extend([s["symbol"] for s in data.get("col_10_to_20", [])[:limit-len(symbols)]])

        return symbols


def test_trades_schema(symbols: List[str], duration_minutes: int = 30):
    """
    Test TRADES schema for given symbols.

    Args:
        symbols: List of stock symbols to test
        duration_minutes: How many minutes of data to fetch
    """
    print("\n" + "=" * 100)
    print("TESTING TRADES SCHEMA FOR LEADERBOARD STOCKS")
    print("=" * 100)
    print(f"\nSymbols: {', '.join(symbols)}")
    print(f"Duration: Last {duration_minutes} minutes")

    # Setup time range - use market hours for EQUS.MINI
    # EQUS.MINI is 9:30 AM - 4:00 PM ET (13:30 - 20:00 UTC)
    now = pd.Timestamp.now("UTC")

    # Get today's market close (4 PM ET)
    now_et = pd.Timestamp.now("US/Eastern")
    market_close_et = now_et.normalize() + timedelta(hours=16)  # 4 PM ET
    market_close_utc = market_close_et.tz_convert("UTC")

    if now > market_close_utc:
        # Market closed, use last 30 min of trading
        end_time = market_close_utc
        start_time = end_time - timedelta(minutes=duration_minutes)
    else:
        # Market open or not yet closed, use recent data
        end_time = now - timedelta(minutes=2)  # Buffer for data availability
        start_time = end_time - timedelta(minutes=duration_minutes)

    print(f"Time range: {start_time.strftime('%H:%M:%S')} to {end_time.strftime('%H:%M:%S')} UTC")

    # Initialize Databento client
    client = db.Historical(key=settings.databento_api_key)

    print("\n📡 Fetching TRADES data from Databento...")

    try:
        # Fetch trades data
        data = client.timeseries.get_range(
            dataset="EQUS.MINI",
            schema="trades",
            symbols=symbols,
            start=start_time.isoformat(),
            end=end_time.isoformat(),
        )

        print("✅ Data fetched successfully!")

        # Process trades into bars
        print("\n" + "-" * 100)
        print("PROCESSING TRADES INTO 1-MINUTE BARS")
        print("-" * 100)

        # Track bars per symbol
        bars_by_symbol: Dict[str, Dict[pd.Timestamp, TradeBar]] = {}
        trade_count_by_symbol: Dict[str, int] = {}

        # Process each trade message
        for msg in data:
            if not isinstance(msg, db.TradeMsg):
                continue

            # Get symbol from instrument_id (need symbology mapping)
            # For now, we'll process and show raw data

            # Extract trade data
            trade_price = format_price(msg.price)
            if trade_price is None:
                continue

            trade_volume = msg.size
            side = decode_side(msg.side)
            action = decode_action(msg.action)
            flags = decode_flags(msg.flags)

            # Get timestamp
            ts = pd.Timestamp(msg.ts_event, unit='ns').tz_localize('UTC').tz_convert('US/Eastern')
            bar_ts = ts.floor('1min')

            # Show first few trades
            if sum(trade_count_by_symbol.values()) < 20:
                print(f"\n📊 Trade #{sum(trade_count_by_symbol.values()) + 1}:")
                print(f"   Instrument ID: {msg.instrument_id}")
                print(f"   Timestamp:     {ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} ET")
                print(f"   Price:         ${trade_price:.4f}")
                print(f"   Volume:        {trade_volume:,} shares")
                print(f"   Side:          {side}")
                print(f"   Action:        {action}")
                print(f"   Flags:         {', '.join(flags) if flags else 'None'}")
                print(f"   Publisher ID:  {msg.publisher_id}")
                print(f"   Sequence:      {msg.sequence}")

        # Convert to dataframe for easier analysis
        print("\n" + "=" * 100)
        print("CONVERTING TO DATAFRAME FOR ANALYSIS")
        print("=" * 100)

        df = data.to_df()

        if len(df) == 0:
            print("\n❌ No trade data received for these symbols!")
            print("\nPossible reasons:")
            print("  1. Symbols are illiquid (no trades in the time window)")
            print("  2. Market is closed")
            print("  3. Symbols may only have quotes (MBP-1) but no actual trades")
            return

        print(f"\n✅ Received {len(df)} trade records")

        # Group by symbol
        if 'symbol' in df.index.names:
            symbols_with_data = df.index.get_level_values('symbol').unique()
            print(f"✅ {len(symbols_with_data)} symbols have trade data: {', '.join(symbols_with_data)}")

            print("\n" + "-" * 100)
            print("TRADE SUMMARY BY SYMBOL")
            print("-" * 100)

            for symbol in symbols_with_data:
                symbol_trades = df.xs(symbol, level='symbol')

                print(f"\n📈 {symbol}")
                print(f"   Trade Count:      {len(symbol_trades):,}")
                print(f"   Total Volume:     {symbol_trades['size'].sum():,} shares")
                print(f"   Price Range:      ${symbol_trades['price'].min():.4f} - ${symbol_trades['price'].max():.4f}")
                print(f"   Avg Trade Size:   {symbol_trades['size'].mean():.0f} shares")
                print(f"   First Trade:      {symbol_trades.index[0].strftime('%H:%M:%S')}")
                print(f"   Last Trade:       {symbol_trades.index[-1].strftime('%H:%M:%S')}")

                # Side distribution
                side_counts = symbol_trades['side'].value_counts()
                print(f"   Side Distribution:")
                for side, count in side_counts.items():
                    side_name = decode_side(side)
                    print(f"     - {side_name}: {count} ({count/len(symbol_trades)*100:.1f}%)")

                # Build 1-minute bars
                print(f"\n   📊 Building 1-minute bars...")
                bars = []

                for minute, trades_in_minute in symbol_trades.groupby(pd.Grouper(freq='1min')):
                    if len(trades_in_minute) == 0:
                        continue

                    bar = TradeBar(
                        symbol=symbol,
                        timestamp=minute,
                        first_trade_price=trades_in_minute.iloc[0]['price'],
                        first_trade_volume=trades_in_minute.iloc[0]['size']
                    )

                    for _, trade in trades_in_minute.iloc[1:].iterrows():
                        bar.add_trade(trade['price'], trade['size'])

                    bars.append(bar)

                print(f"   ✅ Created {len(bars)} bars from {len(symbol_trades)} trades")

                if bars:
                    print(f"\n   Sample bars (first 5):")
                    for bar in bars[:5]:
                        print(f"     {bar}")

        print("\n" + "=" * 100)
        print("COMPARISON: TRADES vs MBP-1")
        print("=" * 100)

        print("\n✅ TRADES SCHEMA PROVIDES:")
        print("   • Actual trade prices")
        print("   • Real trade volume (size field)")
        print("   • Trade aggressor side (buyer/seller)")
        print("   • Can build complete OHLCV bars with volume")
        print("   • Updates on every trade execution")

        print("\n❌ TRADES SCHEMA DOES NOT PROVIDE:")
        print("   • Bid/ask spread")
        print("   • Quote updates (only trades)")
        print("   • Data when no trades occur (illiquid periods)")

        print("\n" + "=" * 100)
        print("RECOMMENDATION")
        print("=" * 100)

        if len(df) > 100:
            print("\n✅ GOOD TRADE VOLUME - Recommend switching to TRADES schema")
            print("   These stocks have enough trading activity to build complete bars.")
        elif len(df) > 0:
            print("\n⚠️  LOW TRADE VOLUME - Consider dual-stream approach")
            print("   Some stocks are illiquid. Consider:")
            print("   • Keep MBP-1 for alerts (captures all price movements)")
            print("   • Use TRADES for bar recording (when trades occur)")
        else:
            print("\n❌ NO TRADES - Keep MBP-1 schema")
            print("   These stocks have no trades in the time window.")
            print("   MBP-1 (quotes) is better for capturing price movements.")

    except Exception as e:
        print(f"\n❌ Error fetching data: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main test function."""
    print("\n🔍 Testing TRADES Schema for Leaderboard Stocks\n")

    # Fetch top leaderboard symbols
    print("📥 Fetching top leaderboard stocks...")
    symbols = await fetch_top_leaderboard_symbols(limit=5)

    if not symbols:
        print("❌ No symbols in leaderboard. Using test symbols.")
        symbols = ["AAPL", "TSLA", "NVDA"]

    print(f"✅ Testing with {len(symbols)} symbols: {', '.join(symbols)}")

    # Test with 30 minutes of data
    test_trades_schema(symbols, duration_minutes=30)

    print("\n" + "=" * 100)
    print("TEST COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(main())
