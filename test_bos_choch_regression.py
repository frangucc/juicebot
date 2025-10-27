#!/usr/bin/env python3
"""
BoS/CHoCH Regression Test Tool

Tests the Break of Structure (BoS) and Change of Character (CHoCH) detection
algorithm against historical BYND data to validate:
1. Pattern detection accuracy
2. Scoring system effectiveness
3. Predictive power of signals

This script runs independently and does not modify the core platform.
"""

import json
import statistics
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from murphy_classifier_v2 import MurphyClassifierV2, MurphySignal


@dataclass
class Bar:
    """Represents a single price bar"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    index: int  # Position in dataset


@dataclass
class SwingPoint:
    """Represents a swing high or low"""
    index: int
    price: float
    timestamp: str
    type: str  # 'high' or 'low'
    broken: bool = False
    broken_at_index: Optional[int] = None


@dataclass
class Signal:
    """Represents a BoS or CHoCH signal"""
    index: int
    price: float
    timestamp: str
    signal_type: str  # 'bos_bullish', 'bos_bearish', 'choch_bullish', 'choch_bearish'
    strength_score: float  # 0-100
    swing_point: SwingPoint

    # Murphy's classification
    murphy_direction: Optional[str] = None  # ↑/↓/−
    murphy_stars: Optional[int] = None  # 0-4
    murphy_grade: Optional[int] = None  # 1-10
    murphy_confidence: Optional[float] = None
    murphy_label: Optional[str] = None  # Full formatted label

    # Prediction tracking
    next_5_bars_move: Optional[float] = None
    next_10_bars_move: Optional[float] = None
    next_20_bars_move: Optional[float] = None
    was_correct: Optional[bool] = None
    murphy_agreed: Optional[bool] = None  # Did Murphy's direction match outcome?


class BoSChoCHDetector:
    """Implements the same detection logic as the frontend chart"""

    def __init__(self, lookback: int = 10, significance_threshold: float = 0.003):
        self.lookback = lookback
        self.significance_threshold = significance_threshold
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []
        self.signals: List[Signal] = []
        self.murphy = MurphyClassifierV2()  # Initialize Murphy's Classifier V2

    def detect_swing_point(self, bars: List[Bar], check_index: int) -> Optional[SwingPoint]:
        """Detect if a bar is a confirmed swing high or low"""
        if check_index < self.lookback or check_index >= len(bars) - self.lookback:
            return None

        bar = bars[check_index]

        # Check for swing high
        before_bars = bars[check_index - self.lookback:check_index]
        after_bars = bars[check_index + 1:check_index + self.lookback + 1]

        is_swing_high = (
            all(b.high < bar.high for b in before_bars) and
            all(b.high < bar.high for b in after_bars)
        )

        if is_swing_high:
            return SwingPoint(
                index=check_index,
                price=bar.high,
                timestamp=bar.timestamp,
                type='high'
            )

        # Check for swing low
        is_swing_low = (
            all(b.low > bar.low for b in before_bars) and
            all(b.low > bar.low for b in after_bars)
        )

        if is_swing_low:
            return SwingPoint(
                index=check_index,
                price=bar.low,
                timestamp=bar.timestamp,
                type='low'
            )

        return None

    def determine_trend(self) -> Tuple[bool, bool, str]:
        """Determine if we're in uptrend or downtrend"""
        recent_highs = self.swing_highs[-3:] if len(self.swing_highs) >= 3 else []
        recent_lows = self.swing_lows[-3:] if len(self.swing_lows) >= 3 else []

        # Need at least 2 swing points to determine trend
        is_uptrend = False
        is_downtrend = False
        trend_strength = "none"

        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            # Strong uptrend: higher highs AND higher lows
            if (recent_highs[-1].price > recent_highs[0].price and
                recent_lows[-1].price > recent_lows[0].price):
                is_uptrend = True
                trend_strength = "strong_up"
            # Strong downtrend: lower lows AND lower highs
            elif (recent_lows[-1].price < recent_lows[0].price and
                  recent_highs[-1].price < recent_highs[0].price):
                is_downtrend = True
                trend_strength = "strong_down"
            # Weak uptrend: higher highs but not higher lows
            elif recent_highs[-1].price > recent_highs[0].price:
                is_uptrend = True
                trend_strength = "weak_up"
            # Weak downtrend: lower lows but not lower highs
            elif recent_lows[-1].price < recent_lows[0].price:
                is_downtrend = True
                trend_strength = "weak_down"

        return is_uptrend, is_downtrend, trend_strength

    def calculate_strength_score(self, swing: SwingPoint, bars: List[Bar],
                                 current_index: int, is_new_extreme: bool) -> float:
        """
        Calculate strength score (0-100) based on:
        1. Volume at swing point
        2. Distance from previous swing
        3. How long swing held before breaking
        4. Significance of the break
        5. Trend alignment
        """
        score = 50.0  # Start at middle

        # Factor 1: Volume confirmation (0-20 points)
        if swing.index < len(bars):
            swing_bar = bars[swing.index]
            nearby_bars = bars[max(0, swing.index - 10):swing.index + 10]
            avg_volume = statistics.mean([b.volume for b in nearby_bars]) if nearby_bars else 1

            volume_ratio = swing_bar.volume / avg_volume if avg_volume > 0 else 1
            if volume_ratio > 1.5:
                score += 15
            elif volume_ratio > 1.2:
                score += 10
            elif volume_ratio > 1.0:
                score += 5
            elif volume_ratio < 0.5:
                score -= 10

        # Factor 2: Time held before breaking (0-20 points)
        bars_held = current_index - swing.index
        if bars_held > 100:
            score += 20  # Very significant level
        elif bars_held > 50:
            score += 15
        elif bars_held > 20:
            score += 10
        elif bars_held < 5:
            score -= 10  # Too quick, might be noise

        # Factor 3: Significance of level (0-20 points)
        if is_new_extreme:
            score += 20  # Breaking to new highs/lows
        else:
            score += 5  # Minor break

        # Factor 4: Distance from previous swings (0-15 points)
        if swing.type == 'high' and len(self.swing_highs) >= 2:
            prev_swing = self.swing_highs[-2]
            distance_pct = abs(swing.price - prev_swing.price) / prev_swing.price
            if distance_pct > 0.02:  # 2% or more
                score += 15
            elif distance_pct > 0.01:
                score += 10
            elif distance_pct > 0.005:
                score += 5

        if swing.type == 'low' and len(self.swing_lows) >= 2:
            prev_swing = self.swing_lows[-2]
            distance_pct = abs(swing.price - prev_swing.price) / prev_swing.price
            if distance_pct > 0.02:
                score += 15
            elif distance_pct > 0.01:
                score += 10
            elif distance_pct > 0.005:
                score += 5

        # Factor 5: Trend alignment (0-10 points)
        is_uptrend, is_downtrend, trend_strength = self.determine_trend()
        if swing.type == 'high' and is_uptrend:
            score += 10  # Bullish break in uptrend
        elif swing.type == 'low' and is_downtrend:
            score += 10  # Bearish break in downtrend

        # Clamp to 0-100
        return max(0, min(100, score))

    def check_for_breaks(self, bars: List[Bar], current_index: int) -> List[Signal]:
        """Check if current bar breaks any swing points"""
        new_signals = []
        current_bar = bars[current_index]

        is_uptrend, is_downtrend, trend_strength = self.determine_trend()

        # Track highest/lowest broken swings for significance filtering
        broken_highs = [s for s in self.signals if 'bullish' in s.signal_type]
        broken_lows = [s for s in self.signals if 'bearish' in s.signal_type]

        highest_broken = max([s.price for s in broken_highs], default=0)
        lowest_broken = min([s.price for s in broken_lows], default=float('inf'))

        # Check swing highs for breaks
        for swing in self.swing_highs:
            if not swing.broken and current_bar.high > swing.price:
                # Check if this is a significant new high
                is_new_high = swing.price > highest_broken * (1 + self.significance_threshold)

                if is_new_high:
                    swing.broken = True
                    swing.broken_at_index = current_index

                    # Determine signal type based on trend
                    # BoS = continuation (breaking high in uptrend or neutral)
                    # CHoCH = reversal (breaking high ONLY in STRONG downtrend)
                    if is_downtrend and trend_strength == 'strong_down':
                        # Only call CHoCH if we're in a STRONG downtrend
                        # (both lower lows AND lower highs)
                        signal_type = 'choch_bullish'
                    else:
                        # Default to BoS for uptrends, weak trends, or neutral
                        signal_type = 'bos_bullish'

                    # Calculate strength score
                    strength = self.calculate_strength_score(
                        swing, bars, current_index, is_new_high
                    )

                    # Get Murphy's classification (V2 with enhancements)
                    structure_age = current_index - swing.index
                    murphy_signal = self.murphy.classify(bars, current_index, structure_age, swing.price)

                    signal = Signal(
                        index=current_index,
                        price=swing.price,
                        timestamp=current_bar.timestamp,
                        signal_type=signal_type,
                        strength_score=strength,
                        swing_point=swing,
                        murphy_direction=murphy_signal.direction,
                        murphy_stars=murphy_signal.stars,
                        murphy_grade=murphy_signal.grade,
                        murphy_confidence=murphy_signal.confidence,
                        murphy_label=self.murphy.format_label(murphy_signal)
                    )

                    new_signals.append(signal)
                    self.signals.append(signal)
                else:
                    # Mark as broken but don't create signal (minor swing)
                    swing.broken = True
                    swing.broken_at_index = current_index

        # Check swing lows for breaks
        for swing in self.swing_lows:
            if not swing.broken and current_bar.low < swing.price:
                # Check if this is a significant new low
                is_new_low = swing.price < lowest_broken * (1 - self.significance_threshold)

                if is_new_low:
                    swing.broken = True
                    swing.broken_at_index = current_index

                    # Determine signal type based on trend
                    # BoS = continuation (breaking low in downtrend or neutral)
                    # CHoCH = reversal (breaking low ONLY in STRONG uptrend)
                    if is_uptrend and trend_strength == 'strong_up':
                        # Only call CHoCH if we're in a STRONG uptrend
                        # (both higher highs AND higher lows)
                        signal_type = 'choch_bearish'
                    else:
                        # Default to BoS for downtrends, weak trends, or neutral
                        signal_type = 'bos_bearish'

                    # Calculate strength score
                    strength = self.calculate_strength_score(
                        swing, bars, current_index, is_new_low
                    )

                    # Get Murphy's classification (V2 with enhancements)
                    structure_age = current_index - swing.index
                    murphy_signal = self.murphy.classify(bars, current_index, structure_age, swing.price)

                    signal = Signal(
                        index=current_index,
                        price=swing.price,
                        timestamp=current_bar.timestamp,
                        signal_type=signal_type,
                        strength_score=strength,
                        swing_point=swing,
                        murphy_direction=murphy_signal.direction,
                        murphy_stars=murphy_signal.stars,
                        murphy_grade=murphy_signal.grade,
                        murphy_confidence=murphy_signal.confidence,
                        murphy_label=self.murphy.format_label(murphy_signal)
                    )

                    new_signals.append(signal)
                    self.signals.append(signal)
                else:
                    # Mark as broken but don't create signal
                    swing.broken = True
                    swing.broken_at_index = current_index

        return new_signals

    def process_bars(self, bars: List[Bar]) -> List[Signal]:
        """Process all bars and detect BoS/CHoCH signals (simulates real-time)"""
        print(f"Processing {len(bars)} bars with lookback={self.lookback}, threshold={self.significance_threshold}")

        # Process bars one at a time, simulating real-time trading
        for current_index in range(len(bars)):
            # Check if we just confirmed a new swing point (lookback bars ago)
            swing_confirm_index = current_index - self.lookback
            if swing_confirm_index >= self.lookback:
                swing = self.detect_swing_point(bars, swing_confirm_index)
                if swing:
                    if swing.type == 'high':
                        self.swing_highs.append(swing)
                    else:
                        self.swing_lows.append(swing)

            # Check if current bar breaks any existing swing points
            if current_index >= self.lookback * 2:
                self.check_for_breaks(bars, current_index)

        print(f"Detected {len(self.swing_highs)} swing highs and {len(self.swing_lows)} swing lows")
        print(f"Generated {len(self.signals)} signals")
        return self.signals


