"""
Market Data Tools

These tools use in-memory bar data from the fast classifier (WebSocket feed).
All tools follow the DSL naming convention: tool_name(params)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


async def get_current_price(symbol: str, bar_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get the current price and latest bar data for a symbol.

    DSL: [current_price(AAPL)]

    Returns:
        {
            "symbol": "AAPL",
            "price": 175.42,
            "open": 174.20,
            "high": 176.50,
            "low": 174.00,
            "volume": 52300000,
            "timestamp": "2025-10-25T15:30:00Z"
        }
    """
    if not bar_history:
        return {"error": f"No bar data available for {symbol}"}

    latest = bar_history[-1]
    return {
        "symbol": symbol,
        "price": float(latest["close"]),
        "open": float(latest["open"]),
        "high": float(latest["high"]),
        "low": float(latest["low"]),
        "volume": int(latest["volume"]),
        "timestamp": latest["timestamp"]
    }


async def get_volume_stats(symbol: str, bar_history: List[Dict[str, Any]], period: str = "today") -> Dict[str, Any]:
    """
    Get volume statistics for a symbol.

    DSL: [volume_stats(AAPL, today)]
    DSL: [volume_last(5)] - shorthand for last N bars

    Args:
        period: "today", "1h", "20bars" (default: "today")

    Returns:
        {
            "symbol": "AAPL",
            "current_volume": 52300000,
            "avg_volume_20d": 45000000,
            "relative_volume": 1.16,
            "volume_trend": "increasing"
        }
    """
    if not bar_history:
        return {"error": f"No bar data available for {symbol}"}

    # Parse period
    if period == "today":
        limit = min(390, len(bar_history))  # Trading day minutes
    elif period.endswith("bars"):
        limit = min(int(period.replace("bars", "")), len(bar_history))
    elif period.endswith("h"):
        limit = min(int(period.replace("h", "")) * 60, len(bar_history))
    else:
        limit = min(20, len(bar_history))

    # Use last N bars from history
    bars = bar_history[-limit:] if limit < len(bar_history) else bar_history

    volumes = [int(bar["volume"]) for bar in bars]
    current_volume = volumes[-1]
    avg_volume = sum(volumes) / len(volumes)
    relative_volume = current_volume / avg_volume if avg_volume > 0 else 0

    # Determine trend
    if len(volumes) >= 5:
        recent_avg = sum(volumes[-5:]) / 5
        older_avg = sum(volumes[-10:-5]) / 5 if len(volumes) >= 10 else sum(volumes[:-5]) / max(1, len(volumes) - 5)
        volume_trend = "increasing" if recent_avg > older_avg else "decreasing"
    else:
        volume_trend = "stable"

    return {
        "symbol": symbol,
        "current_volume": current_volume,
        "avg_volume": round(avg_volume),
        "relative_volume": round(relative_volume, 2),
        "volume_trend": volume_trend
    }


async def get_price_range(symbol: str, bar_history: List[Dict[str, Any]], period: str = "today") -> Dict[str, Any]:
    """
    Get price range (high/low) for a symbol.

    DSL: [price_range(AAPL, today)]
    DSL: [price_high(today)] - shorthand for just high
    DSL: [price_low(today)] - shorthand for just low

    Returns:
        {
            "symbol": "AAPL",
            "high": 176.50,
            "low": 174.20,
            "range": 2.30,
            "range_pct": 1.31,
            "current": 175.42
        }
    """
    if not bar_history:
        return {"error": f"No bar data available for {symbol}"}

    # Parse period
    if period == "today":
        limit = min(390, len(bar_history))
    elif period.endswith("bars"):
        limit = min(int(period.replace("bars", "")), len(bar_history))
    else:
        limit = min(20, len(bar_history))

    bars = bar_history[-limit:] if limit < len(bar_history) else bar_history

    high = max(float(bar["high"]) for bar in bars)
    low = min(float(bar["low"]) for bar in bars)
    current = float(bars[-1]["close"])
    range_val = high - low
    range_pct = (range_val / low) * 100 if low > 0 else 0

    return {
        "symbol": symbol,
        "high": high,
        "low": low,
        "range": round(range_val, 2),
        "range_pct": round(range_pct, 2),
        "current": current
    }


