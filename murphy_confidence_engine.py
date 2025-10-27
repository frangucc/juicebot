#!/usr/bin/env python3
"""
Murphy Confidence Engine
========================

Treats Murphy as a continuous probability monitor, not a discrete signal generator.

Core Concept:
- Murphy provides a "pulse" or "rhythm" of the market
- Track Murphy's recent accuracy (hot streak detection)
- Analyze price patterns (higher highs/lows)
- Monitor structure formation (BoS upside vs downside)
- Compare move magnitudes (bull moves vs bear moves)
- Output: Confidence score (0-100%) for execution decisions

Usage:
    engine = MurphyConfidenceEngine(lookback=50)

    # Update bar by bar
    engine.update(bar, murphy_signal)

    # Get current confidence
    confidence = engine.get_confidence()

    # Use confidence to weight decisions
    if confidence > 0.80:
        SCALE_IN_LARGE()
    elif confidence > 0.60:
        SCALE_IN_MEDIUM()
    elif confidence > 0.40:
        SCALE_IN_SMALL()
    else:
        WAIT()
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from collections import deque
import statistics

# Import Murphy types from root directory
sys.path.insert(0, str(Path(__file__).parent))

from murphy_classifier_v2 import Bar, MurphySignal


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SignalResult:
    """Tracks a Murphy signal and its eventual outcome"""
    bar_index: int
    signal: MurphySignal
    entry_price: float

    # Outcome tracking
    bars_elapsed: int = 0
    current_price: float = 0.0
    max_favorable_move: float = 0.0  # Best move in signal direction
    max_adverse_move: float = 0.0    # Worst move against signal

    # Final result (after N bars or direction change)
    is_correct: Optional[bool] = None
    pnl_pct: float = 0.0

    def update(self, current_bar: Bar):
        """Update this signal's outcome with current bar data"""
        self.bars_elapsed += 1
        self.current_price = current_bar.close

        # Calculate move from entry
        move_pct = ((self.current_price - self.entry_price) / self.entry_price) * 100

        # Track favorable/adverse moves based on signal direction
        if self.signal.direction == "↑":
            # Bullish signal - up is favorable
            if move_pct > self.max_favorable_move:
                self.max_favorable_move = move_pct
            if move_pct < -self.max_adverse_move:
                self.max_adverse_move = abs(move_pct)
        elif self.signal.direction == "↓":
            # Bearish signal - down is favorable
            if move_pct < -self.max_favorable_move:
                self.max_favorable_move = abs(move_pct)
            if move_pct > self.max_adverse_move:
                self.max_adverse_move = move_pct

        # Update P&L
        if self.signal.direction == "↑":
            self.pnl_pct = move_pct
        elif self.signal.direction == "↓":
            self.pnl_pct = -move_pct
        else:  # Neutral
            self.pnl_pct = 0.0

    def finalize(self, threshold: float = 1.0):
        """
        Determine if signal was correct.

        Args:
            threshold: % move needed to consider signal correct (default 1%)
        """
        if self.signal.direction == "−":
            # Neutral signals - correct if no big move either way
            self.is_correct = abs(self.pnl_pct) < threshold
        else:
            # Directional signals - correct if moved in predicted direction
            self.is_correct = self.pnl_pct > threshold


@dataclass
class PriceSwing:
    """Tracks a swing high or swing low"""
    bar_index: int
    price: float
    swing_type: str  # "high" or "low"
    volume: float


@dataclass
class StructureLevel:
    """Tracks a BoS or CHoCH level"""
    bar_index: int
    level_price: float
    level_type: str  # "bos" or "choch"
    direction: str   # "↑" or "↓"
    volume: float


@dataclass
class Move:
    """Tracks a price move (bull or bear)"""
    start_bar: int
    end_bar: int
    start_price: float
    end_price: float
    direction: str  # "bull" or "bear"
    magnitude_pct: float
    avg_volume: float


# ============================================================================
# MURPHY CONFIDENCE ENGINE
# ============================================================================

