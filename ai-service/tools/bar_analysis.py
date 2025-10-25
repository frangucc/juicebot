"""
Bar Data Analysis Tools

Uses in-memory bar data from the fast classifier to analyze price action.
"""

from typing import Dict, Any, List


def get_recent_bars_from_memory(symbol: str, classifier) -> List[Dict[str, Any]]:
    """
    Get recent bars from the in-memory classifier buffer.

    Returns the last N bars that have been fed via WebSocket.
    """
    if symbol not in classifier or not hasattr(classifier[symbol], 'bar_history'):
        return []

    return classifier[symbol].bar_history[-100:]  # Last 100 bars


async def analyze_price_levels(symbol: str, bars: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze price concentration and identify key levels from bar data.

    Returns:
        {
            "high": float,  # Highest price in dataset
            "low": float,   # Lowest price in dataset
            "concentration_above": [prices with most volume above current],
            "concentration_below": [prices with most volume below current],
            "resistance_levels": [price levels that could act as resistance],
            "support_levels": [price levels that could act as support],
            "next_bos_up": float or None,  # Next break of structure up
            "next_bos_down": float or None  # Next break of structure down
        }
    """
    if not bars:
        return {"error": "No bar data available"}

    # Extract prices and volumes
    highs = [float(bar['high']) for bar in bars]
    lows = [float(bar['low']) for bar in bars]
    closes = [float(bar['close']) for bar in bars]
    volumes = [int(bar['volume']) for bar in bars]

    current_price = closes[-1]
    data_high = max(highs)
    data_low = min(lows)

    # Find price concentration (group by price levels and sum volume)
    price_volume = {}
    for i, bar in enumerate(bars):
        # Round to nearest cent for grouping
        price_level = round(float(bar['close']), 2)
        if price_level not in price_volume:
            price_volume[price_level] = 0
        price_volume[price_level] += volumes[i]

    # Separate above and below current price
    above = {p: v for p, v in price_volume.items() if p > current_price}
    below = {p: v for p, v in price_volume.items() if p < current_price}

    # Top 3 concentration levels above
    concentration_above = sorted(above.items(), key=lambda x: x[1], reverse=True)[:3]
    concentration_above = [{"price": p, "volume": v} for p, v in concentration_above]

    # Top 3 concentration levels below
    concentration_below = sorted(below.items(), key=lambda x: x[1], reverse=True)[:3]
    concentration_below = [{"price": p, "volume": v} for p, v in concentration_below]

    # Find swing highs and lows (potential BoS levels)
    swing_highs = []
    swing_lows = []

    for i in range(5, len(bars) - 5):
        # Swing high: higher than 5 bars before and 5 bars after
        if all(highs[i] >= highs[j] for j in range(i-5, i)) and \
           all(highs[i] >= highs[j] for j in range(i+1, i+6)):
            swing_highs.append(highs[i])

        # Swing low: lower than 5 bars before and 5 bars after
        if all(lows[i] <= lows[j] for j in range(i-5, i)) and \
           all(lows[i] <= lows[j] for j in range(i+1, i+6)):
            swing_lows.append(lows[i])

    # Next BoS levels (closest swing high/low not yet broken)
    next_bos_up = min([h for h in swing_highs if h > current_price], default=None)
    next_bos_down = max([l for l in swing_lows if l < current_price], default=None)

    # Resistance = swing highs above current price
    resistance_levels = sorted([h for h in swing_highs if h > current_price])[:3]

    # Support = swing lows below current price
    support_levels = sorted([l for l in swing_lows if l < current_price], reverse=True)[:3]

    return {
        "symbol": symbol,
        "current_price": current_price,
        "high": data_high,
        "low": data_low,
        "range": round(data_high - data_low, 2),
        "concentration_above": concentration_above,
        "concentration_below": concentration_below,
        "resistance_levels": resistance_levels,
        "support_levels": support_levels,
        "next_bos_up": next_bos_up,
        "next_bos_down": next_bos_down
    }
