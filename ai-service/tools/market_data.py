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


async def detect_fvg(symbol: str, bar_history: List[Dict[str, Any]], lookback: int = 50) -> Dict[str, Any]:
    """
    Detect Fair Value Gaps (FVG) in recent price action with confidence scoring.

    DSL: [detect_fvg(AAPL, 50)]

    FVG Definition:
    - Bullish FVG: bar1.high < bar3.low (gap up)
    - Bearish FVG: bar1.low > bar3.high (gap down)

    Returns:
        {
            "patterns": [...],
            "data_quality": {
                "bars_analyzed": 150,
                "time_coverage_mins": 150,
                "quality_score": 7.5
            },
            "confidence": 8.2
        }
    """
    if not bar_history:
        return {"patterns": [], "data_quality": {"bars_analyzed": 0, "quality_score": 0}, "confidence": 0}

    bars = bar_history[-lookback:] if len(bar_history) > lookback else bar_history
    total_bars = len(bar_history)

    if len(bars) < 3:
        return {"patterns": [], "data_quality": {"bars_analyzed": len(bars), "quality_score": 1}, "confidence": 1}

    fvgs = []
    current_price = float(bars[-1]["close"])

    # Check every 3-bar sequence
    for i in range(len(bars) - 2):
        bar1 = bars[i]
        bar2 = bars[i + 1]
        bar3 = bars[i + 2]

        # Bullish FVG: gap between bar1.high and bar3.low
        if float(bar1["high"]) < float(bar3["low"]):
            gap_size = float(bar3["low"]) - float(bar1["high"])
            gap_pct = (gap_size / current_price) * 100

            # Calculate age (bars ago)
            bars_ago = len(bars) - (i + 2)

            fvg = {
                "type": "bullish",
                "top": float(bar3["low"]),
                "bottom": float(bar1["high"]),
                "bar_index": i,
                "bars_ago": bars_ago,
                "timestamp": bar3["timestamp"],
                "filled": False,
                "gap_size": round(gap_size, 4),
                "gap_pct": round(gap_pct, 2)
            }

            # Check if FVG was filled by subsequent bars
            filled_at = None
            for j in range(i + 3, len(bars)):
                if float(bars[j]["low"]) <= fvg["top"]:
                    fvg["filled"] = True
                    filled_at = j
                    break

            # Calculate confidence score (1-10)
            confidence = 10.0

            # Reduce confidence if gap is tiny (< 0.2% of price)
            if gap_pct < 0.2:
                confidence -= 3.0
            elif gap_pct < 0.3:
                confidence -= 1.5

            # Reduce confidence if very old
            if bars_ago > 40:
                confidence -= 2.0
            elif bars_ago > 20:
                confidence -= 1.0

            # Reduce confidence if gap formed on low volume
            if i + 2 < len(bars):
                avg_volume = sum(int(bars[max(0, i-5):i+3][k]["volume"]) for k in range(len(bars[max(0, i-5):i+3]))) / len(bars[max(0, i-5):i+3])
                if int(bar3["volume"]) < avg_volume * 0.8:
                    confidence -= 1.5

            # Distance from current price (relevance)
            distance_to_price = abs(current_price - (fvg["top"] + fvg["bottom"]) / 2)
            distance_pct = (distance_to_price / current_price) * 100
            if distance_pct > 5:  # More than 5% away
                confidence -= 2.0

            fvg["confidence"] = max(1.0, round(confidence, 1))

            if not fvg["filled"]:
                fvgs.append(fvg)

        # Bearish FVG: gap between bar1.low and bar3.high
        elif float(bar1["low"]) > float(bar3["high"]):
            gap_size = float(bar1["low"]) - float(bar3["high"])
            gap_pct = (gap_size / current_price) * 100
            bars_ago = len(bars) - (i + 2)

            fvg = {
                "type": "bearish",
                "top": float(bar1["low"]),
                "bottom": float(bar3["high"]),
                "bar_index": i,
                "bars_ago": bars_ago,
                "timestamp": bar3["timestamp"],
                "filled": False,
                "gap_size": round(gap_size, 4),
                "gap_pct": round(gap_pct, 2)
            }

            # Check if FVG was filled
            for j in range(i + 3, len(bars)):
                if float(bars[j]["high"]) >= fvg["bottom"]:
                    fvg["filled"] = True
                    break

            # Calculate confidence (same logic)
            confidence = 10.0
            if gap_pct < 0.2:
                confidence -= 3.0
            elif gap_pct < 0.3:
                confidence -= 1.5
            if bars_ago > 40:
                confidence -= 2.0
            elif bars_ago > 20:
                confidence -= 1.0
            distance_to_price = abs(current_price - (fvg["top"] + fvg["bottom"]) / 2)
            distance_pct = (distance_to_price / current_price) * 100
            if distance_pct > 5:
                confidence -= 2.0

            fvg["confidence"] = max(1.0, round(confidence, 1))

            if not fvg["filled"]:
                fvgs.append(fvg)

    # Sort by confidence (best first)
    fvgs.sort(key=lambda x: x["confidence"], reverse=True)

    # Calculate data quality score
    quality_score = min(10.0, (total_bars / 20))  # 1 point per 20 bars, cap at 10
    time_coverage_mins = total_bars  # Assuming 1-min bars

    # Overall confidence based on data quality and pattern count
    overall_confidence = quality_score
    if len(fvgs) > 0:
        overall_confidence = (quality_score + fvgs[0]["confidence"]) / 2

    return {
        "patterns": fvgs[:5],  # Return top 5
        "data_quality": {
            "bars_analyzed": len(bars),
            "total_bars_available": total_bars,
            "time_coverage_mins": time_coverage_mins,
            "quality_score": round(quality_score, 1)
        },
        "confidence": round(overall_confidence, 1)
    }


