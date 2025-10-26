"""
Advanced Volume Analysis Tools
Provides volume profile, relative volume, VWAP, and volume trends.
"""

from typing import List, Dict, Any
import statistics


async def get_volume_profile(symbol: str, bar_history: List[Dict[str, Any]], lookback: int = 100) -> Dict[str, Any]:
    """
    Calculate Volume Profile - shows price levels with highest volume concentration.

    Groups bars into price buckets and shows which price levels had most activity.

    Args:
        symbol: Stock symbol
        bar_history: Historical bars
        lookback: Number of bars to analyze (default 100)

    Returns:
        {
            "symbol": "BYND",
            "lookback": 100,
            "high_volume_node": 0.57,  # Price with most volume
            "low_volume_node": 0.62,   # Price with least volume
            "value_area_high": 0.60,   # Top of 70% volume area
            "value_area_low": 0.54,    # Bottom of 70% volume area
            "poc": 0.57,               # Point of Control (max volume)
            "profile": [               # Volume distribution
                {"price": 0.50, "volume": 1000000, "pct": 5.2},
                {"price": 0.55, "volume": 3000000, "pct": 15.6},
                {"price": 0.60, "volume": 2500000, "pct": 13.0},
                ...
            ]
        }
    """
    if not bar_history:
        return {"error": f"No bar data for {symbol}"}

    # Get recent bars
    bars = bar_history[-lookback:] if len(bar_history) > lookback else bar_history

    if not bars:
        return {"error": f"Insufficient bar data for {symbol}"}

    # Find price range
    all_highs = [float(bar['high']) for bar in bars]
    all_lows = [float(bar['low']) for bar in bars]
    price_high = max(all_highs)
    price_low = min(all_lows)
    price_range = price_high - price_low

    # Create 20 price buckets (more granular = better profile)
    num_buckets = 20
    bucket_size = price_range / num_buckets if price_range > 0 else 0.01

    # Initialize buckets: {price_level: total_volume}
    buckets = {}
    for i in range(num_buckets):
        bucket_price = price_low + (i * bucket_size) + (bucket_size / 2)  # Mid-point
        buckets[round(bucket_price, 2)] = 0

    # Distribute volume across buckets
    for bar in bars:
        bar_high = float(bar['high'])
        bar_low = float(bar['low'])
        bar_volume = float(bar['volume'])

        # Distribute bar's volume across price levels it touched
        for price_level in buckets.keys():
            if bar_low <= price_level <= bar_high:
                buckets[price_level] += bar_volume / num_buckets

    # Calculate total volume
    total_volume = sum(buckets.values())

    # Find POC (Point of Control) - price with most volume
    poc_price = max(buckets.items(), key=lambda x: x[1])[0] if buckets else 0
    poc_volume = buckets.get(poc_price, 0)

    # Find high/low volume nodes
    hvn_price = max(buckets.items(), key=lambda x: x[1])[0] if buckets else 0
    lvn_price = min(buckets.items(), key=lambda x: x[1])[0] if buckets else 0

    # Calculate Value Area (70% of volume)
    sorted_buckets = sorted(buckets.items(), key=lambda x: x[1], reverse=True)
    cumulative_volume = 0
    value_area_prices = []

    for price, vol in sorted_buckets:
        cumulative_volume += vol
        value_area_prices.append(price)
        if cumulative_volume >= total_volume * 0.70:
            break

    value_area_high = max(value_area_prices) if value_area_prices else 0
    value_area_low = min(value_area_prices) if value_area_prices else 0

    # Build profile array
    profile = []
    for price, vol in sorted(buckets.items()):
        pct = (vol / total_volume * 100) if total_volume > 0 else 0
        profile.append({
            "price": price,
            "volume": int(vol),
            "pct": round(pct, 1)
        })

    return {
        "symbol": symbol,
        "lookback": len(bars),
        "high_volume_node": hvn_price,
        "low_volume_node": lvn_price,
        "value_area_high": value_area_high,
        "value_area_low": value_area_low,
        "poc": poc_price,
        "poc_volume": int(poc_volume),
        "total_volume": int(total_volume),
        "profile": profile[:10]  # Return top 10 levels for readability
    }


async def get_relative_volume(symbol: str, bar_history: List[Dict[str, Any]], period: int = 20) -> Dict[str, Any]:
    """
    Calculate Relative Volume (RVOL) - compares recent volume to earlier session.

    RVOL = (avg volume last N bars) / (avg volume previous N bars)

    Args:
        symbol: Stock symbol
        bar_history: Historical bars
        period: Number of bars to compare (default 20)

    Returns:
        {
            "symbol": "BYND",
            "rvol": 1.45,              # 45% above average
            "recent_avg": 150000,       # Avg volume last 20 bars
            "previous_avg": 103000,     # Avg volume previous 20 bars
            "current": 180000,          # Current bar volume
            "interpretation": "Hot"     # Cold/Normal/Warm/Hot/Explosive
        }
    """
    if not bar_history:
        return {"error": f"No bar data for {symbol}"}

    if len(bar_history) < period * 2:
        return {"error": f"Need at least {period * 2} bars for RVOL calculation"}

    # Get recent and previous periods
    recent_bars = bar_history[-period:]
    previous_bars = bar_history[-(period * 2):-period]

    # Calculate average volumes
    recent_avg = statistics.mean([float(bar['volume']) for bar in recent_bars])
    previous_avg = statistics.mean([float(bar['volume']) for bar in previous_bars])

    # Calculate RVOL
    rvol = recent_avg / previous_avg if previous_avg > 0 else 1.0

    # Current bar volume
    current_volume = float(bar_history[-1]['volume'])

    # Interpretation
    if rvol < 0.5:
        interpretation = "Cold (below 50% avg)"
    elif rvol < 0.8:
        interpretation = "Below Average"
    elif rvol < 1.2:
        interpretation = "Normal"
    elif rvol < 1.5:
        interpretation = "Warm (above avg)"
    elif rvol < 2.0:
        interpretation = "Hot (50%+ above avg)"
    else:
        interpretation = "Explosive (2x+ avg)"

    return {
        "symbol": symbol,
        "rvol": round(rvol, 2),
        "recent_avg": int(recent_avg),
        "previous_avg": int(previous_avg),
        "current": int(current_volume),
        "period": period,
        "interpretation": interpretation
    }