async def get_historical_bars(symbol: str, bar_history: List[Dict[str, Any]], limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get raw OHLCV bar data for analysis.

    DSL: [get_bars(AAPL, 100)]

    Returns: List of bars with timestamp, open, high, low, close, volume
    """
    if not bar_history:
        return []

    # Return last N bars from history
    return bar_history[-limit:] if len(bar_history) > limit else bar_history


async def detect_fvg(symbol: str, bar_history: List[Dict[str, Any]], lookback: int = 50) -> List[Dict[str, Any]]:
    """
    Detect Fair Value Gaps (FVG) in recent price action.

    DSL: [detect_fvg(AAPL, 50)]

    FVG Definition:
    - Bullish FVG: bar1.high < bar3.low (gap up)
    - Bearish FVG: bar1.low > bar3.high (gap down)

    Returns:
        [
            {
                "type": "bullish",
                "top": 175.45,
                "bottom": 175.20,
                "bar_index": 5,
                "timestamp": "2025-10-25T14:30:00Z",
                "filled": false,
                "gap_size": 0.25
            },
            ...
        ]
    """
    if not bar_history:
        return []

    bars = bar_history[-lookback:] if len(bar_history) > lookback else bar_history

    if len(bars) < 3:
        return []

    fvgs = []

    # Check every 3-bar sequence
    for i in range(len(bars) - 2):
        bar1 = bars[i]
        bar2 = bars[i + 1]
        bar3 = bars[i + 2]

        # Bullish FVG: gap between bar1.high and bar3.low
        if float(bar1["high"]) < float(bar3["low"]):
            gap_size = float(bar3["low"]) - float(bar1["high"])
            fvg = {
                "type": "bullish",
                "top": float(bar3["low"]),
                "bottom": float(bar1["high"]),
                "bar_index": i,
                "timestamp": bar3["timestamp"],
                "filled": False,
                "gap_size": round(gap_size, 4)
            }

            # Check if FVG was filled by subsequent bars
            for j in range(i + 3, len(bars)):
                if float(bars[j]["low"]) <= fvg["top"]:
                    fvg["filled"] = True
                    break

            fvgs.append(fvg)

        # Bearish FVG: gap between bar1.low and bar3.high
        elif float(bar1["low"]) > float(bar3["high"]):
            gap_size = float(bar1["low"]) - float(bar3["high"])
            fvg = {
                "type": "bearish",
                "top": float(bar1["low"]),
                "bottom": float(bar3["high"]),
                "bar_index": i,
                "timestamp": bar3["timestamp"],
                "filled": False,
                "gap_size": round(gap_size, 4)
            }

            # Check if FVG was filled
            for j in range(i + 3, len(bars)):
                if float(bars[j]["high"]) >= fvg["bottom"]:
                    fvg["filled"] = True
                    break

            fvgs.append(fvg)

    # Return only unfilled FVGs (most relevant for trading)
    return [fvg for fvg in fvgs if not fvg["filled"]]


async def detect_bos(symbol: str, bar_history: List[Dict[str, Any]], lookback: int = 50) -> List[Dict[str, Any]]:
    """
    Detect Break of Structure (BoS) - trend continuation signal.

    DSL: [detect_bos(AAPL, 50)]

    BoS Definition:
    - Bullish BoS: Price breaks above previous swing high
    - Bearish BoS: Price breaks below previous swing low

    Returns:
        [
            {
                "type": "bullish",
                "break_level": 176.50,
                "break_bar": 3,
                "timestamp": "2025-10-25T15:00:00Z",
                "strength": "strong"  # based on volume
            },
            ...
        ]
    """
    if not bar_history:
        return []

    bars = bar_history[-lookback:] if len(bar_history) > lookback else bar_history

    if len(bars) < 10:
        return []

    bos_list = []

    # Find swing highs and lows
    for i in range(5, len(bars) - 5):
        bar = bars[i]

        # Check for swing high (local peak)
        is_swing_high = all(float(bars[j]["high"]) < float(bar["high"]) for j in range(i-5, i+5) if j != i)

        if is_swing_high:
            # Look for bullish BoS (break above this swing high)
            for j in range(i+1, min(i+20, len(bars))):
                if float(bars[j]["close"]) > float(bar["high"]):
                    volume_strength = "strong" if int(bars[j]["volume"]) > int(bars[i]["volume"]) * 1.5 else "normal"
                    bos_list.append({
                        "type": "bullish",
                        "break_level": float(bar["high"]),
                        "break_bar": j,
                        "timestamp": bars[j]["timestamp"],
                        "strength": volume_strength
                    })
                    break

        # Check for swing low (local trough)
        is_swing_low = all(float(bars[j]["low"]) > float(bar["low"]) for j in range(i-5, i+5) if j != i)

        if is_swing_low:
            # Look for bearish BoS (break below this swing low)
            for j in range(i+1, min(i+20, len(bars))):
                if float(bars[j]["close"]) < float(bar["low"]):
                    volume_strength = "strong" if int(bars[j]["volume"]) > int(bars[i]["volume"]) * 1.5 else "normal"
                    bos_list.append({
                        "type": "bearish",
                        "break_level": float(bar["low"]),
                        "break_bar": j,
                        "timestamp": bars[j]["timestamp"],
                        "strength": volume_strength
                    })
                    break

    # Return most recent BoS events
    return bos_list[:5]


async def detect_choch(symbol: str, bar_history: List[Dict[str, Any]], lookback: int = 50) -> List[Dict[str, Any]]:
    """
    Detect Change of Character (CHoCH) - potential trend reversal signal.

    DSL: [detect_choch(AAPL, 50)]

    CHoCH Definition:
    - In uptrend: Price breaks below previous swing low (structure broken against trend)
    - In downtrend: Price breaks above previous swing high (structure broken against trend)

    Returns:
        [
            {
                "type": "bearish_to_bullish",
                "break_level": 174.20,
                "break_bar": 8,
                "timestamp": "2025-10-25T14:00:00Z",
                "significance": "high"
            },
            ...
        ]
    """
    if not bar_history:
        return []

    bars = bar_history[-lookback:] if len(bar_history) > lookback else bar_history

    if len(bars) < 15:
        return []

    choch_list = []

    # Determine current trend by comparing recent highs/lows
    recent_highs = [float(bars[i]["high"]) for i in range(min(10, len(bars)))]
    recent_lows = [float(bars[i]["low"]) for i in range(min(10, len(bars)))]

    is_uptrend = recent_highs[0] > recent_highs[-1] and recent_lows[0] > recent_lows[-1]
    is_downtrend = recent_highs[0] < recent_highs[-1] and recent_lows[0] < recent_lows[-1]

    # Look for CHoCH patterns
    for i in range(5, len(bars) - 5):
        bar = bars[i]

        # In uptrend, look for break below swing low (CHoCH to bearish)
        if is_uptrend:
            is_swing_low = all(float(bars[j]["low"]) > float(bar["low"]) for j in range(i-5, i+5) if j != i)
            if is_swing_low:
                for j in range(i+1, min(i+15, len(bars))):
                    if float(bars[j]["close"]) < float(bar["low"]):
                        choch_list.append({
                            "type": "bullish_to_bearish",
                            "break_level": float(bar["low"]),
                            "break_bar": j,
                            "timestamp": bars[j]["timestamp"],
                            "significance": "high"
                        })
                        break

        # In downtrend, look for break above swing high (CHoCH to bullish)
        if is_downtrend:
            is_swing_high = all(float(bars[j]["high"]) < float(bar["high"]) for j in range(i-5, i+5) if j != i)
            if is_swing_high:
                for j in range(i+1, min(i+15, len(bars))):
                    if float(bars[j]["close"]) > float(bar["high"]):
                        choch_list.append({
                            "type": "bearish_to_bullish",
                            "break_level": float(bar["high"]),
                            "break_bar": j,
                            "timestamp": bars[j]["timestamp"],
                            "significance": "high"
                        })
                        break

    return choch_list[:3]
