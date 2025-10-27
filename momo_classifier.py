#!/usr/bin/env python3
"""
Momo Classifier - Multi-Timeframe Momentum System
==================================================

Philosophy:
- Momentum trading, not structure trading
- Multi-timeframe alignment = "juice"
- VWAP-centric risk management
- Unidirectional per trade (follow the momentum)

Key Concept:
When YEST/PRE/OPEN/1H/15M/5M/1M all show green ✅
= MAX JUICE = High probability of continuation

VWAP Distance:
- Near VWAP = low risk entry (value area)
- Far from VWAP = high risk (stretched like RSI)
- Pullback to VWAP = opportunity

Directional Bias:
- All green timeframes = BULLISH ONLY (long trades)
- All red timeframes = BEARISH ONLY (short trades)
- Mixed = NO TRADE (wait for alignment)
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from datetime import datetime, time
import statistics

sys.path.insert(0, str(Path(__file__).parent))
from murphy_classifier_v2 import Bar


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MomoSignal:
    """Momo classifier output"""
    direction: str  # "↑" (bullish), "↓" (bearish), "−" (no alignment)
    stars: int  # 0-7 (number of aligned timeframes)
    juice_score: float  # 0.0-1.0 (strength of alignment)

    # Multi-timeframe changes
    yest_change: float  # % change from yesterday close to today open
    pre_change: float   # % change during premarket
    open_change: float  # % change from open to now
    h1_change: float    # % change from 1 hour ago
    m15_change: float   # % change from 15 minutes ago
    m5_change: float    # % change from 5 minutes ago
    m1_change: float    # % change from 1 minute ago

    # VWAP analysis
    vwap: float
    vwap_distance: float  # % distance from VWAP (like RSI)
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "EXTREME"

    # Context
    price: float
    volume: float
    alignment_count: int  # How many timeframes align

    interpretation: str


# ============================================================================
# MOMO CLASSIFIER
# ============================================================================

class MomoClassifier:
    """
    Multi-timeframe momentum classifier with VWAP analysis.

    Unidirectional: Only trades in direction of momentum.
    """

    def __init__(
        self,
        premarket_start: time = time(4, 0),   # 4:00 AM
        market_open: time = time(9, 30),      # 9:30 AM
        alignment_threshold: float = 0.70     # 70% of timeframes must align
    ):
        self.premarket_start = premarket_start
        self.market_open = market_open
        self.alignment_threshold = alignment_threshold

    def classify(
        self,
        bars: List[Bar],
        signal_index: int,
        yesterday_close: Optional[float] = None
    ) -> MomoSignal:
        """
        Classify momentum at a specific bar.

        Args:
            bars: List of historical bars
            signal_index: Index of current bar to classify
            yesterday_close: Optional yesterday's close price

        Returns:
            MomoSignal with multi-timeframe analysis
        """
        if signal_index < 60:  # Need at least 60 bars of history
            return self._neutral_signal(bars[signal_index])

        current_bar = bars[signal_index]
        current_price = current_bar.close

        # Calculate VWAP
        vwap = self._calculate_vwap(bars, signal_index)
        vwap_distance = ((current_price - vwap) / vwap) * 100 if vwap > 0 else 0.0

        # Determine risk level based on VWAP distance
        risk_level = self._calculate_risk_level(abs(vwap_distance))

        # Calculate multi-timeframe changes
        yest_change = self._calculate_yest_change(bars, signal_index, yesterday_close)
        pre_change = self._calculate_premarket_change(bars, signal_index)
        open_change = self._calculate_open_change(bars, signal_index)
        h1_change = self._calculate_timeframe_change(bars, signal_index, minutes=60)
        m15_change = self._calculate_timeframe_change(bars, signal_index, minutes=15)
        m5_change = self._calculate_timeframe_change(bars, signal_index, minutes=5)
        m1_change = self._calculate_timeframe_change(bars, signal_index, minutes=1)

        # Count alignment
        changes = {
            'YEST': yest_change,
            'PRE': pre_change,
            'OPEN': open_change,
            '1H': h1_change,
            '15M': m15_change,
            '5M': m5_change,
            '1M': m1_change
        }

        # Filter out None values
        valid_changes = {k: v for k, v in changes.items() if v is not None}

        if not valid_changes:
            return self._neutral_signal(current_bar, vwap, vwap_distance, risk_level)

        # Count how many are bullish vs bearish
        bullish_count = sum(1 for v in valid_changes.values() if v > 0)
        bearish_count = sum(1 for v in valid_changes.values() if v < 0)
        total_count = len(valid_changes)

        # Determine direction based on alignment
        if bullish_count >= total_count * self.alignment_threshold:
            direction = "↑"
            stars = bullish_count
            alignment_count = bullish_count
        elif bearish_count >= total_count * self.alignment_threshold:
            direction = "↓"
            stars = bearish_count
            alignment_count = bearish_count
        else:
            direction = "−"
            stars = max(bullish_count, bearish_count)
            alignment_count = 0

        # Calculate juice score (strength of alignment)
        if total_count > 0:
            juice_score = alignment_count / total_count
        else:
            juice_score = 0.0

        # Build interpretation
        interpretation = self._build_interpretation(
            direction, stars, juice_score, vwap_distance, risk_level, valid_changes
        )

        return MomoSignal(
            direction=direction,
            stars=stars,
            juice_score=juice_score,
            yest_change=yest_change,
            pre_change=pre_change,
            open_change=open_change,
            h1_change=h1_change,
            m15_change=m15_change,
            m5_change=m5_change,
            m1_change=m1_change,
            vwap=vwap,
            vwap_distance=vwap_distance,
            risk_level=risk_level,
            price=current_price,
            volume=current_bar.volume,
            alignment_count=alignment_count,
            interpretation=interpretation
        )

    def _calculate_vwap(self, bars: List[Bar], signal_index: int) -> float:
        """
        Calculate VWAP from session start to current bar.

        VWAP = Sum(Price × Volume) / Sum(Volume)
        """
        # Find session start (market open at 9:30 AM)
        session_start = None

        for i in range(signal_index, max(0, signal_index - 200), -1):
            bar_time = self._parse_time(bars[i].timestamp)
            if bar_time and bar_time >= self.market_open:
                session_start = i
            else:
                break

        if session_start is None:
            # Use last 60 bars as fallback
            session_start = max(0, signal_index - 60)

        # Calculate VWAP
        total_pv = 0.0
        total_v = 0.0

        for i in range(session_start, signal_index + 1):
            typical_price = (bars[i].high + bars[i].low + bars[i].close) / 3
            total_pv += typical_price * bars[i].volume
            total_v += bars[i].volume

        if total_v > 0:
            return total_pv / total_v
        else:
            return bars[signal_index].close

    def _calculate_risk_level(self, abs_distance: float) -> str:
        """Calculate risk level based on VWAP distance"""
        if abs_distance < 2.0:
            return "LOW"      # Within 2% of VWAP = value area
        elif abs_distance < 5.0:
            return "MEDIUM"   # 2-5% = moderate risk
        elif abs_distance < 10.0:
            return "HIGH"     # 5-10% = high risk
        else:
            return "EXTREME"  # >10% = extremely stretched

    def _calculate_yest_change(
        self,
        bars: List[Bar],
        signal_index: int,
        yesterday_close: Optional[float]
    ) -> Optional[float]:
        """Calculate % change from yesterday close to today open"""
        if yesterday_close is None:
            # Try to find yesterday's close in data
            yesterday_close = self._find_yesterday_close(bars, signal_index)

        if yesterday_close is None:
            return None

        # Find today's open (first bar at or after market open)
        today_open = self._find_today_open(bars, signal_index)

        if today_open is None:
            return None

        return ((today_open - yesterday_close) / yesterday_close) * 100

    def _calculate_premarket_change(self, bars: List[Bar], signal_index: int) -> Optional[float]:
        """Calculate % change during premarket"""
        # Find premarket start (4:00 AM)
        premarket_start_price = None
        premarket_end_price = None

        for i in range(max(0, signal_index - 400), signal_index + 1):
            bar_time = self._parse_time(bars[i].timestamp)
            if bar_time is None:
                continue

            # Premarket start
            if bar_time >= self.premarket_start and premarket_start_price is None:
                premarket_start_price = bars[i].open

            # Premarket end (just before market open)
            if bar_time >= self.market_open:
                premarket_end_price = bars[i-1].close if i > 0 else None
                break

        if premarket_start_price and premarket_end_price:
            return ((premarket_end_price - premarket_start_price) / premarket_start_price) * 100

        return None

    def _calculate_open_change(self, bars: List[Bar], signal_index: int) -> Optional[float]:
        """Calculate % change from market open to current price"""
        today_open = self._find_today_open(bars, signal_index)

        if today_open is None:
            return None

        current_price = bars[signal_index].close
        return ((current_price - today_open) / today_open) * 100

    def _calculate_timeframe_change(
        self,
        bars: List[Bar],
        signal_index: int,
        minutes: int
    ) -> Optional[float]:
        """Calculate % change over a specific timeframe"""
        if signal_index < minutes:
            return None

        past_bar = bars[signal_index - minutes]
        current_bar = bars[signal_index]

        return ((current_bar.close - past_bar.close) / past_bar.close) * 100

    def _find_yesterday_close(self, bars: List[Bar], signal_index: int) -> Optional[float]:
        """Try to find yesterday's closing price"""
        # Look back for end of previous day (before 4:00 AM of current day)
        current_time = self._parse_time(bars[signal_index].timestamp)
        if current_time is None:
            return None

        current_date = self._parse_date(bars[signal_index].timestamp)

        # Look back up to 1000 bars for previous day
        for i in range(signal_index - 1, max(0, signal_index - 1000), -1):
            bar_date = self._parse_date(bars[i].timestamp)
            if bar_date and bar_date != current_date:
                # Found previous day, return its last close
                return bars[i].close

        return None

    def _find_today_open(self, bars: List[Bar], signal_index: int) -> Optional[float]:
        """Find today's market open price (9:30 AM)"""
        # Look back for first bar at or after market open
        for i in range(max(0, signal_index - 400), signal_index + 1):
            bar_time = self._parse_time(bars[i].timestamp)
            if bar_time and bar_time >= self.market_open:
                return bars[i].open

        return None

    def _parse_time(self, timestamp: str) -> Optional[time]:
        """Parse time from timestamp string"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.time()
        except:
            return None

    def _parse_date(self, timestamp: str) -> Optional[str]:
        """Parse date from timestamp string"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except:
            return None

    def _neutral_signal(
        self,
        bar: Bar,
        vwap: float = 0.0,
        vwap_distance: float = 0.0,
        risk_level: str = "MEDIUM"
    ) -> MomoSignal:
        """Return a neutral signal when we don't have enough data"""
        return MomoSignal(
            direction="−",
            stars=0,
            juice_score=0.0,
            yest_change=None,
            pre_change=None,
            open_change=None,
            h1_change=None,
            m15_change=None,
            m5_change=None,
            m1_change=None,
            vwap=vwap if vwap > 0 else bar.close,
            vwap_distance=vwap_distance,
            risk_level=risk_level,
            price=bar.close,
            volume=bar.volume,
            alignment_count=0,
            interpretation="Insufficient data for momentum analysis"
        )

    def _build_interpretation(
        self,
        direction: str,
        stars: int,
        juice_score: float,
        vwap_distance: float,
        risk_level: str,
        changes: Dict[str, float]
    ) -> str:
        """Build human-readable interpretation"""

        # Direction description
        if direction == "↑":
            dir_str = "BULLISH MOMENTUM"
        elif direction == "↓":
            dir_str = "BEARISH MOMENTUM"
        else:
            dir_str = "NO CLEAR MOMENTUM"

        # Juice description
        if juice_score >= 0.85:
            juice_str = "MAX JUICE"
        elif juice_score >= 0.70:
            juice_str = "STRONG JUICE"
        elif juice_score >= 0.50:
            juice_str = "MODERATE JUICE"
        else:
            juice_str = "WEAK JUICE"

        # VWAP position
        if vwap_distance > 2:
            vwap_str = f"Above VWAP +{vwap_distance:.1f}%"
        elif vwap_distance < -2:
            vwap_str = f"Below VWAP {vwap_distance:.1f}%"
        else:
            vwap_str = f"Near VWAP ({vwap_distance:+.1f}%)"

        # Build interpretation
        interp = f"{dir_str} | {juice_str} ({stars}/{len(changes)}) | {vwap_str} | Risk: {risk_level}"

        # Add timeframe details
        timeframe_str = " | ".join([
            f"{k}:{v:+.1f}%" for k, v in changes.items() if v is not None
        ])

        return f"{interp}\n{timeframe_str}"