class PredictionAnalyzer:
    """Analyzes the predictive accuracy of signals"""

    @staticmethod
    def analyze_signal_predictions(signals: List[Signal], bars: List[Bar]) -> Dict:
        """Calculate prediction metrics for all signals"""

        for signal in signals:
            signal_index = signal.index

            # Calculate price moves after signal
            if signal_index + 5 < len(bars):
                next_5_close = bars[signal_index + 5].close
                signal.next_5_bars_move = ((next_5_close - signal.price) / signal.price) * 100

            if signal_index + 10 < len(bars):
                next_10_close = bars[signal_index + 10].close
                signal.next_10_bars_move = ((next_10_close - signal.price) / signal.price) * 100

            if signal_index + 20 < len(bars):
                next_20_close = bars[signal_index + 20].close
                signal.next_20_bars_move = ((next_20_close - signal.price) / signal.price) * 100

            # Determine if prediction was correct
            # Bullish signals should move up, bearish should move down
            if signal.next_10_bars_move is not None:
                if 'bullish' in signal.signal_type:
                    signal.was_correct = signal.next_10_bars_move > 0
                else:
                    signal.was_correct = signal.next_10_bars_move < 0

                # Check if Murphy agreed with the outcome
                if signal.murphy_direction:
                    if signal.murphy_direction == "↑":
                        signal.murphy_agreed = signal.next_10_bars_move > 0
                    elif signal.murphy_direction == "↓":
                        signal.murphy_agreed = signal.next_10_bars_move < 0
                    else:  # "−" neutral
                        signal.murphy_agreed = None

        # Calculate aggregate metrics
        signals_with_predictions = [s for s in signals if s.was_correct is not None]

        if not signals_with_predictions:
            return {
                'total_signals': len(signals),
                'signals_analyzed': 0,
                'accuracy': 0,
                'error': 'Not enough data for predictions'
            }

        correct_signals = sum(1 for s in signals_with_predictions if s.was_correct)
        accuracy = (correct_signals / len(signals_with_predictions)) * 100

        # Murphy's accuracy
        murphy_predictions = [s for s in signals_with_predictions if s.murphy_agreed is not None]
        murphy_correct = sum(1 for s in murphy_predictions if s.murphy_agreed)
        murphy_accuracy = (murphy_correct / len(murphy_predictions) * 100) if murphy_predictions else 0

        # Break down by signal type
        bos_bullish = [s for s in signals_with_predictions if s.signal_type == 'bos_bullish']
        bos_bearish = [s for s in signals_with_predictions if s.signal_type == 'bos_bearish']
        choch_bullish = [s for s in signals_with_predictions if s.signal_type == 'choch_bullish']
        choch_bearish = [s for s in signals_with_predictions if s.signal_type == 'choch_bearish']

        # Analyze by strength score ranges
        high_strength = [s for s in signals_with_predictions if s.strength_score >= 70]
        medium_strength = [s for s in signals_with_predictions if 50 <= s.strength_score < 70]
        low_strength = [s for s in signals_with_predictions if s.strength_score < 50]

        return {
            'total_signals': len(signals),
            'signals_analyzed': len(signals_with_predictions),
            'overall_accuracy': accuracy,
            'correct_signals': correct_signals,
            'incorrect_signals': len(signals_with_predictions) - correct_signals,

            # Murphy's metrics
            'murphy_predictions': len(murphy_predictions),
            'murphy_correct': murphy_correct,
            'murphy_accuracy': murphy_accuracy,

            'by_type': {
                'bos_bullish': {
                    'count': len(bos_bullish),
                    'accuracy': (sum(1 for s in bos_bullish if s.was_correct) / len(bos_bullish) * 100) if bos_bullish else 0,
                    'avg_strength': statistics.mean([s.strength_score for s in bos_bullish]) if bos_bullish else 0
                },
                'bos_bearish': {
                    'count': len(bos_bearish),
                    'accuracy': (sum(1 for s in bos_bearish if s.was_correct) / len(bos_bearish) * 100) if bos_bearish else 0,
                    'avg_strength': statistics.mean([s.strength_score for s in bos_bearish]) if bos_bearish else 0
                },
                'choch_bullish': {
                    'count': len(choch_bullish),
                    'accuracy': (sum(1 for s in choch_bullish if s.was_correct) / len(choch_bullish) * 100) if choch_bullish else 0,
                    'avg_strength': statistics.mean([s.strength_score for s in choch_bullish]) if choch_bullish else 0
                },
                'choch_bearish': {
                    'count': len(choch_bearish),
                    'accuracy': (sum(1 for s in choch_bearish if s.was_correct) / len(choch_bearish) * 100) if choch_bearish else 0,
                    'avg_strength': statistics.mean([s.strength_score for s in choch_bearish]) if choch_bearish else 0
                }
            },

            'by_strength': {
                'high (70-100)': {
                    'count': len(high_strength),
                    'accuracy': (sum(1 for s in high_strength if s.was_correct) / len(high_strength) * 100) if high_strength else 0,
                    'avg_move_10bars': statistics.mean([abs(s.next_10_bars_move) for s in high_strength if s.next_10_bars_move]) if high_strength else 0
                },
                'medium (50-69)': {
                    'count': len(medium_strength),
                    'accuracy': (sum(1 for s in medium_strength if s.was_correct) / len(medium_strength) * 100) if medium_strength else 0,
                    'avg_move_10bars': statistics.mean([abs(s.next_10_bars_move) for s in medium_strength if s.next_10_bars_move]) if medium_strength else 0
                },
                'low (0-49)': {
                    'count': len(low_strength),
                    'accuracy': (sum(1 for s in low_strength if s.was_correct) / len(low_strength) * 100) if low_strength else 0,
                    'avg_move_10bars': statistics.mean([abs(s.next_10_bars_move) for s in low_strength if s.next_10_bars_move]) if low_strength else 0
                }
            }
        }


