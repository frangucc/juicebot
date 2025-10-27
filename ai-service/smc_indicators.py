"""
SMC Indicators - Native Pattern Detection for Chart Overlays
=============================================================
Professional Break of Structure (BoS) and Change of Character (CHoCH) detection.
These indicators run independently and provide real-time chart overlays.

Pattern Logic:
--------------
BoS (Break of Structure):
  - Bullish: Price breaks above previous swing high → Continuation upward
  - Bearish: Price breaks below previous swing low → Continuation downward
  - Target: Previous swing range + extension (typically 1:1 or higher)
  - Stays valid until: Price breaks back below/above the BoS level

CHoCH (Change of Character):
  - Bullish CHoCH: In downtrend, price breaks above previous lower high → Reversal
  - Bearish CHoCH: In uptrend, price breaks below previous higher low → Reversal
  - Target: Return to previous high/low (mean reversion)
  - Stays valid until: Confirmed by subsequent structure or violated
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SwingPoint:
    """Represents a swing high or swing low."""
    price: float
    index: int
    timestamp: str
    type: str  # "high" or "low"
    bars_ago: int


@dataclass
class BoSLevel:
    """Break of Structure level for chart display."""
    price: float
    type: str  # "bullish" or "bearish"
    formed_at: str
    bars_ago: int
    target_price: float
    stop_invalidation: float
    is_valid: bool
    confidence: float
    volume_ratio: float
    swing_range: float  # Distance of the swing that was broken


@dataclass
class CHoCHLevel:
    """Change of Character level for chart display."""
    price: float
    type: str  # "bullish_to_bearish" or "bearish_to_bullish"
    formed_at: str
    bars_ago: int
    target_price: float
    stop_invalidation: float
    is_valid: bool
    confidence: float
    volume_ratio: float
    trend_strength: str  # "strong", "moderate", "weak"


class SMCIndicators:
    """
    Native SMC pattern detection for real-time chart overlays.
    No AI needed - pure algorithmic detection.
    """

    def __init__(self):
        self.bos_levels: List[BoSLevel] = []
        self.choch_levels: List[CHoCHLevel] = []
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []

    def find_swing_points(self, bars: List[Dict[str, Any]], lookback: int = 5) -> tuple:
        """
        Identify swing highs and swing lows using pivot detection.

        Args:
            bars: List of OHLCV bars
            lookback: Number of bars on each side to confirm pivot (default: 5)

        Returns:
            (swing_highs, swing_lows) as lists of SwingPoint objects
        """
        if len(bars) < lookback * 2 + 1:
            return [], []

        swing_highs = []
        swing_lows = []

        # Check each bar to see if it's a pivot
        for i in range(lookback, len(bars) - lookback):
            bar = bars[i]
            bar_high = float(bar["high"])
            bar_low = float(bar["low"])

            # Check for swing high (highest point in range)
            start_idx = max(0, i - lookback)
            end_idx = min(len(bars), i + lookback + 1)

            is_swing_high = all(
                bar_high > float(bars[j]["high"])
                for j in range(start_idx, end_idx)
                if j != i and 0 <= j < len(bars)
            )

            if is_swing_high:
                swing_highs.append(SwingPoint(
                    price=bar_high,
                    index=i,
                    timestamp=bar["timestamp"],
                    type="high",
                    bars_ago=len(bars) - i
                ))

            # Check for swing low (lowest point in range)
            is_swing_low = all(
                bar_low < float(bars[j]["low"])
                for j in range(start_idx, end_idx)
                if j != i and 0 <= j < len(bars)
            )

            if is_swing_low:
                swing_lows.append(SwingPoint(
                    price=bar_low,
                    index=i,
                    timestamp=bar["timestamp"],
                    type="low",
                    bars_ago=len(bars) - i
                ))

        return swing_highs, swing_lows

    def detect_bos(
        self,
        bars: List[Dict[str, Any]],
        lookback: int = 100
    ) -> List[BoSLevel]:
        """
        Detect Break of Structure patterns.

        Logic:
        - Find swing highs/lows
        - Detect when price breaks above/below these levels
        - Calculate target based on swing range
        - Determine invalidation level

        Returns:
            List of active BoS levels for chart display
        """
        if len(bars) < 20:
            return []

        recent_bars = bars[-lookback:] if len(bars) > lookback else bars
        current_price = float(recent_bars[-1]["close"])

        # Find swing points
        swing_highs, swing_lows = self.find_swing_points(recent_bars)
        print(f"[BoS Detection] Found {len(swing_highs)} swing highs and {len(swing_lows)} swing lows in {len(recent_bars)} bars")

        bos_levels = []

        # Calculate average volume
        avg_volume = sum(float(bar["volume"]) for bar in recent_bars) / len(recent_bars)

        # Look for bullish BoS (break above swing high)
        for i, swing_high in enumerate(swing_highs):
            swing_price = swing_high.price
            swing_index = swing_high.index

            # Check if price broke above this swing high
            for j in range(swing_index + 1, len(recent_bars)):
                bar = recent_bars[j]
                if float(bar["close"]) > swing_price:
                    # BoS confirmed!
                    break_volume = float(bar["volume"])
                    volume_ratio = break_volume / avg_volume if avg_volume > 0 else 1.0

                    # Calculate swing range (for target projection)
                    # Find the low before this swing high
                    prev_low = min(
                        float(recent_bars[k]["low"])
                        for k in range(max(0, swing_index - 20), swing_index)
                    ) if swing_index > 0 else swing_price * 0.99

                    swing_range = swing_price - prev_low

                    # Target: Project swing range upward (1:1 extension)
                    target_price = swing_price + swing_range

                    # Invalidation: Break back below swing high with conviction
                    stop_invalidation = swing_price * 0.998  # 0.2% below

                    # Calculate confidence
                    confidence = self._calculate_bos_confidence(
                        swing_range=swing_range,
                        volume_ratio=volume_ratio,
                        bars_since_break=len(recent_bars) - j,
                        current_price=current_price,
                        bos_price=swing_price
                    )

                    # Check if still valid (price hasn't broken back below)
                    is_valid = current_price > stop_invalidation

                    if is_valid:
                        bos_levels.append(BoSLevel(
                            price=swing_price,
                            type="bullish",
                            formed_at=bar["timestamp"],
                            bars_ago=len(recent_bars) - j,
                            target_price=target_price,
                            stop_invalidation=stop_invalidation,
                            is_valid=True,
                            confidence=confidence,
                            volume_ratio=volume_ratio,
                            swing_range=swing_range
                        ))

                    break  # Only detect first break

        # Look for bearish BoS (break below swing low)
        for swing_low in swing_lows:
            swing_price = swing_low.price
            swing_index = swing_low.index

            # Check if price broke below this swing low
            for j in range(swing_index + 1, len(recent_bars)):
                bar = recent_bars[j]
                if float(bar["close"]) < swing_price:
                    # BoS confirmed!
                    break_volume = float(bar["volume"])
                    volume_ratio = break_volume / avg_volume if avg_volume > 0 else 1.0

                    # Calculate swing range
                    prev_high = max(
                        float(recent_bars[k]["high"])
                        for k in range(max(0, swing_index - 20), swing_index)
                    ) if swing_index > 0 else swing_price * 1.01

                    swing_range = prev_high - swing_price

                    # Target: Project swing range downward
                    target_price = swing_price - swing_range

                    # Invalidation: Break back above swing low
                    stop_invalidation = swing_price * 1.002  # 0.2% above

                    confidence = self._calculate_bos_confidence(
                        swing_range=swing_range,
                        volume_ratio=volume_ratio,
                        bars_since_break=len(recent_bars) - j,
                        current_price=current_price,
                        bos_price=swing_price
                    )

                    is_valid = current_price < stop_invalidation

                    if is_valid:
                        bos_levels.append(BoSLevel(
                            price=swing_price,
                            type="bearish",
                            formed_at=bar["timestamp"],
                            bars_ago=len(recent_bars) - j,
                            target_price=target_price,
                            stop_invalidation=stop_invalidation,
                            is_valid=True,
                            confidence=confidence,
                            volume_ratio=volume_ratio,
                            swing_range=swing_range
                        ))

                    break

        # Sort by recency and confidence
        bos_levels.sort(key=lambda x: (x.bars_ago, -x.confidence))

        # Return top 5 most relevant
        return bos_levels[:5]

    def detect_choch(
        self,
        bars: List[Dict[str, Any]],
        lookback: int = 100
    ) -> List[CHoCHLevel]:
        """
        Detect Change of Character patterns (trend reversals).

        Logic:
        - Identify trend direction
        - Detect when price breaks structure AGAINST trend
        - Calculate mean reversion target
        - Determine invalidation level

        Returns:
            List of active CHoCH levels for chart display
        """
        if len(bars) < 30:
            return []

        recent_bars = bars[-lookback:] if len(bars) > lookback else bars
        current_price = float(recent_bars[-1]["close"])

        # Determine trend
        trend_window = min(20, len(recent_bars))
        recent_highs = [float(recent_bars[i]["high"]) for i in range(-trend_window, 0)]
        recent_lows = [float(recent_bars[i]["low"]) for i in range(-trend_window, 0)]

        # Trend detection: Compare first vs last
        is_uptrend = recent_highs[-1] > recent_highs[0] and recent_lows[-1] > recent_lows[0]
        is_downtrend = recent_highs[-1] < recent_highs[0] and recent_lows[-1] < recent_lows[0]

        # Calculate trend strength
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

        choch_levels = []
        avg_volume = sum(float(bar["volume"]) for bar in recent_bars) / len(recent_bars)

        # Find swing points
        swing_highs, swing_lows = self.find_swing_points(recent_bars, lookback=5)

        # In UPTREND, look for break BELOW previous higher low (CHoCH to bearish)
        if is_uptrend:
            for swing_low in swing_lows:
                swing_price = swing_low.price
                swing_index = swing_low.index

                # Must be a recent swing (part of uptrend)
                if len(recent_bars) - swing_index > 50:
                    continue

                # Check if price broke below this higher low
                for j in range(swing_index + 1, len(recent_bars)):
                    bar = recent_bars[j]
                    if float(bar["close"]) < swing_price:
                        # CHoCH confirmed!
                        break_volume = float(bar["volume"])
                        volume_ratio = break_volume / avg_volume if avg_volume > 0 else 1.0

                        # Target: Mean reversion to recent high
                        target_price = max(recent_highs[-20:])

                        # Invalidation: New higher high formed
                        stop_invalidation = max(recent_highs[-10:]) * 1.002

                        confidence = self._calculate_choch_confidence(
                            trend_strength=trend_strength,
                            volume_ratio=volume_ratio,
                            bars_since_break=len(recent_bars) - j
                        )

                        is_valid = current_price < stop_invalidation

                        if is_valid:
                            choch_levels.append(CHoCHLevel(
                                price=swing_price,
                                type="bullish_to_bearish",
                                formed_at=bar["timestamp"],
                                bars_ago=len(recent_bars) - j,
                                target_price=target_price,
                                stop_invalidation=stop_invalidation,
                                is_valid=True,
                                confidence=confidence,
                                volume_ratio=volume_ratio,
                                trend_strength=trend_strength
                            ))

                        break

        # In DOWNTREND, look for break ABOVE previous lower high (CHoCH to bullish)
        if is_downtrend:
            for swing_high in swing_highs:
                swing_price = swing_high.price
                swing_index = swing_high.index

                if len(recent_bars) - swing_index > 50:
                    continue

                for j in range(swing_index + 1, len(recent_bars)):
                    bar = recent_bars[j]
                    if float(bar["close"]) > swing_price:
                        # CHoCH confirmed!
                        break_volume = float(bar["volume"])
                        volume_ratio = break_volume / avg_volume if avg_volume > 0 else 1.0

                        # Target: Mean reversion to recent low
                        target_price = min(recent_lows[-20:])

                        # Invalidation: New lower low formed
                        stop_invalidation = min(recent_lows[-10:]) * 0.998

                        confidence = self._calculate_choch_confidence(
                            trend_strength=trend_strength,
                            volume_ratio=volume_ratio,
                            bars_since_break=len(recent_bars) - j
                        )

                        is_valid = current_price > stop_invalidation

                        if is_valid:
                            choch_levels.append(CHoCHLevel(
                                price=swing_price,
                                type="bearish_to_bullish",
                                formed_at=bar["timestamp"],
                                bars_ago=len(recent_bars) - j,
                                target_price=target_price,
                                stop_invalidation=stop_invalidation,
                                is_valid=True,
                                confidence=confidence,
                                volume_ratio=volume_ratio,
                                trend_strength=trend_strength
                            ))

                        break

        # Sort by recency and confidence
        choch_levels.sort(key=lambda x: (x.bars_ago, -x.confidence))

        return choch_levels[:3]

    def _calculate_bos_confidence(
        self,
        swing_range: float,
        volume_ratio: float,
        bars_since_break: int,
        current_price: float,
        bos_price: float
    ) -> float:
        """Calculate confidence score for BoS (1-10 scale)."""
        confidence = 10.0

        # Swing range significance
        range_pct = (swing_range / bos_price) * 100
        if range_pct < 1.0:
            confidence -= 2.0  # Small swing = less significant
        elif range_pct < 2.0:
            confidence -= 1.0

        # Volume confirmation
        if volume_ratio < 1.0:
            confidence -= 2.5  # Weak volume
        elif volume_ratio < 1.5:
            confidence -= 1.0
        elif volume_ratio > 2.0:
            confidence += 1.0  # Strong volume bonus

        # Age (recency)
        if bars_since_break > 30:
            confidence -= 2.0  # Old break
        elif bars_since_break > 15:
            confidence -= 1.0

        # Price respect (still holding above/below)
        distance_pct = abs(current_price - bos_price) / bos_price * 100
        if distance_pct < 0.5:
            confidence -= 1.0  # Too close, might violate soon

        return max(1.0, min(10.0, round(confidence, 1)))

    def _calculate_choch_confidence(
        self,
        trend_strength: str,
        volume_ratio: float,
        bars_since_break: int
    ) -> float:
        """Calculate confidence score for CHoCH (1-10 scale)."""
        confidence = 10.0

        # Trend strength (stronger trend = more significant reversal)
        if trend_strength == "weak":
            confidence -= 2.0
        elif trend_strength == "moderate":
            confidence -= 1.0
        elif trend_strength == "ranging":
            confidence -= 3.0  # Unreliable in ranging market

        # Volume confirmation (reversals need strong volume)
        if volume_ratio < 1.2:
            confidence -= 2.5
        elif volume_ratio < 1.5:
            confidence -= 1.0
        elif volume_ratio > 2.0:
            confidence += 1.0  # Bonus

        # Recency
        if bars_since_break > 20:
            confidence -= 2.0
        elif bars_since_break > 10:
            confidence -= 1.0

        return max(1.0, min(10.0, round(confidence, 1)))

    def get_chart_overlays(
        self,
        bars: List[Dict[str, Any]],
        lookback: int = 100
    ) -> Dict[str, Any]:
        """
        Get all chart overlays for display.

        Returns:
            {
                "bos_levels": [...],  # White lines
                "choch_levels": [...],  # Cyan lines
                "swing_highs": [...],  # For debugging
                "swing_lows": [...]    # For debugging
            }
        """
        bos_levels = self.detect_bos(bars, lookback)
        choch_levels = self.detect_choch(bars, lookback)

        return {
            "bos_levels": [
                {
                    "price": level.price,
                    "type": level.type,
                    "formed_at": level.formed_at,
                    "bars_ago": level.bars_ago,
                    "target": level.target_price,
                    "invalidation": level.stop_invalidation,
                    "confidence": level.confidence,
                    "color": "white",
                    "label": f"BoS ({level.type})"
                }
                for level in bos_levels if level.is_valid
            ],
            "choch_levels": [
                {
                    "price": level.price,
                    "type": level.type,
                    "formed_at": level.formed_at,
                    "bars_ago": level.bars_ago,
                    "target": level.target_price,
                    "invalidation": level.stop_invalidation,
                    "confidence": level.confidence,
                    "color": "cyan",
                    "label": f"CHoCH ({level.type})"
                }
                for level in choch_levels if level.is_valid
            ]
        }
