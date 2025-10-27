#!/usr/bin/env python3
"""
Momo Advanced - Trader Logic Encoded
=====================================

Combines multi-timeframe momentum with:
1. VWAP positioning (value zone vs chasing)
2. Synthetic shadow trading (accumulation signals)
3. Leg detection (wave analysis)
4. Time-of-day patterns
5. Reverse psychology (invert wrong signals)

This encodes real trader thinking:
- "Below VWAP = value zone"
- "Accumulating lower = finding support"
- "Leg 1 pullback = prime for Leg 2"
- "9am continuation = prime time"
- "If consistently wrong at 7am, do opposite"
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import datetime, time
from collections import deque
import statistics

sys.path.insert(0, str(Path(__file__).parent))
from murphy_classifier_v2 import Bar
from momo_classifier import MomoClassifier, MomoSignal


# ============================================================================
# VWAP CONTEXT
# ============================================================================

@dataclass
class VWAPContext:
    """VWAP position analysis"""
    zone: str              # DEEP_VALUE, VALUE, FAIR, EXTENDED, EXTREME
    distance_pct: float    # % from VWAP
    risk: str             # LOW, MEDIUM, HIGH, EXTREME
    action_bias: str      # AGGRESSIVE_BUY, BUY_PULLBACK, NEUTRAL, CHASE_WARNING, NO_BUY


class VWAPAnalyzer:
    """Analyze position relative to VWAP"""

    def analyze(self, current_price: float, vwap: float) -> VWAPContext:
        """Determine if we're in value zone or chasing"""

        if vwap == 0:
            return VWAPContext("UNKNOWN", 0.0, "MEDIUM", "NEUTRAL")

        distance_pct = ((current_price - vwap) / vwap) * 100

        # Determine zone
        if distance_pct < -5:
            zone = "DEEP_VALUE"
            risk = "LOW"
            action_bias = "AGGRESSIVE_BUY"
        elif -5 <= distance_pct < -2:
            zone = "VALUE"
            risk = "LOW"
            action_bias = "BUY_PULLBACK"
        elif -2 <= distance_pct <= 2:
            zone = "FAIR"
            risk = "MEDIUM"
            action_bias = "NEUTRAL"
        elif 2 < distance_pct <= 5:
            zone = "EXTENDED"
            risk = "HIGH"
            action_bias = "CHASE_WARNING"
        else:
            zone = "EXTREME"
            risk = "EXTREME"
            action_bias = "NO_BUY"

        return VWAPContext(zone, distance_pct, risk, action_bias)


# ============================================================================
# SYNTHETIC SHADOW TRADING
# ============================================================================

@dataclass
class SyntheticEntry:
    """A synthetic buy entry"""
    bar_index: int
    price: float
    shares: int = 1


class SyntheticTracker:
    """Shadow trade to detect support via P&L"""

    def __init__(self, max_entries: int = 5):
        self.entries: List[SyntheticEntry] = []
        self.max_entries = max_entries

    def add_entry(self, bar_index: int, price: float):
        """Add a synthetic buy"""
        if len(self.entries) < self.max_entries:
            self.entries.append(SyntheticEntry(bar_index, price))

    def get_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L %"""
        if not self.entries:
            return 0.0

        avg_entry = statistics.mean([e.price for e in self.entries])
        return ((current_price - avg_entry) / avg_entry) * 100

    def is_accumulating_lower(self) -> bool:
        """Check if we're buying progressively lower"""
        if len(self.entries) < 2:
            return False

        # Check if last 3 entries are descending
        recent = self.entries[-min(3, len(self.entries)):]
        prices = [e.price for e in recent]

        return all(prices[i] > prices[i+1] for i in range(len(prices)-1))

    def get_signal(self, current_price: float) -> Dict:
        """Generate accumulation signal"""

        if len(self.entries) < 3:
            return {'signal': 'WAIT', 'confidence': 0.0, 'reason': 'Not enough entries'}

        pnl = self.get_unrealized_pnl(current_price)
        accumulating_lower = self.is_accumulating_lower()

        # Key insight: If we accumulated 3+ times while going LOWER,
        # and now starting to bounce = we found support!
        if accumulating_lower and pnl < -3:
            # More entries = higher confidence
            confidence = min(0.90, 0.60 + (len(self.entries) * 0.10))
            return {
                'signal': 'STRONG_BUY',
                'confidence': confidence,
                'reason': f'Accumulated {len(self.entries)}x while going lower, found support',
                'avg_entry': statistics.mean([e.price for e in self.entries]),
                'unrealized_pnl': pnl
            }

        # Light accumulation, not enough signal
        return {'signal': 'WAIT', 'confidence': 0.0, 'reason': 'Accumulating but no clear support'}

    def reset(self):
        """Clear entries (when position closed)"""
        self.entries = []