async def detect_bos(symbol: str, bar_history: List[Dict[str, Any]], lookback: int = 50) -> Dict[str, Any]:
    """
    Detect Break of Structure (BoS) with confidence scoring.

    DSL: [detect_bos(AAPL, 50)]

    BoS Definition:
    - Bullish BoS: Price breaks above previous swing high
    - Bearish BoS: Price breaks below previous swing low

    Returns:
        {
            "patterns": [
                {
                    "type": "bullish",
                    "break_level": 176.50,
                    "break_bar": 3,
                    "bars_ago": 12,
                    "timestamp": "2025-10-25T15:00:00Z",
                    "strength": "strong",
                    "confidence": 8.5
                },
                ...
            ],
            "data_quality": {...},
            "confidence": 8.2
        }
    """
    if not bar_history:
        return {"patterns": [], "data_quality": {}, "confidence": 0}

    bars = bar_history[-lookback:] if len(bar_history) > lookback else bar_history
    total_bars = len(bar_history)
    current_price = float(bars[-1]["close"])

    if len(bars) < 10:
        return {"patterns": [], "data_quality": {}, "confidence": 0}

    bos_list = []

    # Calculate average volume for the period
    avg_volume = sum(int(bar["volume"]) for bar in bars) / len(bars)

    # Find swing highs and lows
    for i in range(5, len(bars) - 5):
        bar = bars[i]

        # Check for swing high (local peak)
        is_swing_high = all(float(bars[j]["high"]) < float(bar["high"]) for j in range(i-5, i+5) if j != i)

        if is_swing_high:
            # Look for bullish BoS (break above this swing high)
            for j in range(i+1, min(i+20, len(bars))):
                if float(bars[j]["close"]) > float(bar["high"]):
                    break_volume = int(bars[j]["volume"])
                    break_size = float(bars[j]["close"]) - float(bar["high"])
                    break_pct = (break_size / float(bar["high"])) * 100
                    bars_ago = len(bars) - j

                    # Calculate confidence score (1-10)
                    confidence = 10.0

                    # Structure significance
                    if break_pct < 1.0:
                        confidence -= 2.0  # Minor break
                    elif break_pct < 2.0:
                        confidence -= 1.0  # Moderate break

                    # Volume strength
                    volume_ratio = break_volume / avg_volume if avg_volume > 0 else 1.0
                    if volume_ratio < 1.0:
                        confidence -= 2.5  # Weak volume
                        strength = "weak"
                    elif volume_ratio < 1.5:
                        confidence -= 1.0  # Normal volume
                        strength = "normal"
                    elif volume_ratio > 1.5:
                        confidence += 1.0  # Strong confirmation bonus
                        strength = "strong"
                    else:
                        strength = "normal"

                    # Age
                    if bars_ago > 30:
                        confidence -= 2.0
                    elif bars_ago > 15:
                        confidence -= 1.0

                    # Subsequent price action - check if price held above break level
                    retraced = False
                    if j < len(bars) - 1:
                        subsequent_bars = bars[j+1:]
                        lowest_after = min(float(b["low"]) for b in subsequent_bars)
                        if lowest_after < float(bar["high"]) * 0.995:  # Retraced >50% of break
                            confidence -= 2.0
                            retraced = True

                    bos_list.append({
                        "type": "bullish",
                        "break_level": float(bar["high"]),
                        "break_bar": j,
                        "bars_ago": bars_ago,
                        "timestamp": bars[j]["timestamp"],
                        "strength": strength,
                        "volume_ratio": round(volume_ratio, 2),
                        "break_pct": round(break_pct, 2),
                        "retraced": retraced,
                        "confidence": max(1.0, round(confidence, 1))
                    })
                    break

        # Check for swing low (local trough)
        is_swing_low = all(float(bars[j]["low"]) > float(bar["low"]) for j in range(i-5, i+5) if j != i)

        if is_swing_low:
            # Look for bearish BoS (break below this swing low)
            for j in range(i+1, min(i+20, len(bars))):
                if float(bars[j]["close"]) < float(bar["low"]):
                    break_volume = int(bars[j]["volume"])
                    break_size = float(bar["low"]) - float(bars[j]["close"])
                    break_pct = (break_size / float(bar["low"])) * 100
                    bars_ago = len(bars) - j

                    # Calculate confidence score (1-10)
                    confidence = 10.0

                    # Structure significance
                    if break_pct < 1.0:
                        confidence -= 2.0
                    elif break_pct < 2.0:
                        confidence -= 1.0

                    # Volume strength
                    volume_ratio = break_volume / avg_volume if avg_volume > 0 else 1.0
                    if volume_ratio < 1.0:
                        confidence -= 2.5
                        strength = "weak"
                    elif volume_ratio < 1.5:
                        confidence -= 1.0
                        strength = "normal"
                    elif volume_ratio > 1.5:
                        confidence += 1.0
                        strength = "strong"
                    else:
                        strength = "normal"

                    # Age
                    if bars_ago > 30:
                        confidence -= 2.0
                    elif bars_ago > 15:
                        confidence -= 1.0

                    # Subsequent price action - check if price held below break level
                    retraced = False
                    if j < len(bars) - 1:
                        subsequent_bars = bars[j+1:]
                        highest_after = max(float(b["high"]) for b in subsequent_bars)
                        if highest_after > float(bar["low"]) * 1.005:  # Retraced >50% of break
                            confidence -= 2.0
                            retraced = True

                    bos_list.append({
                        "type": "bearish",
                        "break_level": float(bar["low"]),
                        "break_bar": j,
                        "bars_ago": bars_ago,
                        "timestamp": bars[j]["timestamp"],
                        "strength": strength,
                        "volume_ratio": round(volume_ratio, 2),
                        "break_pct": round(break_pct, 2),
                        "retraced": retraced,
                        "confidence": max(1.0, round(confidence, 1))
                    })
                    break

    # Sort by confidence (best first)
    bos_list.sort(key=lambda x: x["confidence"], reverse=True)

    # Calculate data quality score
    quality_score = min(10.0, (total_bars / 20))
    time_coverage_mins = total_bars

    # Overall confidence
    overall_confidence = quality_score
    if len(bos_list) > 0:
        overall_confidence = (quality_score + bos_list[0]["confidence"]) / 2

    return {
        "patterns": bos_list[:5],  # Return top 5
        "data_quality": {
            "bars_analyzed": len(bars),
            "total_bars_available": total_bars,
            "time_coverage_mins": time_coverage_mins,
            "quality_score": round(quality_score, 1)
        },
        "confidence": round(overall_confidence, 1)
    }