# ============================================================================
# TESTING
# ============================================================================

def test_momo_classifier(data_file: str, focus_date: str = "2025-10-20"):
    """Test Momo classifier on historical data"""
    import json

    print("=" * 100)
    print("MOMO CLASSIFIER TEST")
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

    # Initialize classifier
    classifier = MomoClassifier()

    # Test on first 50 bars of focus date
    print(f"{'Bar':<6} {'Time':<20} {'Price':<8} {'Dir':<4} {'Stars':<6} {'Juice':<8} {'VWAP Dist':<12} {'Risk':<8}")
    print("-" * 100)

    for i in range(start_bar, min(start_bar + 50, len(bars)), 5):  # Every 5 bars
        signal = classifier.classify(bars, i, yesterday_close=0.73)  # BYND closed at $0.73 on Oct 19

        print(f"{i:<6} {bars[i].timestamp[11:19]:<20} ${signal.price:<7.2f} "
              f"{signal.direction:<4} {signal.stars}/7    {signal.juice_score:<7.1%} "
              f"{signal.vwap_distance:>+6.1f}%      {signal.risk_level:<8}")

    # Show detailed analysis for a few key bars
    print("\n" + "=" * 100)
    print("DETAILED ANALYSIS")
    print("=" * 100)

    for bar_offset in [0, 20, 40]:
        i = start_bar + bar_offset
        if i >= len(bars):
            continue

        signal = classifier.classify(bars, i, yesterday_close=0.73)

        print(f"\nBar {i} ({bars[i].timestamp}):")
        print(f"  Price: ${signal.price:.2f}")
        print(f"  Direction: {signal.direction}")
        print(f"  Stars: {signal.stars}/7")
        print(f"  Juice Score: {signal.juice_score:.1%}")
        print(f"  VWAP: ${signal.vwap:.2f}")
        print(f"  VWAP Distance: {signal.vwap_distance:+.2f}%")
        print(f"  Risk Level: {signal.risk_level}")
        print(f"  \nTimeframe Changes:")
        if signal.yest_change: print(f"    YEST: {signal.yest_change:+.2f}%")
        if signal.pre_change: print(f"    PRE:  {signal.pre_change:+.2f}%")
        if signal.open_change: print(f"    OPEN: {signal.open_change:+.2f}%")
        if signal.h1_change: print(f"    1H:   {signal.h1_change:+.2f}%")
        if signal.m15_change: print(f"    15M:  {signal.m15_change:+.2f}%")
        if signal.m5_change: print(f"    5M:   {signal.m5_change:+.2f}%")
        if signal.m1_change: print(f"    1M:   {signal.m1_change:+.2f}%")
        print(f"  \nInterpretation:")
        print(f"    {signal.interpretation}")

    print("\n" + "=" * 100)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Momo Classifier Test')
    parser.add_argument('--data', type=str, default='bynd_historical_data.json')
    parser.add_argument('--date', type=str, default='2025-10-20')

    args = parser.parse_args()

    test_momo_classifier(args.data, args.date)
