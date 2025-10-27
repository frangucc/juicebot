#!/usr/bin/env python3
"""
Murphy Regression Test V4 - CONFIDENCE-WEIGHTED EXECUTION
==========================================================

Evolution from V3:
- V3: Used Murphy signals directly (↑ = enter, ↓ = exit)
- V4: Uses Murphy Confidence Engine to weight decisions

Key Concept:
- Murphy Confidence = combination of recent accuracy, pattern, structure, magnitude, volume
- High confidence (>75%) = scale in large
- Medium confidence (60-75%) = scale in medium
- Low confidence (45-60%) = scale in small
- Very low (<45%) = wait

This treats Murphy as a continuous probability monitor, not a discrete signal generator.
"""

import json
import sys
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import statistics

# Add imports
sys.path.insert(0, str(Path(__file__).parent))

from murphy_classifier_v2 import MurphyClassifier, Bar, MurphySignal
from murphy_confidence_engine import MurphyConfidenceEngine


# Import V3 structures
from murphy_regression_test_v3 import (
    CONVICTION_RISK_MODES,
    ConvictionPosition,
    ConvictionTrade
)


# ============================================================================
# CONFIDENCE-WEIGHTED TRADER
# ============================================================================

class ConfidenceWeightedTrader:
    """
    Conviction trader that uses Murphy Confidence Engine for execution weighting.

    Key Differences from V3:
    - V3: "Murphy says ↑ → enter"
    - V4: "Murphy confidence 85% + pattern bullish → enter large"

    Decision Flow:
    1. Check if system wants to enter/add/exit
    2. Query Murphy Confidence Engine for current confidence
    3. Weight the decision based on confidence level
    4. Execute with appropriate sizing
    """

    def __init__(self, allocated_capital: float, risk_mode: str = 'medium'):
        self.allocated_capital = allocated_capital
        self.risk_mode = risk_mode
        self.config = CONVICTION_RISK_MODES[risk_mode]

        self.position: Optional[ConvictionPosition] = None
        self.completed_trades: List[ConvictionTrade] = []

        # Price tracking
        self.recent_bars: List[Bar] = []
        self.lookback = 20

        # Murphy Confidence Engine
        self.confidence_engine = MurphyConfidenceEngine(
            lookback=50,
            accuracy_window=20,
            pattern_window=30,
            structure_window=40
        )

    def execute_trade(
        self,
        bars: List[Bar],
        signals: List[MurphySignal],
        start_bar: int = 0,
        session_bias: str = "bullish",
        session_open_price: float = None,
        session_close_price: float = None,
        session_high: float = None,
        session_low: float = None
    ) -> None:
        """
        Execute confidence-weighted trading strategy.

        Args:
            bars: List of price bars
            signals: List of Murphy signals
            start_bar: Bar index to start trading
            session_bias: "bullish" or "bearish"
            session_open_price: Session open for metrics
            session_close_price: Session close for metrics
            session_high: Session high for metrics
            session_low: Session low for metrics
        """
        self.position = None
        self.recent_bars = []
        self.session_bias = session_bias

        for i in range(start_bar, len(bars)):
            bar = bars[i]
            signal = signals[i] if i < len(signals) else None

            # Update confidence engine
            self.confidence_engine.update(bar, signal)

            # Update recent bars
            self.recent_bars.append(bar)
            if len(self.recent_bars) > self.lookback:
                self.recent_bars.pop(0)

            # Update position high
            if self.position:
                self.position.update_high(i, bar.high)

            # Get current confidence
            confidence_data = self.confidence_engine.get_confidence(bias=session_bias)
            confidence_score = confidence_data['confidence_score']
            recommendation = confidence_data['recommendation']

            # Decision logic based on confidence
            if not self.position:
                # Check for initial entry
                self._check_initial_entry(i, bar, signal, confidence_score, recommendation)
            else:
                # Check for scale in
                self._check_scale_in(i, bar, signal, confidence_score, recommendation)

                # Check for scale out
                self._check_scale_out(i, bar, signal, confidence_score, recommendation)

                # Check time-based exit
                if self._check_time_exit(i, len(bars)):
                    self._exit_all(i, bar, "end_of_session")

        # Close any remaining position
        if self.position and len(bars) > 0:
            self._exit_all(len(bars) - 1, bars[-1], "end_of_data")

    def _check_initial_entry(
        self,
        bar_index: int,
        bar: Bar,
        signal: Optional[MurphySignal],
        confidence: float,
        recommendation: str
    ):
        """
        Check if we should make initial entry based on confidence.

        V3 logic: "if Murphy says ↑ and meets tier → enter"
        V4 logic: "if confidence is medium+ and pattern aligns → enter"
        """
        if not signal:
            return

        # Must have bullish signal for initial entry
        if signal.direction != "↑":
            return

        # Check minimum confidence threshold
        min_confidence = 0.55 if self.config['dip_buying'] == 'AGGRESSIVE' else 0.60

        if confidence < min_confidence:
            return

        # Size entry based on confidence
        if recommendation == "high":
            entry_pct = self.config['initial_entry_pct'] * 1.5  # Enter larger
        elif recommendation == "medium":
            entry_pct = self.config['initial_entry_pct']
        else:  # low
            entry_pct = self.config['initial_entry_pct'] * 0.75  # Enter smaller

        entry_capital = self.allocated_capital * entry_pct
        shares = int(entry_capital / bar.close)

        if shares <= 0:
            return

        self.position = ConvictionPosition(
            symbol="POSITION",
            direction="LONG",
            allocated_capital=self.allocated_capital
        )

        self.position.add_entry(bar_index, bar.close, shares)
        self.position.update_high(bar_index, bar.high)

    def _check_scale_in(
        self,
        bar_index: int,
        bar: Bar,
        signal: Optional[MurphySignal],
        confidence: float,
        recommendation: str
    ):
        """
        Check if we should add to position based on confidence.

        V3 logic: "if healthy dip + Murphy confirms support → add"
        V4 logic: "if healthy dip + HIGH confidence → add large, if MEDIUM confidence → add small"
        """
        if not self.position or not signal:
            return

        # Check if at max position
        position_pct = self.position.get_position_pct()
        if position_pct >= self.config['max_position_pct']:
            return

        # Check for dip
        is_dip, pullback_pct = self._is_healthy_dip(bar, bar_index)
        if not is_dip:
            return

        # Check if Murphy signal is bullish
        if signal.direction != "↑":
            return

        # V4: Weight add size by CONFIDENCE
        # High confidence + dip = aggressive add
        # Low confidence + dip = wait or small add

        if recommendation == "high":
            # High confidence: add aggressively
            add_multiplier = 1.5
        elif recommendation == "medium":
            # Medium confidence: standard add
            add_multiplier = 1.0
        elif recommendation == "low":
            # Low confidence: conservative add
            add_multiplier = 0.5
        else:  # wait
            # Very low confidence: skip
            return

        # Calculate add size
        remaining_capital = (self.allocated_capital * self.config['max_position_pct'] -
                           self.position.capital_deployed)

        base_add_pct = 0.30 if self.config['dip_buying'] == 'AGGRESSIVE' else 0.20
        add_pct = base_add_pct * add_multiplier

        add_capital = remaining_capital * add_pct
        shares = int(add_capital / bar.close)

        if shares > 0:
            self.position.add_entry(bar_index, bar.close, shares)

    def _check_scale_out(
        self,
        bar_index: int,
        bar: Bar,
        signal: Optional[MurphySignal],
        confidence: float,
        recommendation: str
    ):
        """
        Check if we should take profits based on confidence.

        V3 logic: "if Murphy shows weakness → exit"
        V4 logic: "if confidence drops + at resistance → exit"
        """
        if not self.position or self.position.shares_held == 0 or not signal:
            return

        # Check if at/near resistance
        at_resistance = bar.close >= self.position.highest_high * 0.95

        # V4: Exit based on CONFIDENCE DROP
        # If confidence was high and now drops to medium/low → take profits
        # If confidence drops to "wait" → exit aggressively

        if at_resistance:
            if recommendation == "wait":
                # Confidence dropped to very low at resistance → exit large
                shares_to_sell = int(self.position.shares_held * 0.50)
                if shares_to_sell > 0:
                    self.position.add_exit(bar_index, bar.close, shares_to_sell, "low_confidence_at_resistance")

            elif recommendation == "low" and confidence < 0.50:
                # Low confidence at resistance → exit medium
                shares_to_sell = int(self.position.shares_held * 0.30)
                if shares_to_sell > 0:
                    self.position.add_exit(bar_index, bar.close, shares_to_sell, "medium_confidence_at_resistance")

        # Also check for bearish signal with high confidence (reversal)
        if signal.direction == "↓" and recommendation in ["high", "medium"]:
            # High confidence bearish signal → exit
            shares_to_sell = int(self.position.shares_held * 0.40)
            if shares_to_sell > 0:
                self.position.add_exit(bar_index, bar.close, shares_to_sell, "high_confidence_reversal")

    def _is_healthy_dip(self, current_bar: Bar, bar_index: int) -> Tuple[bool, float]:
        """Check for healthy pullback"""
        if not self.position or self.position.highest_high == 0:
            return False, 0.0

        current_price = current_bar.close
        pullback_pct = (self.position.highest_high - current_price) / self.position.highest_high

        if pullback_pct < self.config['dip_threshold_min']:
            return False, pullback_pct

        if pullback_pct > self.config['dip_threshold_max']:
            return False, pullback_pct

        # Check volume (should not be panic selling)
        if len(self.recent_bars) >= 5:
            avg_volume = statistics.mean([b.volume for b in self.recent_bars[-5:]])
            if current_bar.volume > avg_volume * 2.0:
                if current_bar.close < current_bar.open:
                    return False, pullback_pct

        return True, pullback_pct

    def _check_time_exit(self, bar_index: int, total_bars: int) -> bool:
        """Check time-based exit"""
        return bar_index >= total_bars * 0.95

    def _exit_all(self, bar_index: int, bar: Bar, reason: str):
        """Exit entire position"""
        if not self.position or self.position.shares_held == 0:
            return

        shares_to_sell = self.position.shares_held
        self.position.add_exit(bar_index, bar.close, shares_to_sell, reason)

        # Create trade record
        if len(self.position.entries) > 0 and len(self.position.exits) > 0:
            trade = self._create_trade_record()
            self.completed_trades.append(trade)

        self.position = None

    def _create_trade_record(self) -> ConvictionTrade:
        """Create completed trade record"""
        if not self.position:
            return None

        total_shares_entered = sum(s for _, _, s in self.position.entries)
        total_shares_exited = sum(s for _, _, s, _ in self.position.exits)

        total_entry_cost = sum(p * s for _, p, s in self.position.entries)
        avg_entry = total_entry_cost / total_shares_entered if total_shares_entered > 0 else 0

        total_exit_proceeds = sum(p * s for _, p, s, _ in self.position.exits)
        avg_exit = total_exit_proceeds / total_shares_exited if total_shares_exited > 0 else 0

        realized_pnl = total_exit_proceeds - (avg_entry * total_shares_exited)
        realized_pnl_pct = (realized_pnl / (avg_entry * total_shares_exited)) * 100 if total_shares_exited > 0 else 0

        max_deployed = max(
            sum(p * s for _, p, s in self.position.entries[:i+1])
            for i in range(len(self.position.entries))
        )
        max_position_pct = (max_deployed / self.position.allocated_capital) * 100

        exit_reason = self.position.exits[-1][3] if self.position.exits else "unknown"

        return ConvictionTrade(
            symbol=self.position.symbol,
            entry_bar=self.position.entries[0][0],
            exit_bar=self.position.exits[-1][0] if self.position.exits else 0,
            bars_held=self.position.exits[-1][0] - self.position.entries[0][0] if self.position.exits else 0,
            entries=self.position.entries,
            exits=self.position.exits,
            avg_entry_price=avg_entry,
            avg_exit_price=avg_exit,
            total_shares=total_shares_exited,
            allocated_capital=self.position.allocated_capital,
            capital_deployed=self.position.capital_deployed,
            max_position_pct=max_position_pct,
            realized_pnl=realized_pnl,
            realized_pnl_pct=realized_pnl_pct,
            exit_reason=exit_reason,
            move_captured_pct=0.0,
            entry_efficiency=0.0,
            exit_efficiency=0.0
        )

    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        if not self.completed_trades:
            return {
                'total_trades': 0,
                'total_pnl': 0.0,
                'total_pnl_pct': 0.0,
            }

        total_pnl = sum(t.realized_pnl for t in self.completed_trades)
        total_pnl_pct = (total_pnl / self.allocated_capital) * 100

        return {
            'total_trades': len(self.completed_trades),
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'avg_pnl': total_pnl / len(self.completed_trades),
            'avg_pnl_pct': statistics.mean([t.realized_pnl_pct for t in self.completed_trades]),
            'avg_bars_held': statistics.mean([t.bars_held for t in self.completed_trades]),
            'avg_entries_per_trade': statistics.mean([len(t.entries) for t in self.completed_trades]),
            'avg_max_position_pct': statistics.mean([t.max_position_pct for t in self.completed_trades]),
        }


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_confidence_weighted_test(
    data_file: str,
    risk_mode: str = 'medium',
    allocated_capital: float = 100000.0,
    output_dir: str = ".",
    focus_date: Optional[str] = None
) -> Dict:
    """Run confidence-weighted trading test"""

    print(f"\n{'='*100}")
    print(f"MURPHY V4 CONFIDENCE-WEIGHTED TEST - {CONVICTION_RISK_MODES[risk_mode]['name']}")
    print(f"{'='*100}\n")

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

    print(f"Loaded {len(bars)} bars\n")

    # Generate Murphy signals
    print("Generating Murphy signals...")
    classifier = MurphyClassifier()
    signals = []

    for i in range(len(bars)):
        signal = classifier.classify(
            bars=bars,
            signal_index=i,
            structure_age_bars=50,
            level_price=None
        )
        signals.append(signal)

    print(f"Generated {len(signals)} signals\n")

    # Find focus date
    start_bar = 0
    session_open = None
    session_close = None
    session_high = None
    session_low = None

    if focus_date:
        focus_bars = []
        for i, bar in enumerate(bars):
            if focus_date in bar.timestamp:
                if not focus_bars:
                    start_bar = i
                focus_bars.append(i)

        if focus_bars:
            print(f"Found {len(focus_bars)} bars for {focus_date}")
            session_bars = [bars[i] for i in focus_bars]
            session_open = session_bars[0].open
            session_close = session_bars[-1].close
            session_high = max(b.high for b in session_bars)
            session_low = min(b.low for b in session_bars)

            print(f"Session: ${session_open:.2f} → ${session_close:.2f} (range: {((session_high-session_low)/session_low)*100:.1f}%)\n")

    # Run confidence-weighted trading
    print("Running confidence-weighted trading simulation...")
    trader = ConfidenceWeightedTrader(allocated_capital=allocated_capital, risk_mode=risk_mode)

    trader.execute_trade(
        bars=bars,
        signals=signals,
        start_bar=start_bar,
        session_bias="bullish",
        session_open_price=session_open,
        session_close_price=session_close,
        session_high=session_high,
        session_low=session_low
    )

    # Calculate metrics
    if session_open and session_close and session_high and session_low:
        for trade in trader.completed_trades:
            trade.entry_efficiency = ((session_open - trade.avg_entry_price) / session_open) * 100
            trade.exit_efficiency = ((trade.avg_exit_price - session_close) / session_close) * 100
            session_range = session_high - session_low
            trade_profit_per_share = trade.avg_exit_price - trade.avg_entry_price
            trade.move_captured_pct = (trade_profit_per_share / session_range) * 100 if session_range > 0 else 0

    # Get performance
    perf = trader.get_performance_summary()

    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"{output_dir}/murphy_v4_confidence_{risk_mode}_{timestamp}.txt"

    with open(report_file, 'w') as f:
        f.write("=" * 100 + "\n")
        f.write("MURPHY V4 CONFIDENCE-WEIGHTED TRADING TEST\n")
        f.write("=" * 100 + "\n")
        f.write(f"Risk Mode: {CONVICTION_RISK_MODES[risk_mode]['name']}\n")
        f.write(f"Allocated Capital: ${allocated_capital:,.2f}\n")
        f.write(f"\nPerformance:\n")
        f.write(f"Total Trades: {perf['total_trades']}\n")
        if perf['total_trades'] > 0:
            f.write(f"Total P&L: ${perf['total_pnl']:,.2f} ({perf['total_pnl_pct']:+.2f}%)\n")
            f.write(f"Avg P&L: ${perf['avg_pnl']:,.2f} ({perf['avg_pnl_pct']:+.2f}%)\n")
        f.write("=" * 100 + "\n")

    print(f"\nReport saved to: {report_file}")
    print(f"Result: {perf['total_pnl_pct']:+.2f}%\n")

    return {
        'performance': perf,
        'trades': trader.completed_trades,
        'report_file': report_file
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Murphy V4 Confidence-Weighted Test')
    parser.add_argument('--data', type=str, default='bynd_historical_data.json')
    parser.add_argument('--risk', type=str, default='medium', choices=['low', 'medium', 'high'])
    parser.add_argument('--capital', type=float, default=100000.0)
    parser.add_argument('--output', type=str, default='.')
    parser.add_argument('--date', type=str, default='2025-10-20')
    parser.add_argument('--all', action='store_true', help='Run all risk modes')

    args = parser.parse_args()

    if args.all:
        print("\nRunning all confidence-weighted risk modes...\n")
        for risk_mode in ['low', 'medium', 'high']:
            results = run_confidence_weighted_test(
                data_file=args.data,
                risk_mode=risk_mode,
                allocated_capital=args.capital,
                output_dir=args.output,
                focus_date=args.date
            )
            print(f"{risk_mode.upper()}: {results['performance']['total_pnl_pct']:+.2f}%")
    else:
        results = run_confidence_weighted_test(
            data_file=args.data,
            risk_mode=args.risk,
            allocated_capital=args.capital,
            output_dir=args.output,
            focus_date=args.date
        )


if __name__ == '__main__':
    main()