def load_historical_bars(filename: str = "bynd_historical_data.json") -> List[Bar]:
    """Load all historical bars from flat file (fast)"""
    print(f"Loading historical bars from {filename}...")

    with open(filename, 'r') as f:
        bars_data = json.load(f)

    all_bars = []
    for bar_data in bars_data:
        bar = Bar(
            timestamp=bar_data['timestamp'],
            open=float(bar_data['open']),
            high=float(bar_data['high']),
            low=float(bar_data['low']),
            close=float(bar_data['close']),
            volume=int(bar_data['volume']),
            index=bar_data['index']
        )
        all_bars.append(bar)

    print(f"✓ Loaded {len(all_bars)} bars")
    return all_bars


def generate_report(signals: List[Signal], metrics: Dict, bars: List[Bar]) -> str:
    """Generate a comprehensive test report"""

    report = []
    report.append("=" * 80)
    report.append("BoS/CHoCH REGRESSION TEST REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Dataset: BYND - {len(bars)} bars")
    report.append("")

    # Dataset overview
    report.append("DATASET OVERVIEW")
    report.append("-" * 80)
    report.append(f"First bar: {bars[0].timestamp} @ ${bars[0].close:.4f}")
    report.append(f"Last bar:  {bars[-1].timestamp} @ ${bars[-1].close:.4f}")
    report.append(f"High:      ${max(b.high for b in bars):.4f}")
    report.append(f"Low:       ${min(b.low for b in bars):.4f}")
    report.append("")

    # Signal detection summary
    report.append("SIGNAL DETECTION SUMMARY")
    report.append("-" * 80)
    report.append(f"Total signals detected: {metrics['total_signals']}")
    report.append(f"Signals with predictions: {metrics['signals_analyzed']}")
    report.append(f"Overall accuracy: {metrics['overall_accuracy']:.2f}%")
    report.append(f"  ✓ Correct predictions: {metrics['correct_signals']}")
    report.append(f"  ✗ Incorrect predictions: {metrics['incorrect_signals']}")
    report.append("")

    # Murphy's classifier performance
    report.append("MURPHY'S CLASSIFIER PERFORMANCE")
    report.append("-" * 80)
    report.append(f"Murphy predictions made: {metrics['murphy_predictions']}")
    report.append(f"Murphy correct: {metrics['murphy_correct']}")
    report.append(f"Murphy accuracy: {metrics['murphy_accuracy']:.2f}%")
    if metrics['murphy_accuracy'] > metrics['overall_accuracy']:
        improvement = metrics['murphy_accuracy'] - metrics['overall_accuracy']
        report.append(f"  🚀 Murphy improved accuracy by {improvement:.2f}%")
    report.append("")

    # Breakdown by signal type
    report.append("ACCURACY BY SIGNAL TYPE")
    report.append("-" * 80)
    for sig_type, data in metrics['by_type'].items():
        if data['count'] > 0:
            report.append(f"{sig_type.upper()}")
            report.append(f"  Count: {data['count']}")
            report.append(f"  Accuracy: {data['accuracy']:.2f}%")
            report.append(f"  Avg Strength: {data['avg_strength']:.2f}")
            report.append("")

    # Breakdown by strength score
    report.append("ACCURACY BY STRENGTH SCORE")
    report.append("-" * 80)
    for strength_range, data in metrics['by_strength'].items():
        if data['count'] > 0:
            report.append(f"{strength_range}")
            report.append(f"  Count: {data['count']}")
            report.append(f"  Accuracy: {data['accuracy']:.2f}%")
            report.append(f"  Avg 10-bar move: {data['avg_move_10bars']:.2f}%")
            report.append("")

    # Top 10 strongest signals
    report.append("TOP 10 STRONGEST SIGNALS")
    report.append("-" * 80)
    top_signals = sorted(signals, key=lambda s: s.strength_score, reverse=True)[:10]
    for i, sig in enumerate(top_signals, 1):
        correct_marker = "✓" if sig.was_correct else "✗" if sig.was_correct is not None else "?"
        move_str = f"{sig.next_10_bars_move:+.2f}%" if sig.next_10_bars_move else "N/A"
        report.append(f"{i}. {sig.signal_type.upper()} @ ${sig.price:.4f}")
        report.append(f"   Strength: {sig.strength_score:.2f} | 10-bar move: {move_str} {correct_marker}")
    report.append("")

    # All signals chronologically
    report.append("ALL SIGNALS (CHRONOLOGICAL)")
    report.append("-" * 80)
    for sig in signals:
        correct_marker = "✓" if sig.was_correct else "✗" if sig.was_correct is not None else "?"
        murphy_marker = "✓" if sig.murphy_agreed else "✗" if sig.murphy_agreed is not None else "−"
        move_5 = f"{sig.next_5_bars_move:+.2f}%" if sig.next_5_bars_move else "N/A"
        move_10 = f"{sig.next_10_bars_move:+.2f}%" if sig.next_10_bars_move else "N/A"
        move_20 = f"{sig.next_20_bars_move:+.2f}%" if sig.next_20_bars_move else "N/A"
        murphy_label = sig.murphy_label if sig.murphy_label else "−"

        report.append(f"Bar {sig.index:4d} | {sig.timestamp} | {sig.signal_type:14s} @ ${sig.price:.4f}")
        report.append(f"  Strength: {sig.strength_score:5.1f} | Murphy: {murphy_label:10s} {murphy_marker}")
        report.append(f"  Moves: 5bar={move_5:>7s} 10bar={move_10:>7s} 20bar={move_20:>7s} {correct_marker}")

    report.append("")
    report.append("=" * 80)

    return "\n".join(report)