# ============================================================================
# LEG DETECTION
# ============================================================================

@dataclass
class Leg:
    """A momentum leg (wave)"""
    start_bar: int
    top_bar: int
    start_price: float
    top_price: float
    magnitude_pct: float
    bars_duration: int


@dataclass
class LegContext:
    """Current leg context"""
    current_leg: int
    legs: List[Leg]
    next_leg_probability: float
    pullback_pct: float
    in_pullback_zone: bool
    biggest_leg_magnitude: float


class LegDetector:
    """Detect momentum legs (waves)"""

    def __init__(self, min_leg_magnitude: float = 5.0):
        self.min_leg_magnitude = min_leg_magnitude

    def detect_legs(self, bars: List[Bar], current_index: int, lookback: int = 100) -> List[Leg]:
        """Find significant price legs"""

        legs = []
        start = max(0, current_index - lookback)

        # Find local highs (potential leg tops)
        local_highs = self._find_local_highs(bars, start, current_index)

        for high_idx in local_highs:
            # Find leg start (low before this high)
            leg_start_idx = self._find_leg_start(bars, start, high_idx)

            if leg_start_idx is not None:
                start_price = bars[leg_start_idx].low
                top_price = bars[high_idx].high
                magnitude = ((top_price - start_price) / start_price) * 100

                # Only count significant legs
                if magnitude >= self.min_leg_magnitude:
                    legs.append(Leg(
                        start_bar=leg_start_idx,
                        top_bar=high_idx,
                        start_price=start_price,
                        top_price=top_price,
                        magnitude_pct=magnitude,
                        bars_duration=high_idx - leg_start_idx
                    ))

        # Sort by magnitude (biggest first)
        legs.sort(key=lambda x: x.magnitude_pct, reverse=True)

        return legs

    def _find_local_highs(self, bars: List[Bar], start: int, end: int) -> List[int]:
        """Find local high points"""
        highs = []

        for i in range(start + 2, end - 2):
            if (bars[i].high > bars[i-1].high and
                bars[i].high > bars[i-2].high and
                bars[i].high > bars[i+1].high and
                bars[i].high > bars[i+2].high):
                highs.append(i)

        return highs

    def _find_leg_start(self, bars: List[Bar], start: int, high_idx: int) -> Optional[int]:
        """Find the low that started this leg"""
        if high_idx < start + 10:
            return None

        # Look back from high to find the low
        lookback_start = max(start, high_idx - 50)
        lows = [(i, bars[i].low) for i in range(lookback_start, high_idx)]

        if not lows:
            return None

        # Return index of lowest point
        return min(lows, key=lambda x: x[1])[0]

    def get_context(self, bars: List[Bar], current_index: int, legs: List[Leg]) -> LegContext:
        """Analyze current position relative to legs"""

        if not legs:
            return LegContext(0, [], 0.0, 0.0, False, 0.0)

        current_leg = len(legs)

        # Leg probabilities (decreasing)
        leg_probs = {1: 0.85, 2: 0.65, 3: 0.45, 4: 0.25, 5: 0.10}
        next_leg_prob = leg_probs.get(current_leg + 1, 0.05)

        # Calculate pullback from last leg top
        current_price = bars[current_index].close
        last_leg_top = legs[0].top_price
        pullback_pct = ((last_leg_top - current_price) / last_leg_top) * 100

        # Sweet spot for next leg: 3-8% pullback
        in_pullback_zone = 3 <= pullback_pct <= 8

        return LegContext(
            current_leg=current_leg,
            legs=legs,
            next_leg_probability=next_leg_prob,
            pullback_pct=pullback_pct,
            in_pullback_zone=in_pullback_zone,
            biggest_leg_magnitude=legs[0].magnitude_pct
        )


# ============================================================================
# TIME-OF-DAY CONTEXT
# ============================================================================

@dataclass
class TimePeriodBehavior:
    """Expected behavior for a time period"""
    period: str
    behavior: str
    bias: str
    volatility: str
    note: str


