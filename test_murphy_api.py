#!/usr/bin/env python3
"""
Quick test to verify Murphy API endpoint integration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from murphy_classifier_v2 import MurphyClassifier, Bar
from datetime import datetime, timedelta

def test_murphy_classifier():
    """Test Murphy classifier with sample data"""
    print("Testing Murphy Classifier V2...")

    # Create sample bars (bullish trend)
    bars = []
    base_time = datetime.now()
    base_price = 10.0

    for i in range(50):
        # Simulate bullish trend with some noise
        price = base_price + (i * 0.01) + ((-1)**(i % 3) * 0.005)
        bar = Bar(
            timestamp=str(base_time + timedelta(minutes=i)),
            open=price,
            high=price + 0.02,
            low=price - 0.01,
            close=price + 0.01,
            volume=1000 + (i * 50),
            index=i
        )
        bars.append(bar)

    # Test classification
    murphy = MurphyClassifier()

    signal = murphy.classify(
        bars=bars,
        signal_index=len(bars) - 1,
        structure_age_bars=10,
        level_price=10.5
    )

    print(f"\n✓ Murphy Signal Generated:")
    print(f"  Direction: {signal.direction}")
    print(f"  Stars: {signal.stars}")
    print(f"  Grade: {signal.grade}")
    print(f"  Confidence: {signal.confidence:.2f}")
    print(f"  Label: {murphy.format_label(signal)}")
    print(f"  Interpretation: {signal.interpretation[:100]}...")

    # Test V2 enhancements
    print(f"\n✓ V2 Enhancements:")
    print(f"  Liquidity Sweep: {signal.has_liquidity_sweep}")
    print(f"  Rejection Type: {signal.rejection_type}")
    print(f"  Pattern: {signal.pattern}")
    print(f"  FVG Momentum: {signal.fvg_momentum}")

    print("\n✓ Murphy Classifier V2 test passed!")
    return True

if __name__ == "__main__":
    try:
        test_murphy_classifier()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