async def get_vwap(symbol: str, bar_history: List[Dict[str, Any]], lookback: int = 390) -> Dict[str, Any]:
    """
    Calculate Volume-Weighted Average Price (VWAP).

    VWAP = Sum(Price × Volume) / Sum(Volume)

    Args:
        symbol: Stock symbol
        bar_history: Historical bars
        lookback: Number of bars (default 390 = full day)

    Returns:
        {
            "symbol": "BYND",
            "vwap": 0.5834,
            "current_price": 0.5900,
            "distance": +0.0066,
            "distance_pct": +1.13,
            "position": "Above VWAP"  # Above/Below/At VWAP
        }
    """
    if not bar_history:
        return {"error": f"No bar data for {symbol}"}

    # Get bars
    bars = bar_history[-lookback:] if len(bar_history) > lookback else bar_history

    if not bars:
        return {"error": f"Insufficient bar data for {symbol}"}

    # Calculate VWAP
    total_pv = 0  # Price × Volume
    total_volume = 0

    for bar in bars:
        typical_price = (float(bar['high']) + float(bar['low']) + float(bar['close'])) / 3
        volume = float(bar['volume'])
        total_pv += typical_price * volume
        total_volume += volume

    vwap = total_pv / total_volume if total_volume > 0 else 0

    # Current price
    current_price = float(bars[-1]['close'])

    # Distance from VWAP
    distance = current_price - vwap
    distance_pct = (distance / vwap * 100) if vwap > 0 else 0

    # Position
    if abs(distance_pct) < 0.5:
        position = "At VWAP"
    elif distance > 0:
        position = "Above VWAP"
    else:
        position = "Below VWAP"

    return {
        "symbol": symbol,
        "vwap": round(vwap, 4),
        "current_price": round(current_price, 4),
        "distance": round(distance, 4),
        "distance_pct": round(distance_pct, 2),
        "position": position,
        "bars_analyzed": len(bars)
    }


async def get_volume_trend(symbol: str, bar_history: List[Dict[str, Any]], lookback: int = 50) -> Dict[str, Any]:
    """
    Analyze volume trend - is volume increasing or decreasing?

    Compares first half vs second half of period.

    Args:
        symbol: Stock symbol
        bar_history: Historical bars
        lookback: Number of bars to analyze (default 50)

    Returns:
        {
            "symbol": "BYND",
            "trend": "Increasing",      # Increasing/Decreasing/Flat
            "first_half_avg": 120000,
            "second_half_avg": 165000,
            "change_pct": +37.5,
            "recent_spike": True,       # Last 5 bars vs avg
            "interpretation": "Building momentum"
        }
    """
    if not bar_history:
        return {"error": f"No bar data for {symbol}"}

    # Get bars
    bars = bar_history[-lookback:] if len(bar_history) > lookback else bar_history

    if len(bars) < 10:
        return {"error": f"Need at least 10 bars for volume trend"}

    # Split into halves
    mid_point = len(bars) // 2
    first_half = bars[:mid_point]
    second_half = bars[mid_point:]

    # Calculate averages
    first_half_avg = statistics.mean([float(bar['volume']) for bar in first_half])
    second_half_avg = statistics.mean([float(bar['volume']) for bar in second_half])

    # Calculate change
    change_pct = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0

    # Determine trend
    if change_pct > 10:
        trend = "Increasing"
        interpretation = "Building momentum"
    elif change_pct < -10:
        trend = "Decreasing"
        interpretation = "Losing interest"
    else:
        trend = "Flat"
        interpretation = "Stable volume"

    # Check for recent spike (last 5 bars)
    recent_bars = bars[-5:]
    recent_avg = statistics.mean([float(bar['volume']) for bar in recent_bars])
    overall_avg = statistics.mean([float(bar['volume']) for bar in bars])
    recent_spike = recent_avg > overall_avg * 1.5

    if recent_spike:
        interpretation += " with recent spike"

    return {
        "symbol": symbol,
        "trend": trend,
        "first_half_avg": int(first_half_avg),
        "second_half_avg": int(second_half_avg),
        "change_pct": round(change_pct, 1),
        "recent_spike": recent_spike,
        "recent_avg": int(recent_avg),
        "overall_avg": int(overall_avg),
        "interpretation": interpretation,
        "bars_analyzed": len(bars)
    }