class MurphyConfidenceEngine:
    """
    Continuous probability monitor for Murphy signals.

    Tracks:
    1. Recent accuracy (rolling window)
    2. Price patterns (higher highs/lows)
    3. Structure rhythm (BoS/CHoCH counts)
    4. Move magnitudes (bull vs bear)
    5. Overall confidence score
    """

    def __init__(
        self,
        lookback: int = 50,
        accuracy_window: int = 20,
        pattern_window: int = 30,
        structure_window: int = 40
    ):
        """
        Args:
            lookback: How many bars to look back for pattern detection
            accuracy_window: How many recent signals to track for accuracy
            pattern_window: How many bars for pattern analysis
            structure_window: How many bars for structure analysis
        """
        self.lookback = lookback
        self.accuracy_window = accuracy_window
        self.pattern_window = pattern_window
        self.structure_window = structure_window

        # Signal tracking
        self.active_signals: deque[SignalResult] = deque(maxlen=accuracy_window)
        self.recent_signals: deque[SignalResult] = deque(maxlen=accuracy_window)

        # Price tracking
        self.bars: deque[Bar] = deque(maxlen=lookback)
        self.swing_highs: deque[PriceSwing] = deque(maxlen=pattern_window)
        self.swing_lows: deque[PriceSwing] = deque(maxlen=pattern_window)

        # Structure tracking
        self.bos_levels: deque[StructureLevel] = deque(maxlen=structure_window)
        self.choch_levels: deque[StructureLevel] = deque(maxlen=structure_window)

        # Move tracking
        self.bull_moves: deque[Move] = deque(maxlen=20)
        self.bear_moves: deque[Move] = deque(maxlen=20)

        # Current state
        self.current_bar_index = 0
        self.session_high = 0.0
        self.session_low = float('inf')

    def update(self, bar: Bar, signal: Optional[MurphySignal] = None):
        """
        Update the confidence engine with a new bar and optional Murphy signal.

        Args:
            bar: Current price bar
            signal: Murphy signal for this bar (if any)
        """
        self.current_bar_index += 1
        self.bars.append(bar)

        # Update session high/low
        if bar.high > self.session_high:
            self.session_high = bar.high
        if bar.low < self.session_low:
            self.session_low = bar.low

        # Update active signals (track their outcomes)
        self._update_active_signals(bar)

        # Add new signal if provided
        if signal and signal.direction in ["↑", "↓", "−"]:
            self._add_new_signal(bar, signal)

        # Detect swing highs/lows
        self._detect_swings(bar)

        # Detect structure levels (BoS/CHoCH)
        if signal:
            self._detect_structure(bar, signal)

        # Detect moves (bull/bear)
        self._detect_moves(bar)

    def _update_active_signals(self, bar: Bar):
        """Update all active signals with current bar data"""
        for sig_result in self.active_signals:
            sig_result.update(bar)

            # Finalize signals after N bars (e.g., 20 bars)
            if sig_result.bars_elapsed >= 20 and sig_result.is_correct is None:
                sig_result.finalize(threshold=1.0)
                self.recent_signals.append(sig_result)

    def _add_new_signal(self, bar: Bar, signal: MurphySignal):
        """Add a new Murphy signal to track"""
        sig_result = SignalResult(
            bar_index=self.current_bar_index,
            signal=signal,
            entry_price=bar.close
        )
        self.active_signals.append(sig_result)

    def _detect_swings(self, bar: Bar):
        """Detect swing highs and swing lows"""
        if len(self.bars) < 5:
            return

        # Look at bar 2 positions back (need 2 bars on each side)
        bars_list = list(self.bars)
        if len(bars_list) < 5:
            return

        check_bar = bars_list[-3]  # 2 bars back
        left_2 = bars_list[-5]
        left_1 = bars_list[-4]
        right_1 = bars_list[-2]
        right_2 = bars_list[-1]

        # Swing high: higher than 2 bars on each side
        if (check_bar.high > left_2.high and check_bar.high > left_1.high and
            check_bar.high > right_1.high and check_bar.high > right_2.high):
            self.swing_highs.append(PriceSwing(
                bar_index=self.current_bar_index - 2,
                price=check_bar.high,
                swing_type="high",
                volume=check_bar.volume
            ))

        # Swing low: lower than 2 bars on each side
        if (check_bar.low < left_2.low and check_bar.low < left_1.low and
            check_bar.low < right_1.low and check_bar.low < right_2.low):
            self.swing_lows.append(PriceSwing(
                bar_index=self.current_bar_index - 2,
                price=check_bar.low,
                swing_type="low",
                volume=check_bar.volume
            ))

    def _detect_structure(self, bar: Bar, signal: MurphySignal):
        """Detect BoS and CHoCH levels from Murphy signals"""
        # Check interpretation string for BoS/CHoCH mentions
        interpretation = signal.interpretation.lower()

        if "bos" in interpretation or "break of structure" in interpretation:
            self.bos_levels.append(StructureLevel(
                bar_index=self.current_bar_index,
                level_price=bar.close,
                level_type="bos",
                direction=signal.direction,
                volume=bar.volume
            ))

        if "choch" in interpretation or "change of character" in interpretation:
            self.choch_levels.append(StructureLevel(
                bar_index=self.current_bar_index,
                level_price=bar.close,
                level_type="choch",
                direction=signal.direction,
                volume=bar.volume
            ))

    def _detect_moves(self, bar: Bar):
        """Detect and track bull/bear moves"""
        if len(self.bars) < 10:
            return

        bars_list = list(self.bars)

        # Look for moves in recent bars (last 10)
        recent_bars = bars_list[-10:]
        start_price = recent_bars[0].close
        end_price = recent_bars[-1].close

        magnitude_pct = ((end_price - start_price) / start_price) * 100
        avg_volume = statistics.mean([b.volume for b in recent_bars])

        # Only track significant moves (> 1%)
        if abs(magnitude_pct) > 1.0:
            move = Move(
                start_bar=self.current_bar_index - 10,
                end_bar=self.current_bar_index,
                start_price=start_price,
                end_price=end_price,
                direction="bull" if magnitude_pct > 0 else "bear",
                magnitude_pct=abs(magnitude_pct),
                avg_volume=avg_volume
            )

            if magnitude_pct > 0:
                self.bull_moves.append(move)
            else:
                self.bear_moves.append(move)

    # ========================================================================
    # ANALYSIS METHODS
    # ========================================================================

    def get_recent_accuracy(self) -> float:
        """
        Get Murphy's recent accuracy (rolling window).

        Returns:
            Accuracy as 0.0-1.0 (e.g., 0.75 = 75% accurate)
        """
        finalized = [s for s in self.recent_signals if s.is_correct is not None]

        if not finalized:
            return 0.50  # Default to 50% if no data

        correct_count = sum(1 for s in finalized if s.is_correct)
        return correct_count / len(finalized)

    def get_pattern_score(self) -> Tuple[float, str]:
        """
        Analyze price pattern (higher highs/lows).

        Returns:
            (score, pattern_type)
            score: 0.0-1.0 (1.0 = strong uptrend)
            pattern_type: "uptrend", "downtrend", "sideways"
        """
        if len(self.swing_highs) < 3 or len(self.swing_lows) < 3:
            return 0.50, "sideways"

        # Check last 3 swing highs
        recent_highs = list(self.swing_highs)[-3:]
        highs_ascending = all(
            recent_highs[i].price < recent_highs[i+1].price
            for i in range(len(recent_highs)-1)
        )

        # Check last 3 swing lows
        recent_lows = list(self.swing_lows)[-3:]
        lows_ascending = all(
            recent_lows[i].price < recent_lows[i+1].price
            for i in range(len(recent_lows)-1)
        )

        # Uptrend: higher highs AND higher lows
        if highs_ascending and lows_ascending:
            return 0.90, "uptrend"

        # Downtrend: lower highs AND lower lows
        highs_descending = all(
            recent_highs[i].price > recent_highs[i+1].price
            for i in range(len(recent_highs)-1)
        )
        lows_descending = all(
            recent_lows[i].price > recent_lows[i+1].price
            for i in range(len(recent_lows)-1)
        )

        if highs_descending and lows_descending:
            return 0.10, "downtrend"

        # Mixed or consolidating
        if highs_ascending or lows_ascending:
            return 0.65, "sideways"

        return 0.50, "sideways"

    def get_structure_bias(self) -> Tuple[float, Dict]:
        """
        Get structure bias (BoS/CHoCH direction).

        Returns:
            (bias_score, details)
            bias_score: 0.0-1.0 (1.0 = strong bullish structure)
            details: dict with counts
        """
        if not self.bos_levels and not self.choch_levels:
            return 0.50, {"upside_bos": 0, "downside_bos": 0, "total": 0}

        # Count recent BoS levels by direction
        recent_bos = list(self.bos_levels)[-20:]  # Last 20 BoS levels

        upside_bos = sum(1 for b in recent_bos if b.direction == "↑")
        downside_bos = sum(1 for b in recent_bos if b.direction == "↓")

        total_bos = upside_bos + downside_bos

        if total_bos == 0:
            return 0.50, {"upside_bos": 0, "downside_bos": 0, "total": 0}

        # Calculate bias score
        bias_score = upside_bos / total_bos

        # Check CHoCH for reversal signals
        recent_choch = list(self.choch_levels)[-5:]  # Last 5 CHoCH
        downside_choch = sum(1 for c in recent_choch if c.direction == "↓")

        # Downside CHoCH reduces bullish bias
        if downside_choch > 0:
            bias_score *= (1.0 - (downside_choch * 0.1))  # Reduce by 10% per downside CHoCH

        return bias_score, {
            "upside_bos": upside_bos,
            "downside_bos": downside_bos,
            "total": total_bos,
            "recent_choch_down": downside_choch
        }

    def get_move_magnitude_ratio(self) -> Tuple[float, Dict]:
        """
        Compare bull vs bear move magnitudes.

        Returns:
            (ratio_score, details)
            ratio_score: 0.0-1.0 (1.0 = bull moves much larger)
            details: dict with move stats
        """
        if not self.bull_moves and not self.bear_moves:
            return 0.50, {"bull_avg": 0, "bear_avg": 0, "ratio": 1.0}

        # Calculate average magnitudes
        bull_avg = statistics.mean([m.magnitude_pct for m in self.bull_moves]) if self.bull_moves else 0.0
        bear_avg = statistics.mean([m.magnitude_pct for m in self.bear_moves]) if self.bear_moves else 0.0

        if bear_avg == 0:
            ratio = 10.0 if bull_avg > 0 else 1.0
        else:
            ratio = bull_avg / bear_avg

        # Convert ratio to 0-1 score
        # ratio = 3.0 means bull moves 3x larger = score ~0.85
        # ratio = 1.0 means equal = score 0.50
        # ratio = 0.33 means bear moves 3x larger = score ~0.15

        if ratio >= 1.0:
            # Bull moves larger
            score = 0.50 + min(0.45, (ratio - 1.0) * 0.15)
        else:
            # Bear moves larger
            score = 0.50 - min(0.45, (1.0 / ratio - 1.0) * 0.15)

        return score, {
            "bull_avg": bull_avg,
            "bear_avg": bear_avg,
            "ratio": ratio,
            "bull_count": len(self.bull_moves),
            "bear_count": len(self.bear_moves)
        }

    def get_volume_trend(self) -> Tuple[float, str]:
        """
        Analyze volume trend (increasing vs decreasing).

        Returns:
            (score, trend)
            score: 0.0-1.0 (1.0 = volume increasing)
            trend: "increasing", "decreasing", "stable"
        """
        if len(self.bars) < 10:
            return 0.50, "stable"

        bars_list = list(self.bars)
        recent_10 = bars_list[-10:]

        # Compare first 5 vs last 5
        first_5_avg = statistics.mean([b.volume for b in recent_10[:5]])
        last_5_avg = statistics.mean([b.volume for b in recent_10[5:]])

        if last_5_avg > first_5_avg * 1.5:
            return 0.85, "increasing"
        elif last_5_avg > first_5_avg * 1.1:
            return 0.65, "increasing"
        elif last_5_avg < first_5_avg * 0.7:
            return 0.15, "decreasing"
        elif last_5_avg < first_5_avg * 0.9:
            return 0.35, "decreasing"
        else:
            return 0.50, "stable"

    def get_confidence(self, bias: str = "bullish") -> Dict:
        """
        Get overall confidence score for execution decisions.

        Args:
            bias: Session bias ("bullish" or "bearish")

        Returns:
            Dict with:
                - confidence_score: 0.0-1.0
                - components: individual component scores
                - recommendation: "high", "medium", "low", "wait"
        """
        # Get all components
        accuracy = self.get_recent_accuracy()
        pattern_score, pattern_type = self.get_pattern_score()
        structure_score, structure_details = self.get_structure_bias()
        magnitude_score, magnitude_details = self.get_move_magnitude_ratio()
        volume_score, volume_trend = self.get_volume_trend()

        # Weight components based on bias
        if bias == "bullish":
            # For bullish bias, weight factors that confirm uptrend
            weights = {
                'accuracy': 0.25,      # Murphy's recent correctness
                'pattern': 0.20,       # Higher highs/lows
                'structure': 0.25,     # BoS upside vs downside
                'magnitude': 0.20,     # Bull moves vs bear moves
                'volume': 0.10         # Volume trend
            }
        else:  # bearish
            # For bearish bias, invert pattern and magnitude scores
            pattern_score = 1.0 - pattern_score
            magnitude_score = 1.0 - magnitude_score
            structure_score = 1.0 - structure_score

            weights = {
                'accuracy': 0.25,
                'pattern': 0.20,
                'structure': 0.25,
                'magnitude': 0.20,
                'volume': 0.10
            }

        # Calculate weighted confidence
        confidence_score = (
            accuracy * weights['accuracy'] +
            pattern_score * weights['pattern'] +
            structure_score * weights['structure'] +
            magnitude_score * weights['magnitude'] +
            volume_score * weights['volume']
        )

        # Determine recommendation
        if confidence_score >= 0.75:
            recommendation = "high"
        elif confidence_score >= 0.60:
            recommendation = "medium"
        elif confidence_score >= 0.45:
            recommendation = "low"
        else:
            recommendation = "wait"

        return {
            'confidence_score': confidence_score,
            'recommendation': recommendation,
            'components': {
                'accuracy': accuracy,
                'pattern': {'score': pattern_score, 'type': pattern_type},
                'structure': {'score': structure_score, 'details': structure_details},
                'magnitude': {'score': magnitude_score, 'details': magnitude_details},
                'volume': {'score': volume_score, 'trend': volume_trend}
            },
            'weights': weights
        }

    def get_status_summary(self) -> str:
        """Get human-readable status summary"""
        confidence_data = self.get_confidence()

        summary = f"""
Murphy Confidence Engine Status
================================
Confidence Score: {confidence_data['confidence_score']:.1%}
Recommendation:   {confidence_data['recommendation'].upper()}

Components:
- Recent Accuracy:  {confidence_data['components']['accuracy']:.1%}
- Pattern:          {confidence_data['components']['pattern']['type']} ({confidence_data['components']['pattern']['score']:.1%})
- Structure Bias:   {confidence_data['components']['structure']['score']:.1%} ({confidence_data['components']['structure']['details']['upside_bos']} up, {confidence_data['components']['structure']['details']['downside_bos']} down)
- Move Magnitude:   Bull/Bear {confidence_data['components']['magnitude']['details']['ratio']:.2f}x ({confidence_data['components']['magnitude']['score']:.1%})
- Volume Trend:     {confidence_data['components']['volume']['trend']} ({confidence_data['components']['volume']['score']:.1%})

Active Signals:     {len(self.active_signals)}
Recent Signals:     {len(self.recent_signals)}
Swing Highs:        {len(self.swing_highs)}
Swing Lows:         {len(self.swing_lows)}
BoS Levels:         {len(self.bos_levels)}
CHoCH Levels:       {len(self.choch_levels)}
"""
        return summary


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def test_confidence_engine(data_file: str, focus_date: Optional[str] = None):
    """
    Test the confidence engine on historical data.

    Args:
        data_file: Path to historical data JSON
        focus_date: Optional date to focus on
    """
    import json
    from murphy_classifier_v2 import MurphyClassifier

    print("=" * 80)
    print("MURPHY CONFIDENCE ENGINE TEST")
    print("=" * 80)

    # Load data
    print(f"\nLoading data from: {data_file}")
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

    print(f"Loaded {len(bars)} bars\n")

    # Find focus date bars
    start_bar = 0
    if focus_date:
        for i, bar in enumerate(bars):
            if focus_date in bar.timestamp:
                start_bar = i
                break
        print(f"Starting at bar {start_bar} ({bars[start_bar].timestamp})")

    # Initialize
    engine = MurphyConfidenceEngine(lookback=50, accuracy_window=20)
    classifier = MurphyClassifier()

    # Run through bars
    print("\nProcessing bars and tracking confidence...\n")

    confidence_history = []

    for i in range(start_bar, min(start_bar + 200, len(bars))):  # Process first 200 bars
        bar = bars[i]

        # Generate Murphy signal
        signal = classifier.classify(
            bars=bars,
            signal_index=i,
            structure_age_bars=50,
            level_price=None
        )

        # Update engine
        engine.update(bar, signal)

        # Get confidence every 10 bars
        if i % 10 == 0:
            confidence_data = engine.get_confidence(bias="bullish")
            confidence_history.append({
                'bar': i,
                'timestamp': bar.timestamp,
                'price': bar.close,
                'confidence': confidence_data['confidence_score'],
                'recommendation': confidence_data['recommendation']
            })

            print(f"Bar {i:4d} | {bar.timestamp} | ${bar.close:.2f} | "
                  f"Confidence: {confidence_data['confidence_score']:.1%} ({confidence_data['recommendation'].upper()})")

    # Final summary
    print("\n" + "=" * 80)
    print(engine.get_status_summary())
    print("=" * 80)

    return engine, confidence_history


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Murphy Confidence Engine Test')
    parser.add_argument('--data', type=str, default='bynd_historical_data.json',
                        help='Path to historical data JSON')
    parser.add_argument('--date', type=str, default='2025-10-20',
                        help='Focus date')

    args = parser.parse_args()

    engine, history = test_confidence_engine(args.data, args.date)