async def detect_choch(symbol: str, bar_history: List[Dict[str, Any]], lookback: int = 50) -> Dict[str, Any]:
    """
    Detect Change of Character (CHoCH) with confidence scoring - potential trend reversal signal.

    DSL: [detect_choch(AAPL, 50)]

    CHoCH Definition:
    - In uptrend: Price breaks below previous swing low (structure broken against trend)
    - In downtrend: Price breaks above previous swing high (structure broken against trend)

    Returns:
        {
            "patterns": [
                {
                    "type": "bearish_to_bullish",
                    "break_level": 174.20,
                    "break_bar": 8,
                    "bars_ago": 15,
                    "timestamp": "2025-10-25T14:00:00Z",
                    "trend_strength": "strong",
                    "confidence": 7.8
                },
                ...
            ],
            "data_quality": {...},
            "confidence": 7.5
        }
    """
    if not bar_history:
        return {"patterns": [], "data_quality": {}, "confidence": 0}

    bars = bar_history[-lookback:] if len(bar_history) > lookback else bar_history
    total_bars = len(bar_history)

    if len(bars) < 15:
        return {"patterns": [], "data_quality": {}, "confidence": 0}

    choch_list = []

    # Calculate average volume for the period
    avg_volume = sum(int(bar["volume"]) for bar in bars) / len(bars)

    # Determine current trend by comparing recent highs/lows
    # FIXED: Was comparing [0] > [-1] which is backwards!
    # Should compare last bar vs first bar to see if trending up
    recent_highs = [float(bars[i]["high"]) for i in range(min(10, len(bars)))]
    recent_lows = [float(bars[i]["low"]) for i in range(min(10, len(bars)))]

    # FIX: Compare last bar to first bar (correct direction)
    is_uptrend = recent_highs[-1] > recent_highs[0] and recent_lows[-1] > recent_lows[0]
    is_downtrend = recent_highs[-1] < recent_highs[0] and recent_lows[-1] < recent_lows[0]

    # Calculate trend strength for confidence scoring
    if is_uptrend or is_downtrend:
        high_change = abs(recent_highs[-1] - recent_highs[0]) / recent_highs[0] * 100
        low_change = abs(recent_lows[-1] - recent_lows[0]) / recent_lows[0] * 100
        trend_change_pct = (high_change + low_change) / 2

        if trend_change_pct > 5.0:
            trend_strength = "strong"
        elif trend_change_pct > 2.0:
            trend_strength = "moderate"
        else:
            trend_strength = "weak"
    else:
        trend_strength = "ranging"

    # Look for CHoCH patterns
    for i in range(5, len(bars) - 5):
        bar = bars[i]

        # In uptrend, look for break below swing low (CHoCH to bearish)
        if is_uptrend:
            is_swing_low = all(float(bars[j]["low"]) > float(bar["low"]) for j in range(i-5, i+5) if j != i)
            if is_swing_low:
                for j in range(i+1, min(i+15, len(bars))):
                    if float(bars[j]["close"]) < float(bar["low"]):
                        break_volume = int(bars[j]["volume"])
                        bars_ago = len(bars) - j

                        # Calculate confidence score (1-10)
                        confidence = 10.0

                        # Trend strength before break
                        if trend_strength == "weak":
                            confidence -= 2.0  # Unreliable reversal
                        elif trend_strength == "moderate":
                            confidence -= 1.0

                        # Counter-trend volume (should be strong to confirm reversal)
                        volume_ratio = break_volume / avg_volume if avg_volume > 0 else 1.0
                        if volume_ratio < 1.2:
                            confidence -= 2.0  # Weak reversal
                        elif volume_ratio < 1.5:
                            confidence -= 1.0

                        choch_list.append({
                            "type": "bullish_to_bearish",
                            "break_level": float(bar["low"]),
                            "break_bar": j,
                            "bars_ago": bars_ago,
                            "timestamp": bars[j]["timestamp"],
                            "trend_strength": trend_strength,
                            "volume_ratio": round(volume_ratio, 2),
                            "confidence": max(1.0, round(confidence, 1))
                        })
                        break

        # In downtrend, look for break above swing high (CHoCH to bullish)
        if is_downtrend:
            is_swing_high = all(float(bars[j]["high"]) < float(bar["high"]) for j in range(i-5, i+5) if j != i)
            if is_swing_high:
                for j in range(i+1, min(i+15, len(bars))):
                    if float(bars[j]["close"]) > float(bar["high"]):
                        break_volume = int(bars[j]["volume"])
                        bars_ago = len(bars) - j

                        # Calculate confidence score (1-10)
                        confidence = 10.0

                        # Trend strength before break
                        if trend_strength == "weak":
                            confidence -= 2.0
                        elif trend_strength == "moderate":
                            confidence -= 1.0

                        # Counter-trend volume
                        volume_ratio = break_volume / avg_volume if avg_volume > 0 else 1.0
                        if volume_ratio < 1.2:
                            confidence -= 2.0
                        elif volume_ratio < 1.5:
                            confidence -= 1.0

                        choch_list.append({
                            "type": "bearish_to_bullish",
                            "break_level": float(bar["high"]),
                            "break_bar": j,
                            "bars_ago": bars_ago,
                            "timestamp": bars[j]["timestamp"],
                            "trend_strength": trend_strength,
                            "volume_ratio": round(volume_ratio, 2),
                            "confidence": max(1.0, round(confidence, 1))
                        })
                        break

    # Sort by confidence (best first)
    choch_list.sort(key=lambda x: x["confidence"], reverse=True)

    # Calculate data quality score
    quality_score = min(10.0, (total_bars / 20))
    time_coverage_mins = total_bars

    # Overall confidence
    overall_confidence = quality_score
    if len(choch_list) > 0:
        overall_confidence = (quality_score + choch_list[0]["confidence"]) / 2

    return {
        "patterns": choch_list[:3],  # Return top 3
        "data_quality": {
            "bars_analyzed": len(bars),
            "total_bars_available": total_bars,
            "time_coverage_mins": time_coverage_mins,
            "quality_score": round(quality_score, 1)
        },
        "confidence": round(overall_confidence, 1)
    }