def main():
    """Run the regression test"""
    print("BoS/CHoCH Regression Test Tool")
    print("=" * 80)
    print()

    # Configuration
    SYMBOL = "BYND"
    LOOKBACK = 10
    SIGNIFICANCE_THRESHOLD = 0.003  # 0.3%

    # Load data from flat file (fast!)
    bars = load_historical_bars()
    print()

    # Run detection
    print("Running BoS/CHoCH detection...")
    detector = BoSChoCHDetector(lookback=LOOKBACK, significance_threshold=SIGNIFICANCE_THRESHOLD)
    signals = detector.process_bars(bars)
    print()

    # Analyze predictions
    print("Analyzing prediction accuracy...")
    analyzer = PredictionAnalyzer()
    metrics = analyzer.analyze_signal_predictions(signals, bars)
    print()

    # Generate report
    report = generate_report(signals, metrics, bars)

    # Save report
    report_filename = f"bos_choch_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w') as f:
        f.write(report)

    print(report)
    print()
    print(f"Report saved to: {report_filename}")

    # Also save signals as JSON for further analysis
    signals_data = []
    for sig in signals:
        signals_data.append({
            'index': sig.index,
            'timestamp': sig.timestamp,
            'price': sig.price,
            'signal_type': sig.signal_type,
            'strength_score': sig.strength_score,
            'next_5_bars_move': sig.next_5_bars_move,
            'next_10_bars_move': sig.next_10_bars_move,
            'next_20_bars_move': sig.next_20_bars_move,
            'was_correct': sig.was_correct
        })

    json_filename = f"bos_choch_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_filename, 'w') as f:
        json.dump({
            'config': {
                'lookback': LOOKBACK,
                'significance_threshold': SIGNIFICANCE_THRESHOLD,
                'total_bars': len(bars)
            },
            'metrics': metrics,
            'signals': signals_data
        }, f, indent=2)

    print(f"Signals data saved to: {json_filename}")


if __name__ == "__main__":
    main()