class TimeContext:
    """Time-of-day pattern analysis"""

    TIME_PERIODS = {
        'premarket_early': (time(3, 0), time(6, 0)),
        'premarket_pullback': (time(6, 0), time(7, 0)),
        'premarket_coil': (time(7, 0), time(8, 30)),
        'market_open': (time(8, 30), time(9, 0)),
        'morning_run': (time(9, 0), time(11, 0)),
        'lunch_chop': (time(11, 0), time(13, 0)),
        'power_hour': (time(13, 0), time(15, 0)),
        'close': (time(15, 0), time(16, 0)),
        'after_hours': (time(16, 0), time(20, 0))
    }

    BEHAVIORS = {
        'premarket_early': TimePeriodBehavior(
            'premarket_early', 'thin_books', 'bullish', 'high',
            'Easy to run order books 3-6am'
        ),
        'premarket_pullback': TimePeriodBehavior(
            'premarket_pullback', 'pullback', 'bearish', 'medium',
            'Expected 7am pullback'
        ),
        'premarket_coil': TimePeriodBehavior(
            'premarket_coil', 'consolidation', 'neutral', 'low',
            'Coiling before open 7-8:30am'
        ),
        'market_open': TimePeriodBehavior(
            'market_open', 'sweeps', 'volatile', 'extreme',
            'Sweeps and scrambles 8:30-9am'
        ),
        'morning_run': TimePeriodBehavior(
            'morning_run', 'continuation', 'bullish', 'high',
            'Momo continues 9-11am, PRIME TIME'
        ),
        'lunch_chop': TimePeriodBehavior(
            'lunch_chop', 'choppy', 'neutral', 'low',
            'Lunch chop 11am-1pm, avoid'
        ),
        'power_hour': TimePeriodBehavior(
            'power_hour', 'continuation', 'bullish', 'high',
            'Power hour 1-3pm, second wind'
        ),
        'close': TimePeriodBehavior(
            'close', 'positioning', 'neutral', 'medium',
            'Close near highs = continuation tomorrow'
        ),
        'after_hours': TimePeriodBehavior(
            'after_hours', 'thin_continuation', 'bullish', 'high',
            'Can spike if closed strong'
        )
    }

    def get_period(self, timestamp_str: str) -> TimePeriodBehavior:
        """Get expected behavior for this time"""

        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            t = dt.time()
        except:
            return TimePeriodBehavior('unknown', 'unknown', 'neutral', 'medium', 'Unknown time')

        for period_name, (start, end) in self.TIME_PERIODS.items():
            if start <= t < end:
                return self.BEHAVIORS[period_name]

        return TimePeriodBehavior('unknown', 'unknown', 'neutral', 'medium', 'Unknown time')


# ============================================================================
# REVERSE PSYCHOLOGY
# ============================================================================

@dataclass
class SignalHistory:
    """Track signal correctness"""
    timestamp: str
    period: str
    signal_type: str
    direction: str
    was_correct: bool


class ReverseSignalDetector:
    """Invert signals when consistently wrong"""

    def __init__(self, history_size: int = 50):
        self.history: deque[SignalHistory] = deque(maxlen=history_size)
        self.inversion_rules: Dict[str, bool] = {}  # period -> should_invert

    def track_signal(self, timestamp: str, period: str, signal_type: str,
                     direction: str, was_correct: bool):
        """Record signal outcome"""
        self.history.append(SignalHistory(
            timestamp, period, signal_type, direction, was_correct
        ))

        # Update inversion rules
        self._update_inversion_rules()

    def _update_inversion_rules(self):
        """Check if we should invert signals for specific periods"""

        # Group by period
        by_period: Dict[str, List[bool]] = {}

        for signal in self.history:
            if signal.period not in by_period:
                by_period[signal.period] = []
            by_period[signal.period].append(signal.was_correct)

        # Check accuracy for each period
        for period, results in by_period.items():
            if len(results) >= 10:  # Need at least 10 signals
                accuracy = sum(results) / len(results)

                # If consistently wrong (< 35%), enable inversion
                self.inversion_rules[period] = accuracy < 0.35

    def should_invert(self, period: str) -> bool:
        """Check if we should invert signals for this period"""
        return self.inversion_rules.get(period, False)

    def apply_inversion(self, direction: str, period: str) -> Tuple[str, str]:
        """Invert signal if needed"""

        if self.should_invert(period):
            if direction == '↑':
                return '↓', f"INVERTED (consistently wrong at {period})"
            elif direction == '↓':
                return '↑', f"INVERTED (consistently wrong at {period})"

        return direction, ""


# ============================================================================
# MOMO ADVANCED SIGNAL
# ============================================================================

@dataclass
class MomoAdvancedSignal:
    """Enhanced Momo signal with trader context"""
    # Basic Momo
    direction: str
    stars: int
    juice_score: float

    # VWAP context
    vwap_context: VWAPContext

    # Leg context
    leg_context: LegContext

    # Shadow trading
    shadow_signal: Dict

    # Time period
    time_period: TimePeriodBehavior

    # Final confidence
    confidence: float
    action: str  # STRONG_BUY, BUY, WAIT, SELL, STRONG_SELL
    reason: str

    # Raw data
    price: float
    vwap: float


