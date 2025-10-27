#!/usr/bin/env python3
"""
Indicator Accuracy Test - Pure Signal Quality Evaluation
=========================================================

Tests indicator accuracy WITHOUT any execution strategy.

Measures ONLY:
- Was the signal directionally correct?
- Accuracy at 5/10/20/50 bars forward
- Breakdown by signal strength (stars/tiers)

NO P&L calculations, NO execution logic, NO stops/targets.

This gives us apples-to-apples comparison of:
- Murphy (SMC) indicator quality
- Momo (Momentum) indicator quality
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from murphy_classifier_v2 import MurphyClassifier, Bar
from momo_classifier import MomoClassifier


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SignalTest:
    """Tracks a signal and its accuracy over time"""
    bar_index: int
    timestamp: str
    direction: str  # "↑", "↓", "−"
    stars: int
    entry_price: float

    # Accuracy tests
    correct_5bars: Optional[bool] = None
    correct_10bars: Optional[bool] = None
    correct_20bars: Optional[bool] = None
    correct_50bars: Optional[bool] = None

    # Price moves
    move_5bars: float = 0.0
    move_10bars: float = 0.0
    move_20bars: float = 0.0
    move_50bars: float = 0.0


# ============================================================================
# INDICATOR ACCURACY TESTER
# ============================================================================

class IndicatorAccuracyTest:
    """
    Test indicator accuracy without execution strategy.
    """

    def __init__(self, indicator_name: str):
        self.indicator_name = indicator_name
        self.signals: List[SignalTest] = []

    def test(
        self,
        bars: List[Bar],
        signals: List,  # Murphy or Momo signals
        start_bar: int = 0,
        threshold: float = 1.0  # % move needed to consider signal correct
    ):
        """
        Test indicator accuracy.

        Args:
            bars: Price bars
            signals: List of indicator signals
            start_bar: Where to start testing
            threshold: % move needed to consider signal "correct"
        """
        for i in range(start_bar, len(signals)):
            signal = signals[i]

            if signal.direction == "−":
                continue  # Skip neutral signals

            # Create test record
            test = SignalTest(
                bar_index=i,
                timestamp=bars[i].timestamp,
                direction=signal.direction,
                stars=signal.stars,
                entry_price=bars[i].close
            )

            # Test at various timeframes
            for bars_forward in [5, 10, 20, 50]:
                if i + bars_forward < len(bars):
                    future_price = bars[i + bars_forward].close
                    move_pct = ((future_price - test.entry_price) / test.entry_price) * 100

                    # Store move
                    if bars_forward == 5:
                        test.move_5bars = move_pct
                    elif bars_forward == 10:
                        test.move_10bars = move_pct
                    elif bars_forward == 20:
                        test.move_20bars = move_pct
                    elif bars_forward == 50:
                        test.move_50bars = move_pct

                    # Check correctness
                    if signal.direction == "↑":
                        is_correct = move_pct > threshold
                    else:  # "↓"
                        is_correct = move_pct < -threshold

                    if bars_forward == 5:
                        test.correct_5bars = is_correct
                    elif bars_forward == 10:
                        test.correct_10bars = is_correct
                    elif bars_forward == 20:
                        test.correct_20bars = is_correct
                    elif bars_forward == 50:
                        test.correct_50bars = is_correct

            self.signals.append(test)

    def get_accuracy_report(self) -> Dict:
        """Generate accuracy report"""

        if not self.signals:
            return {}

        # Overall accuracy
        total_signals = len(self.signals)

        def count_correct(attr):
            return sum(1 for s in self.signals if getattr(s, attr) is not None and getattr(s, attr))

        def count_tested(attr):
            return sum(1 for s in self.signals if getattr(s, attr) is not None)

        accuracy_5 = (count_correct('correct_5bars') / count_tested('correct_5bars') * 100) if count_tested('correct_5bars') > 0 else 0
        accuracy_10 = (count_correct('correct_10bars') / count_tested('correct_10bars') * 100) if count_tested('correct_10bars') > 0 else 0
        accuracy_20 = (count_correct('correct_20bars') / count_tested('correct_20bars') * 100) if count_tested('correct_20bars') > 0 else 0
        accuracy_50 = (count_correct('correct_50bars') / count_tested('correct_50bars') * 100) if count_tested('correct_50bars') > 0 else 0

        # Breakdown by stars
        by_stars = {}
        max_stars = max(s.stars for s in self.signals)

        for star_level in range(1, max_stars + 1):
            star_signals = [s for s in self.signals if s.stars == star_level]

            if not star_signals:
                continue

            def count_star_correct(signals, attr):
                return sum(1 for s in signals if getattr(s, attr) is not None and getattr(s, attr))

            def count_star_tested(signals, attr):
                return sum(1 for s in signals if getattr(s, attr) is not None)

            star_acc_20 = (count_star_correct(star_signals, 'correct_20bars') / count_star_tested(star_signals, 'correct_20bars') * 100) if count_star_tested(star_signals, 'correct_20bars') > 0 else 0

            by_stars[star_level] = {
                'count': len(star_signals),
                'accuracy_20bars': star_acc_20
            }

        # Directional breakdown
        bullish_signals = [s for s in self.signals if s.direction == "↑"]
        bearish_signals = [s for s in self.signals if s.direction == "↓"]

        def dir_accuracy(signals):
            if not signals:
                return 0.0
            correct = sum(1 for s in signals if s.correct_20bars is not None and s.correct_20bars)
            tested = sum(1 for s in signals if s.correct_20bars is not None)
            return (correct / tested * 100) if tested > 0 else 0

        return {
            'indicator': self.indicator_name,
            'total_signals': total_signals,
            'accuracy': {
                '5bars': accuracy_5,
                '10bars': accuracy_10,
                '20bars': accuracy_20,
                '50bars': accuracy_50
            },
            'by_stars': by_stars,
            'by_direction': {
                'bullish_count': len(bullish_signals),
                'bullish_accuracy': dir_accuracy(bullish_signals),
                'bearish_count': len(bearish_signals),
                'bearish_accuracy': dir_accuracy(bearish_signals)
            }
        }


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_indicator_comparison(
    data_file: str,
    focus_date: Optional[str] = None,
    output_file: Optional[str] = None
) -> Dict:
    """
    Compare Murphy vs Momo on same data.

    Returns accuracy metrics for both indicators.
    """

    print("=" * 100)
    print("INDICATOR ACCURACY COMPARISON - Murphy (SMC) vs Momo (Momentum)")
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
    if focus_date:
        for i, bar in enumerate(bars):
            if focus_date in bar.timestamp:
                start_bar = i
                break
        print(f"Starting at bar {start_bar} ({bars[start_bar].timestamp})")

    # Generate Murphy signals
    print("\nGenerating Murphy (SMC) signals...")
    murphy = MurphyClassifier()
    murphy_signals = []

    for i in range(len(bars)):
        signal = murphy.classify(
            bars=bars,
            signal_index=i,
            structure_age_bars=50,
            level_price=None
        )
        murphy_signals.append(signal)

    print(f"Generated {len(murphy_signals)} Murphy signals")

    # Generate Momo signals
    print("Generating Momo (Momentum) signals...")
    momo = MomoClassifier()
    momo_signals = []

    for i in range(len(bars)):
        signal = momo.classify(
            bars=bars,
            signal_index=i,
            yesterday_close=0.73  # BYND Oct 19 close
        )
        momo_signals.append(signal)

    print(f"Generated {len(momo_signals)} Momo signals\n")

    # Test Murphy accuracy
    print("Testing Murphy accuracy...")
    murphy_test = IndicatorAccuracyTest("Murphy (SMC)")
    murphy_test.test(bars, murphy_signals, start_bar)

    # Test Momo accuracy
    print("Testing Momo accuracy...")
    momo_test = IndicatorAccuracyTest("Momo (Momentum)")
    momo_test.test(bars, momo_signals, start_bar)

    # Get reports
    murphy_report = murphy_test.get_accuracy_report()
    momo_report = momo_test.get_accuracy_report()

    # Print results
    print("\n" + "=" * 100)
    print("RESULTS")
    print("=" * 100)

    print(f"\n{'Indicator':<20} {'Total Signals':<15} {'5-Bar':<10} {'10-Bar':<10} {'20-Bar':<10} {'50-Bar':<10}")
    print("-" * 100)

    print(f"{murphy_report['indicator']:<20} {murphy_report['total_signals']:<15} "
          f"{murphy_report['accuracy']['5bars']:>7.1f}%  {murphy_report['accuracy']['10bars']:>7.1f}%  "
          f"{murphy_report['accuracy']['20bars']:>7.1f}%  {murphy_report['accuracy']['50bars']:>7.1f}%")

    print(f"{momo_report['indicator']:<20} {momo_report['total_signals']:<15} "
          f"{momo_report['accuracy']['5bars']:>7.1f}%  {momo_report['accuracy']['10bars']:>7.1f}%  "
          f"{momo_report['accuracy']['20bars']:>7.1f}%  {momo_report['accuracy']['50bars']:>7.1f}%")

    # Stars breakdown
    print("\n" + "-" * 100)
    print("ACCURACY BY SIGNAL STRENGTH (20-bar forward)")
    print("-" * 100)

    print(f"\n{'Indicator':<20} {'Stars':<10} {'Count':<10} {'Accuracy':<10}")
    print("-" * 100)

    for star_level in sorted(murphy_report['by_stars'].keys()):
        data = murphy_report['by_stars'][star_level]
        print(f"{'Murphy':<20} {star_level:<10} {data['count']:<10} {data['accuracy_20bars']:>7.1f}%")

    print()

    for star_level in sorted(momo_report['by_stars'].keys()):
        data = momo_report['by_stars'][star_level]
        print(f"{'Momo':<20} {star_level:<10} {data['count']:<10} {data['accuracy_20bars']:>7.1f}%")

    # Directional breakdown
    print("\n" + "-" * 100)
    print("ACCURACY BY DIRECTION (20-bar forward)")
    print("-" * 100)

    print(f"\n{'Indicator':<20} {'Direction':<15} {'Count':<10} {'Accuracy':<10}")
    print("-" * 100)

    print(f"{'Murphy':<20} {'Bullish':<15} {murphy_report['by_direction']['bullish_count']:<10} "
          f"{murphy_report['by_direction']['bullish_accuracy']:>7.1f}%")
    print(f"{'Murphy':<20} {'Bearish':<15} {murphy_report['by_direction']['bearish_count']:<10} "
          f"{murphy_report['by_direction']['bearish_accuracy']:>7.1f}%")

    print(f"{'Momo':<20} {'Bullish':<15} {momo_report['by_direction']['bullish_count']:<10} "
          f"{momo_report['by_direction']['bullish_accuracy']:>7.1f}%")
    print(f"{'Momo':<20} {'Bearish':<15} {momo_report['by_direction']['bearish_count']:<10} "
          f"{momo_report['by_direction']['bearish_accuracy']:>7.1f}%")

    print("\n" + "=" * 100)

    # Save report if requested
    if output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{output_file}_{timestamp}.json"

        with open(report_file, 'w') as f:
            json.dump({
                'murphy': murphy_report,
                'momo': momo_report
            }, f, indent=2)

        print(f"\nReport saved to: {report_file}")

    return {
        'murphy': murphy_report,
        'momo': momo_report
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Indicator Accuracy Test')
    parser.add_argument('--data', type=str, default='bynd_historical_data.json')
    parser.add_argument('--date', type=str, default='2025-10-20')
    parser.add_argument('--output', type=str, default='indicator_accuracy_report')

    args = parser.parse_args()

    results = run_indicator_comparison(
        data_file=args.data,
        focus_date=args.date,
        output_file=args.output
    )


if __name__ == '__main__':
    main()
