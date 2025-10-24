"""
Test script to analyze top 20%+ leaderboard stocks
Fetches bar count and price action data for the most extreme movers
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import sys


API_URL = "http://localhost:8000"


async def fetch_leaderboard_20_plus(direction: str = "up") -> List[Dict[str, Any]]:
    """Fetch the 20%+ column from leaderboard"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{API_URL}/symbols/leaderboard",
            params={
                "threshold": 1.0,
                "baseline": "yesterday",
                "direction": direction
            }
        )
        response.raise_for_status()
        data = response.json()
        return data.get("col_20_plus", [])


async def fetch_bars(symbol: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
    """Fetch 1-minute bars for a symbol"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {"symbol": symbol}
        if start_date:
            params["start"] = start_date
        if end_date:
            params["end"] = end_date

        response = await client.get(f"{API_URL}/bars/{symbol}", params=params)
        response.raise_for_status()
        return response.json()


async def fetch_symbol_state(symbol: str) -> Dict[str, Any]:
    """Fetch current symbol state from database"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{API_URL}/symbols/{symbol}/latest-price")
        response.raise_for_status()
        return response.json()


def calculate_price_action_metrics(bars: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate price action metrics from bars"""
    if not bars:
        return {
            "bar_count": 0,
            "error": "No bars available"
        }

    # Sort bars by timestamp (API returns 'timestamp', not 'ts_event')
    sorted_bars = sorted(bars, key=lambda x: x["timestamp"])

    first_bar = sorted_bars[0]
    last_bar = sorted_bars[-1]

    # Calculate price metrics
    open_price = first_bar["open"]
    close_price = last_bar["close"]
    high_price = max(bar["high"] for bar in sorted_bars)
    low_price = min(bar["low"] for bar in sorted_bars)

    # Calculate percentage moves
    pct_change = ((close_price - open_price) / open_price) * 100 if open_price > 0 else 0
    daily_range_pct = ((high_price - low_price) / open_price) * 100 if open_price > 0 else 0

    # Volume analysis
    total_volume = sum(bar["volume"] for bar in sorted_bars)
    avg_volume_per_bar = total_volume / len(sorted_bars) if sorted_bars else 0

    # Volatility (average bar range as % of price)
    bar_ranges = [((bar["high"] - bar["low"]) / bar["open"]) * 100
                  for bar in sorted_bars if bar["open"] > 0]
    avg_volatility = sum(bar_ranges) / len(bar_ranges) if bar_ranges else 0

    # Count significant moves (>1% bar move)
    significant_moves = sum(1 for pct in bar_ranges if pct > 1.0)

    # Time analysis
    first_ts = datetime.fromisoformat(first_bar["timestamp"].replace("Z", "+00:00"))
    last_ts = datetime.fromisoformat(last_bar["timestamp"].replace("Z", "+00:00"))
    duration_minutes = (last_ts - first_ts).total_seconds() / 60

    return {
        "bar_count": len(sorted_bars),
        "duration_minutes": round(duration_minutes, 1),
        "first_bar_time": first_ts.strftime("%H:%M:%S"),
        "last_bar_time": last_ts.strftime("%H:%M:%S"),
        "open": round(open_price, 2),
        "close": round(close_price, 2),
        "high": round(high_price, 2),
        "low": round(low_price, 2),
        "pct_change": round(pct_change, 2),
        "daily_range_pct": round(daily_range_pct, 2),
        "total_volume": total_volume,
        "avg_volume_per_bar": round(avg_volume_per_bar, 0),
        "avg_volatility_per_bar": round(avg_volatility, 2),
        "significant_moves_count": significant_moves,
        "bars_per_minute": round(len(sorted_bars) / duration_minutes, 2) if duration_minutes > 0 else 0
    }


async def analyze_symbol(symbol_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a single symbol"""
    symbol = symbol_data["symbol"]
    print(f"\n📊 Analyzing {symbol}...")

    try:
        # Fetch today's bars
        today = datetime.now().strftime("%Y-%m-%d")
        bars = await fetch_bars(symbol, start_date=today)

        # Calculate metrics
        price_action = calculate_price_action_metrics(bars)

        # Get current state
        try:
            current_state = await fetch_symbol_state(symbol)
        except Exception as e:
            current_state = symbol_data

        return {
            "symbol": symbol,
            "current_price": symbol_data.get("current_price", 0),
            "pct_from_yesterday": symbol_data.get("pct_from_yesterday", 0),
            "pct_from_open": symbol_data.get("pct_from_open", 0),
            "pct_from_5min": symbol_data.get("pct_from_5min", 0),
            "last_updated": symbol_data.get("last_updated", ""),
            **price_action
        }
    except Exception as e:
        print(f"❌ Error analyzing {symbol}: {e}")
        return {
            "symbol": symbol,
            "error": str(e),
            "current_price": symbol_data.get("current_price", 0),
            "pct_from_yesterday": symbol_data.get("pct_from_yesterday", 0)
        }


def format_analysis_report(results: List[Dict[str, Any]], direction: str):
    """Format and print analysis report"""
    print("\n" + "=" * 100)
    print(f"🚀 TOP 20%+ {'GAP UPS' if direction == 'up' else 'GAP DOWNS'} - LEADERBOARD ANALYSIS")
    print("=" * 100)
    print(f"\nTotal symbols analyzed: {len(results)}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Filter successful analyses
    successful = [r for r in results if "bar_count" in r and r["bar_count"] > 0]
    failed = [r for r in results if "error" in r or r.get("bar_count", 0) == 0]

    print(f"\n✅ Successfully analyzed: {len(successful)}")
    print(f"❌ Failed/No data: {len(failed)}")

    if failed:
        print("\n⚠️  Symbols with no bar data:")
        for r in failed:
            print(f"   - {r['symbol']}: {r.get('error', 'No bars available')}")

    if not successful:
        print("\n❌ No symbols with bar data to analyze")
        return

    # Sort by percentage from yesterday (descending for ups, ascending for downs)
    successful.sort(key=lambda x: x["pct_from_yesterday"], reverse=(direction == "up"))

    print("\n" + "-" * 100)
    print("DETAILED ANALYSIS")
    print("-" * 100)

    for i, result in enumerate(successful, 1):
        print(f"\n{i}. {result['symbol']} - ${result['current_price']:.2f}")
        print(f"   {'─' * 90}")
        print(f"   📈 Performance:")
        print(f"      • From Yesterday: {result['pct_from_yesterday']:+.2f}%")
        print(f"      • From Open:      {result['pct_from_open']:+.2f}%")
        print(f"      • Last 5min:      {result['pct_from_5min']:+.2f}%")
        print(f"      • Intraday Move:  {result['pct_change']:+.2f}%")
        print(f"      • Daily Range:    {result['daily_range_pct']:.2f}%")

        print(f"\n   📊 Bar Data:")
        print(f"      • Bar Count:      {result['bar_count']} bars")
        print(f"      • Duration:       {result['duration_minutes']} minutes")
        print(f"      • Bars/Minute:    {result['bars_per_minute']}")
        print(f"      • First Bar:      {result['first_bar_time']}")
        print(f"      • Last Bar:       {result['last_bar_time']}")

        print(f"\n   💰 Price Action:")
        print(f"      • Open:           ${result['open']:.2f}")
        print(f"      • High:           ${result['high']:.2f}")
        print(f"      • Low:            ${result['low']:.2f}")
        print(f"      • Close:          ${result['close']:.2f}")

        print(f"\n   📉 Volatility:")
        print(f"      • Avg Bar Range:  {result['avg_volatility_per_bar']:.2f}%")
        print(f"      • Big Moves (>1%): {result['significant_moves_count']} bars")

        print(f"\n   📦 Volume:")
        print(f"      • Total Volume:   {result['total_volume']:,}")
        print(f"      • Avg per Bar:    {result['avg_volume_per_bar']:,.0f}")

    # Summary statistics
    print("\n" + "=" * 100)
    print("SUMMARY STATISTICS")
    print("=" * 100)

    avg_bars = sum(r["bar_count"] for r in successful) / len(successful)
    avg_duration = sum(r["duration_minutes"] for r in successful) / len(successful)
    avg_volatility = sum(r["avg_volatility_per_bar"] for r in successful) / len(successful)
    avg_volume = sum(r["total_volume"] for r in successful) / len(successful)
    avg_pct_from_yesterday = sum(r["pct_from_yesterday"] for r in successful) / len(successful)

    print(f"\n📊 Average Metrics across {len(successful)} symbols:")
    print(f"   • Bars per Symbol:        {avg_bars:.1f}")
    print(f"   • Duration (minutes):     {avg_duration:.1f}")
    print(f"   • Volatility per Bar:     {avg_volatility:.2f}%")
    print(f"   • Total Volume:           {avg_volume:,.0f}")
    print(f"   • % from Yesterday:       {avg_pct_from_yesterday:+.2f}%")

    # Find extremes
    max_bars = max(successful, key=lambda x: x["bar_count"])
    min_bars = min(successful, key=lambda x: x["bar_count"])
    max_vol = max(successful, key=lambda x: x["avg_volatility_per_bar"])
    max_volume = max(successful, key=lambda x: x["total_volume"])

    print(f"\n🏆 Extremes:")
    print(f"   • Most Bars:        {max_bars['symbol']} ({max_bars['bar_count']} bars)")
    print(f"   • Fewest Bars:      {min_bars['symbol']} ({min_bars['bar_count']} bars)")
    print(f"   • Most Volatile:    {max_vol['symbol']} ({max_vol['avg_volatility_per_bar']:.2f}% per bar)")
    print(f"   • Highest Volume:   {max_volume['symbol']} ({max_volume['total_volume']:,})")

    print("\n" + "=" * 100)


async def main():
    """Main test function"""
    print("\n🔍 Starting Leaderboard Analysis Test...")
    print("Connecting to API at:", API_URL)

    # Get direction from command line or default to 'up'
    if len(sys.argv) > 1:
        direction = sys.argv[1].lower()
        if direction not in ["up", "down"]:
            print("❌ Invalid direction. Use 'up' or 'down'")
            print("Usage: python test_leaderboard_analysis.py [up|down]")
            return
    else:
        direction = "up"
        print(f"\n💡 Defaulting to GAP UPS. Use 'python test_leaderboard_analysis.py down' for GAP DOWNS")

    # Fetch leaderboard
    print(f"\n📥 Fetching 20%+ {direction.upper()} stocks from leaderboard...")
    leaderboard = await fetch_leaderboard_20_plus(direction)

    if not leaderboard:
        print("❌ No stocks in 20%+ category")
        return

    print(f"✅ Found {len(leaderboard)} stocks in 20%+ category")

    # Analyze each symbol
    results = []
    for symbol_data in leaderboard:
        result = await analyze_symbol(symbol_data)
        results.append(result)
        await asyncio.sleep(0.1)  # Small delay to avoid overwhelming API

    # Format and display report
    format_analysis_report(results, direction)

    # Save to file
    output_file = f"leaderboard_analysis_{direction}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