# ============================================================================
# MOMO ADVANCED CLASSIFIER
# ============================================================================

class MomoAdvanced:
    """
    Advanced Momo with full trader logic
    """

    def __init__(self):
        self.basic_momo = MomoClassifier()
        self.vwap_analyzer = VWAPAnalyzer()
        self.shadow_trader = SyntheticTracker()
        self.leg_detector = LegDetector()
        self.time_context = TimeContext()
        self.reverse_detector = ReverseSignalDetector()

    def classify(self, bars: List[Bar], signal_index: int,
                 yesterday_close: Optional[float] = None) -> MomoAdvancedSignal:
        """
        Generate advanced Momo signal with trader logic
        """

        current_bar = bars[signal_index]

        # 1. Basic Momo signal
        basic_signal = self.basic_momo.classify(bars, signal_index, yesterday_close)

        # 2. VWAP context
        vwap_ctx = self.vwap_analyzer.analyze(current_bar.close, basic_signal.vwap)

        # 3. Leg detection
        legs = self.leg_detector.detect_legs(bars, signal_index)
        leg_ctx = self.leg_detector.get_context(bars, signal_index, legs)

        # 4. Shadow trading signal
        # Synthetically "buy" on dips below VWAP
        if vwap_ctx.zone in ['VALUE', 'DEEP_VALUE']:
            self.shadow_trader.add_entry(signal_index, current_bar.close)

        shadow_signal = self.shadow_trader.get_signal(current_bar.close)

        # 5. Time period
        time_period = self.time_context.get_period(current_bar.timestamp)

        # 6. Combine with trader logic
        final_signal = self._combine_trader_logic(
            basic_signal, vwap_ctx, leg_ctx, shadow_signal, time_period
        )

        # 7. Apply reverse psychology
        inverted_direction, invert_note = self.reverse_detector.apply_inversion(
            final_signal['direction'], time_period.period
        )

        if invert_note:
            final_signal['direction'] = inverted_direction
            final_signal['reason'] += f" | {invert_note}"

        return MomoAdvancedSignal(
            direction=final_signal['direction'],
            stars=basic_signal.stars,
            juice_score=basic_signal.juice_score,
            vwap_context=vwap_ctx,
            leg_context=leg_ctx,
            shadow_signal=shadow_signal,
            time_period=time_period,
            confidence=final_signal['confidence'],
            action=final_signal['action'],
            reason=final_signal['reason'],
            price=current_bar.close,
            vwap=basic_signal.vwap
        )

    def _combine_trader_logic(self, basic, vwap_ctx, leg_ctx, shadow, time_period) -> Dict:
        """Combine all signals using trader logic"""

        confidence = 0.50  # Start neutral
        reasons = []

        # VWAP logic
        if vwap_ctx.zone == 'DEEP_VALUE':
            if basic.direction == '↑':
                confidence += 0.25
                reasons.append(f"Deep value zone ({vwap_ctx.distance_pct:+.1f}% from VWAP)")
        elif vwap_ctx.zone == 'VALUE':
            if basic.direction == '↑':
                confidence += 0.15
                reasons.append(f"Value zone ({vwap_ctx.distance_pct:+.1f}% from VWAP)")
        elif vwap_ctx.zone == 'EXTREME':
            confidence -= 0.20
            reasons.append(f"Extreme extension ({vwap_ctx.distance_pct:+.1f}% from VWAP)")

        # Leg logic
        if leg_ctx.in_pullback_zone and leg_ctx.next_leg_probability > 0.60:
            if basic.direction == '↑':
                confidence += 0.20
                reasons.append(f"Leg {leg_ctx.current_leg} pullback zone, {leg_ctx.next_leg_probability:.0%} prob of next leg")

        # Shadow trading logic
        if shadow['signal'] == 'STRONG_BUY':
            confidence += 0.20
            reasons.append(f"Shadow found support (accumulated while dropping)")

        # Time period logic
        if time_period.behavior == 'continuation' and time_period.bias == 'bullish':
            confidence += 0.10
            reasons.append(f"{time_period.note}")
        elif time_period.behavior == 'choppy':
            confidence -= 0.15
            reasons.append("Lunch chop period")
        elif time_period.behavior == 'pullback':
            if basic.direction == '↓':
                confidence += 0.10
                reasons.append("Expected pullback period")

        # Max juice bonus
        if basic.juice_score >= 0.85:
            confidence += 0.10
            reasons.append(f"MAX JUICE ({basic.stars}/7 stars)")

        # Clamp confidence
        confidence = min(0.95, max(0.05, confidence))

        # Determine action
        if confidence >= 0.80:
            action = "STRONG_BUY" if basic.direction == '↑' else "STRONG_SELL"
        elif confidence >= 0.65:
            action = "BUY" if basic.direction == '↑' else "SELL"
        elif confidence >= 0.45:
            action = "WAIT"
        else:
            action = "AVOID"

        return {
            'direction': basic.direction,
            'confidence': confidence,
            'action': action,
            'reason': ' | '.join(reasons) if reasons else 'No strong signals'
        }