async def detect_pattern_confluence(
    symbol: str,
    bar_history: List[Dict[str, Any]],
    lookback: int = 50
) -> Dict[str, Any]:
    """
    Detect confluence zones where multiple SMC patterns align.

    Confluence occurs when:
    - FVG + BoS at similar price levels
    - Multiple patterns of same direction
    - High volume confirmation

    Returns:
        {
            "confluence_zones": [
                {
                    "price_level": 0.5670,
                    "patterns": ["bullish_fvg", "bullish_bos"],
                    "confidence": 9.2,
                    "strength": "strong",
                    "description": "High confluence - FVG + BoS alignment"
                }
            ],
            "best_zone": {...},
            "overall_confidence": 9.2
        }
    """
    if not bar_history or len(bar_history) < 10:
        return {"confluence_zones": [], "best_zone": None, "overall_confidence": 0}

    # Get all pattern types
    fvg_result = await detect_fvg(symbol, bar_history, lookback)
    bos_result = await detect_bos(symbol, bar_history, lookback)
    choch_result = await detect_choch(symbol, bar_history, lookback)

    fvgs = fvg_result.get("patterns", [])
    bos_patterns = bos_result.get("patterns", [])
    choch_patterns = choch_result.get("patterns", [])

    current_price = float(bar_history[-1]["close"])
    confluence_zones = []

    # Check FVG + BoS confluence
    for fvg in fvgs:
        if fvg["confidence"] < 5.0:  # Skip low confidence patterns
            continue

        fvg_mid = (fvg["top"] + fvg["bottom"]) / 2
        fvg_type = fvg["type"]  # "bullish" or "bearish"

        # Look for BoS patterns near this FVG
        for bos in bos_patterns:
            if bos["confidence"] < 5.0:
                continue

            bos_level = bos["break_level"]
            distance_pct = abs(bos_level - fvg_mid) / current_price * 100

            # If within 1% of each other and same direction, it's confluence
            if distance_pct < 1.0:
                # Check if directions align
                if (fvg_type == "bullish" and bos["type"] == "bullish") or \
                   (fvg_type == "bearish" and bos["type"] == "bearish"):

                    # Calculate confluence confidence
                    base_confidence = (fvg["confidence"] + bos["confidence"]) / 2
                    confluence_boost = 2.0  # Bonus for confluence

                    # Volume confirmation bonus
                    volume_bonus = 0
                    if bos.get("volume_ratio", 0) > 1.5:
                        volume_bonus = 1.0

                    confluence_confidence = min(10.0, base_confidence + confluence_boost + volume_bonus)

                    # Determine strength
                    if confluence_confidence >= 9.0:
                        strength = "very_strong"
                    elif confluence_confidence >= 8.0:
                        strength = "strong"
                    elif confluence_confidence >= 7.0:
                        strength = "moderate"
                    else:
                        strength = "weak"

                    confluence_zones.append({
                        "price_level": round(fvg_mid, 4),
                        "patterns": [f"{fvg_type}_fvg", f"{bos['type']}_bos"],
                        "confidence": round(confluence_confidence, 1),
                        "strength": strength,
                        "distance_from_price": round(abs(current_price - fvg_mid), 4),
                        "distance_pct": round(abs(current_price - fvg_mid) / current_price * 100, 2),
                        "fvg_details": {
                            "top": fvg["top"],
                            "bottom": fvg["bottom"],
                            "confidence": fvg["confidence"],
                            "bars_ago": fvg["bars_ago"]
                        },
                        "bos_details": {
                            "break_level": bos["break_level"],
                            "confidence": bos["confidence"],
                            "volume_ratio": bos.get("volume_ratio", 1.0),
                            "bars_ago": bos["bars_ago"]
                        },
                        "description": f"{strength.replace('_', ' ').title()} confluence - {fvg_type.title()} FVG + BoS alignment"
                    })

    # Check FVG + CHoCH confluence (reversal zones)
    for fvg in fvgs:
        if fvg["confidence"] < 5.0:
            continue

        fvg_mid = (fvg["top"] + fvg["bottom"]) / 2
        fvg_type = fvg["type"]

        for choch in choch_patterns:
            if choch["confidence"] < 5.0:
                continue

            choch_level = choch["break_level"]
            distance_pct = abs(choch_level - fvg_mid) / current_price * 100

            if distance_pct < 1.0:
                # CHoCH should align with FVG direction (both bullish or both bearish)
                choch_direction = "bullish" if "bullish" in choch["type"] else "bearish"

                if fvg_type == choch_direction:
                    base_confidence = (fvg["confidence"] + choch["confidence"]) / 2
                    confluence_boost = 1.5  # CHoCH confluence is slightly less strong

                    volume_bonus = 0
                    if choch.get("volume_ratio", 0) > 1.5:
                        volume_bonus = 0.5

                    confluence_confidence = min(10.0, base_confidence + confluence_boost + volume_bonus)

                    if confluence_confidence >= 8.5:
                        strength = "strong"
                    elif confluence_confidence >= 7.0:
                        strength = "moderate"
                    else:
                        strength = "weak"

                    confluence_zones.append({
                        "price_level": round(fvg_mid, 4),
                        "patterns": [f"{fvg_type}_fvg", choch["type"]],
                        "confidence": round(confluence_confidence, 1),
                        "strength": strength,
                        "distance_from_price": round(abs(current_price - fvg_mid), 4),
                        "distance_pct": round(abs(current_price - fvg_mid) / current_price * 100, 2),
                        "fvg_details": {
                            "top": fvg["top"],
                            "bottom": fvg["bottom"],
                            "confidence": fvg["confidence"],
                            "bars_ago": fvg["bars_ago"]
                        },
                        "choch_details": {
                            "break_level": choch["break_level"],
                            "confidence": choch["confidence"],
                            "trend_strength": choch.get("trend_strength", "unknown"),
                            "bars_ago": choch["bars_ago"]
                        },
                        "description": f"{strength.title()} reversal zone - {fvg_type.title()} FVG + CHoCH"
                    })

    # Sort by confidence
    confluence_zones.sort(key=lambda x: x["confidence"], reverse=True)

    # Get best zone
    best_zone = confluence_zones[0] if confluence_zones else None
    overall_confidence = best_zone["confidence"] if best_zone else 0

    return {
        "confluence_zones": confluence_zones[:5],  # Return top 5
        "best_zone": best_zone,
        "overall_confidence": round(overall_confidence, 1),
        "data_quality": fvg_result.get("data_quality", {})
    }