# ============================================================================
# TESTING
# ============================================================================

def test_momo_advanced(data_file: str, focus_date: str = "2025-10-20"):
    """Test advanced Momo on historical data"""
    import json

    print("=" * 100)
    print("MOMO ADVANCED TEST - Trader Logic Encoded")
    print("=" * 100)

    # Load data
    with open(data_file, 'r') as f:
        data = json.load(f)

    bars_data = data['bars'] if isinstance(data, dict) and 'bars' in data else data

    bars = []
    for i, b in enumerate(bars_data):
        bars.append(Bar(
            index=b.get('index', i),
            timestamp=b['timestamp'],
            open=b['open'],
            high=b['high'],
            low=b['low'],
            close=b['close'],
            volume=b['volume']
        ))

    print(f"\nLoaded {len(bars)} bars")

    # Find focus date
    start_bar = 0
    for i, bar in enumerate(bars):
        if focus_date in bar.timestamp:
            start_bar = i
            break

    print(f"Starting at bar {start_bar} ({bars[start_bar].timestamp})\n")

    # Initialize
    momo = MomoAdvanced()

    # Test on key bars
    print(f"{'Bar':<6} {'Time':<12} {'Price':<8} {'Dir':<4} {'Conf':<6} {'Action':<12} {'VWAP Zone':<12} {'Leg':<10}")
    print("-" * 100)

    for i in range(start_bar, min(start_bar + 100, len(bars)), 5):
        signal = momo.classify(bars, i, yesterday_close=0.73)

        print(f"{i:<6} {bars[i].timestamp[11:19]:<12} ${signal.price:<7.2f} "
              f"{signal.direction:<4} {signal.confidence:<5.0%} {signal.action:<12} "
              f"{signal.vwap_context.zone:<12} Leg {signal.leg_context.current_leg:<9}")

    # Detailed analysis for a few bars
    print("\n" + "=" * 100)
    print("DETAILED ANALYSIS")
    print("=" * 100)

    for offset in [0, 20, 40]:
        i = start_bar + offset
        if i >= len(bars):
            continue

        signal = momo.classify(bars, i, yesterday_close=0.73)

        print(f"\nBar {i} ({bars[i].timestamp}):")
        print(f"  Price: ${signal.price:.2f}")
        print(f"  Direction: {signal.direction}")
        print(f"  Confidence: {signal.confidence:.0%}")
        print(f"  Action: {signal.action}")
        print(f"  \nVWAP Context:")
        print(f"    Zone: {signal.vwap_context.zone}")
        print(f"    Distance: {signal.vwap_context.distance_pct:+.2f}%")
        print(f"    Action Bias: {signal.vwap_context.action_bias}")
        print(f"  \nLeg Context:")
        print(f"    Current Leg: {signal.leg_context.current_leg}")
        print(f"    Pullback: {signal.leg_context.pullback_pct:.1f}%")
        print(f"    In Pullback Zone: {signal.leg_context.in_pullback_zone}")
        print(f"    Next Leg Probability: {signal.leg_context.next_leg_probability:.0%}")
        print(f"  \nShadow Trading:")
        print(f"    Signal: {signal.shadow_signal['signal']}")
        print(f"    Confidence: {signal.shadow_signal['confidence']:.0%}")
        print(f"  \nTime Period:")
        print(f"    Period: {signal.time_period.period}")
        print(f"    Behavior: {signal.time_period.behavior}")
        print(f"    Note: {signal.time_period.note}")
        print(f"  \nReason:")
        print(f"    {signal.reason}")

    print("\n" + "=" * 100)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Momo Advanced Test')
    parser.add_argument('--data', type=str, default='bynd_historical_data.json')
    parser.add_argument('--date', type=str, default='2025-10-20')

    args = parser.parse_args()

    test_momo_advanced(args.data, args.date)
