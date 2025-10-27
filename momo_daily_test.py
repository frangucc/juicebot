#!/usr/bin/env python3
"""
Momo Advanced - Daily Segmented Test
=====================================

Tests Momo Advanced on full dataset, segmented by trading day.

Key Features:
- Daily P&L breakdown
- Front-side vs back-side detection
- Cooling period detection (gap downs, red momentum)
- Trade less when cooling
- Focus on momentum days

Cooling Indicators:
- Gap down from yesterday
- Multiple red timeframes
- After big run (exhaustion)
- Volume declining
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict
import statistics

sys.path.insert(0, str(Path(__file__).parent))
from murphy_classifier_v2 import Bar
from momo_advanced import MomoAdvanced, MomoAdvancedSignal


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class DailySession:
    """A single trading day"""
    date: str
    bars: List[Bar]
    bar_indices: List[int]

    # Session metrics
    open_price: float = 0.0
    close_price: float = 0.0
    high: float = 0.0
    low: float = 0.0

    # Performance
    session_move_pct: float = 0.0
    session_range_pct: float = 0.0

    # Cooling indicators
    gap_from_yesterday: Optional[float] = None
    is_cooling: bool = False
    cooling_reasons: List[str] = field(default_factory=list)


@dataclass
class Trade:
    """A single trade"""
    entry_bar: int
    entry_time: str
    entry_price: float
    entry_signal: MomoAdvancedSignal

    exit_bar: Optional[int] = None
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""

    bars_held: int = 0
    pnl_pct: float = 0.0
    pnl_dollars: float = 0.0


@dataclass
class DailyPerformance:
    """Performance for one day"""
    date: str
    trades: List[Trade]

    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    win_rate: float = 0.0

    # Session info
    was_cooling: bool = False
    gap_from_yesterday: float = 0.0
    session_move: float = 0.0


# ============================================================================
# DAILY SEGMENTER
# ============================================================================

class DailySegmenter:
    """Segment bars into trading days"""

    def segment(self, bars: List[Bar]) -> List[DailySession]:
        """Group bars by trading day"""

        sessions_by_date: Dict[str, List[int]] = defaultdict(list)

        # Group by date
        for i, bar in enumerate(bars):
            date = self._extract_date(bar.timestamp)
            sessions_by_date[date].append(i)

        # Create session objects
        sessions = []
        prev_close = None

        for date in sorted(sessions_by_date.keys()):
            indices = sessions_by_date[date]
            session_bars = [bars[i] for i in indices]

            session = DailySession(
                date=date,
                bars=session_bars,
                bar_indices=indices
            )

            # Calculate session metrics
            session.open_price = session_bars[0].open
            session.close_price = session_bars[-1].close
            session.high = max(b.high for b in session_bars)
            session.low = min(b.low for b in session_bars)

            session.session_move_pct = ((session.close_price - session.open_price) /
                                       session.open_price) * 100
            session.session_range_pct = ((session.high - session.low) / session.low) * 100

            # Gap from yesterday
            if prev_close is not None:
                session.gap_from_yesterday = ((session.open_price - prev_close) /
                                             prev_close) * 100

            prev_close = session.close_price
            sessions.append(session)

        return sessions

    def _extract_date(self, timestamp: str) -> str:
        """Extract YYYY-MM-DD from timestamp"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except:
            return timestamp[:10]


# ============================================================================
# COOLING DETECTOR
# ============================================================================

class CoolingDetector:
    """Detect when momentum is cooling (trade less)"""

    def is_cooling(self, session: DailySession, signals: List[MomoAdvancedSignal]) -> tuple[bool, List[str]]:
        """
        Detect if this day is cooling off (back-side of move).

        Returns: (is_cooling, reasons)
        """
        reasons = []

        # 1. Gap down
        if session.gap_from_yesterday is not None:
            if session.gap_from_yesterday < -3:
                reasons.append(f"Gap down {session.gap_from_yesterday:.1f}%")

        # 2. Majority red timeframes
        if signals:
            bearish_signals = sum(1 for s in signals if s.direction == '↓')
            bearish_pct = bearish_signals / len(signals)

            if bearish_pct > 0.60:
                reasons.append(f"{bearish_pct:.0%} bearish signals")

        # 3. Low confidence throughout day
        if signals:
            avg_confidence = statistics.mean([s.confidence for s in signals])
            if avg_confidence < 0.40:
                reasons.append(f"Low avg confidence {avg_confidence:.0%}")

        # 4. Declining session (close < open by >5%)
        if session.session_move_pct < -5:
            reasons.append(f"Session down {session.session_move_pct:.1f}%")

        is_cooling = len(reasons) >= 2  # Need 2+ cooling indicators

        return is_cooling, reasons


# ============================================================================
# SIMPLE TRADER
# ============================================================================

class SimpleMomoTrader:
    """
    Simple trading logic using Momo Advanced signals.

    Strategy:
    - Enter on STRONG_BUY or BUY signals
    - Exit on confidence drop or extension
    - Reduce size when cooling
    - Focus on front-side momentum
    """

    def __init__(self, starting_capital: float = 10000):
        self.starting_capital = starting_capital
        self.capital = starting_capital
        self.position: Optional[Trade] = None
        self.trades: List[Trade] = []

    def trade_day(
        self,
        bars: List[Bar],
        bar_indices: List[int],
        signals: List[MomoAdvancedSignal],
        is_cooling: bool
    ):
        """Trade through one day"""

        for i, (bar_idx, signal) in enumerate(zip(bar_indices, signals)):
            bar = bars[bar_idx]

            # Check for entry
            if not self.position:
                should_enter = self._should_enter(signal, is_cooling)
                if should_enter:
                    self._enter(bar_idx, bar, signal, is_cooling)

            # Check for exit
            else:
                should_exit, reason = self._should_exit(signal, bars, bar_idx, is_cooling)
                if should_exit:
                    self._exit(bar_idx, bar, reason)

        # Close any position at end of day
        if self.position and bar_indices:
            last_bar_idx = bar_indices[-1]
            self._exit(last_bar_idx, bars[last_bar_idx], "end_of_day")

    def _should_enter(self, signal: MomoAdvancedSignal, is_cooling: bool) -> bool:
        """Decide if should enter"""

        # Don't trade when cooling
        if is_cooling:
            return False

        # Only enter on strong signals
        if signal.action not in ["STRONG_BUY", "BUY"]:
            return False

        # Prefer value zones
        if signal.vwap_context.zone in ["VALUE", "DEEP_VALUE", "FAIR"]:
            return signal.confidence >= 0.60

        return False

    def _should_exit(
        self,
        signal: MomoAdvancedSignal,
        bars: List[Bar],
        current_bar_idx: int,
        is_cooling: bool
    ) -> tuple[bool, str]:
        """Decide if should exit"""

        if not self.position:
            return False, ""

        # Calculate current P&L
        current_price = bars[current_bar_idx].close
        pnl_pct = ((current_price - self.position.entry_price) /
                   self.position.entry_price) * 100

        # Exit on cooling
        if is_cooling and pnl_pct > 0:
            return True, "cooling_take_profits"

        # Exit on extreme extension
        if signal.vwap_context.zone == "EXTREME":
            return True, "extreme_extension"

        # Exit on confidence drop
        if signal.confidence < 0.35:
            return True, "confidence_drop"

        # Stop loss (only if cooling)
        if is_cooling and pnl_pct < -5:
            return True, "cooling_stop_loss"

        # Take profits on big winners
        if pnl_pct > 15:
            return True, "take_profits_15pct"

        # Hold otherwise
        return False, ""

    def _enter(self, bar_idx: int, bar: Bar, signal: MomoAdvancedSignal, is_cooling: bool):
        """Enter position"""

        # Size based on confidence and cooling
        base_size = self.capital * 0.30  # 30% of capital

        if is_cooling:
            base_size *= 0.5  # Half size when cooling

        size = base_size * signal.confidence

        self.position = Trade(
            entry_bar=bar_idx,
            entry_time=bar.timestamp,
            entry_price=bar.close,
            entry_signal=signal
        )

        # Use capital
        self.capital -= size

    def _exit(self, bar_idx: int, bar: Bar, reason: str):
        """Exit position"""

        if not self.position:
            return

        self.position.exit_bar = bar_idx
        self.position.exit_time = bar.timestamp
        self.position.exit_price = bar.close
        self.position.exit_reason = reason
        self.position.bars_held = bar_idx - self.position.entry_bar

        # Calculate P&L
        self.position.pnl_pct = ((bar.close - self.position.entry_price) /
                                 self.position.entry_price) * 100

        # Simplified P&L (assume 30% position)
        position_size = self.starting_capital * 0.30
        self.position.pnl_dollars = position_size * (self.position.pnl_pct / 100)

        # Return capital + P&L
        self.capital += position_size + self.position.pnl_dollars

        # Record trade
        self.trades.append(self.position)
        self.position = None

    def get_daily_performance(self, date: str) -> DailyPerformance:
        """Get performance for a specific day"""

        day_trades = [t for t in self.trades
                     if t.entry_time.startswith(date)]

        if not day_trades:
            return DailyPerformance(date, [], 0.0, 0.0, 0.0)

        total_pnl = sum(t.pnl_dollars for t in day_trades)
        total_pnl_pct = (total_pnl / self.starting_capital) * 100

        winners = sum(1 for t in day_trades if t.pnl_pct > 0)
        win_rate = (winners / len(day_trades)) * 100

        return DailyPerformance(
            date=date,
            trades=day_trades,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            win_rate=win_rate
        )


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_daily_test(data_file: str, output_file: str = "momo_daily_results.txt"):
    """Run Momo Advanced test segmented by day"""

    print("=" * 100)
    print("MOMO ADVANCED - DAILY SEGMENTED TEST")
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

    # Segment by day
    print("Segmenting into trading days...")
    segmenter = DailySegmenter()
    sessions = segmenter.segment(bars)
    print(f"Found {len(sessions)} trading days\n")

    # Initialize systems
    momo = MomoAdvanced()
    cooling_detector = CoolingDetector()
    trader = SimpleMomoTrader(starting_capital=10000)

    # Process each day
    print("Processing days...\n")
    print(f"{'Date':<12} {'Gap':<8} {'Range':<8} {'Cooling':<10} {'Trades':<8} {'P&L':<12} {'Capital':<12}")
    print("-" * 100)

    daily_results = []

    for session in sessions:
        # Generate signals for this day
        signals = []
        prev_close = None

        if session.bar_indices[0] > 0:
            prev_close = bars[session.bar_indices[0] - 1].close

        for bar_idx in session.bar_indices:
            signal = momo.classify(bars, bar_idx, yesterday_close=prev_close)
            signals.append(signal)

        # Check if cooling
        is_cooling, cooling_reasons = cooling_detector.is_cooling(session, signals)
        session.is_cooling = is_cooling
        session.cooling_reasons = cooling_reasons

        # Trade this day
        trader.trade_day(bars, session.bar_indices, signals, is_cooling)

        # Get daily performance
        perf = trader.get_daily_performance(session.date)
        perf.was_cooling = is_cooling
        perf.gap_from_yesterday = session.gap_from_yesterday or 0.0
        perf.session_move = session.session_move_pct

        daily_results.append((session, perf))

        # Print row
        cooling_str = "YES" if is_cooling else ""
        gap_str = f"{session.gap_from_yesterday:+.1f}%" if session.gap_from_yesterday else "N/A"

        print(f"{session.date:<12} {gap_str:<8} {session.session_range_pct:>6.1f}%  "
              f"{cooling_str:<10} {len(perf.trades):<8} "
              f"${perf.total_pnl:>+9.2f}  ${trader.capital:>10,.2f}")

    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)

    total_trades = len(trader.trades)
    total_pnl = trader.capital - trader.starting_capital
    total_pnl_pct = (total_pnl / trader.starting_capital) * 100

    winners = sum(1 for t in trader.trades if t.pnl_pct > 0)
    win_rate = (winners / total_trades * 100) if total_trades > 0 else 0

    print(f"\nStarting Capital: ${trader.starting_capital:,.2f}")
    print(f"Ending Capital:   ${trader.capital:,.2f}")
    print(f"Total P&L:        ${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)")
    print(f"\nTotal Trades:     {total_trades}")
    print(f"Win Rate:         {win_rate:.1f}%")
    print(f"Winners:          {winners}")
    print(f"Losers:           {total_trades - winners}")

    if trader.trades:
        avg_win = statistics.mean([t.pnl_pct for t in trader.trades if t.pnl_pct > 0]) if winners > 0 else 0
        avg_loss = statistics.mean([t.pnl_pct for t in trader.trades if t.pnl_pct < 0]) if winners < total_trades else 0

        print(f"\nAvg Winner:       {avg_win:+.2f}%")
        print(f"Avg Loser:        {avg_loss:+.2f}%")

    # Front-side vs back-side analysis
    print("\n" + "-" * 100)
    print("FRONT-SIDE vs BACK-SIDE ANALYSIS")
    print("-" * 100)

    front_side_days = [p for s, p in daily_results if not p.was_cooling]
    back_side_days = [p for s, p in daily_results if p.was_cooling]

    print(f"\nFront-Side Days (momentum): {len(front_side_days)}")
    if front_side_days:
        front_pnl = sum(p.total_pnl for p in front_side_days)
        front_trades = sum(len(p.trades) for p in front_side_days)
        print(f"  Total P&L: ${front_pnl:+,.2f}")
        print(f"  Trades: {front_trades}")
        print(f"  Avg P&L per day: ${front_pnl/len(front_side_days):+.2f}")

    print(f"\nBack-Side Days (cooling): {len(back_side_days)}")
    if back_side_days:
        back_pnl = sum(p.total_pnl for p in back_side_days)
        back_trades = sum(len(p.trades) for p in back_side_days)
        print(f"  Total P&L: ${back_pnl:+,.2f}")
        print(f"  Trades: {back_trades}")
        print(f"  Avg P&L per day: ${back_pnl/len(back_side_days):+.2f}")

    # Best and worst days
    print("\n" + "-" * 100)
    print("BEST & WORST DAYS")
    print("-" * 100)

    sorted_days = sorted(daily_results, key=lambda x: x[1].total_pnl, reverse=True)

    print("\nTop 5 Days:")
    for i, (session, perf) in enumerate(sorted_days[:5], 1):
        print(f"  {i}. {session.date}: ${perf.total_pnl:+.2f} "
              f"({perf.win_rate:.0f}% WR, {len(perf.trades)} trades, "
              f"gap {perf.gap_from_yesterday:+.1f}%)")

    print("\nWorst 5 Days:")
    for i, (session, perf) in enumerate(sorted_days[-5:], 1):
        print(f"  {i}. {session.date}: ${perf.total_pnl:+.2f} "
              f"({perf.win_rate:.0f}% WR, {len(perf.trades)} trades, "
              f"gap {perf.gap_from_yesterday:+.1f}%)")

    print("\n" + "=" * 100)

    # Save detailed report
    with open(output_file, 'w') as f:
        f.write("MOMO ADVANCED - DAILY SEGMENTED TEST RESULTS\n")
        f.write("=" * 100 + "\n\n")
        f.write(f"Total P&L: ${total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)\n")
        f.write(f"Win Rate: {win_rate:.1f}%\n\n")

        f.write("DAILY BREAKDOWN:\n")
        f.write("-" * 100 + "\n")
        for session, perf in daily_results:
            f.write(f"\n{session.date}:\n")
            f.write(f"  Gap: {perf.gap_from_yesterday:+.1f}%\n")
            f.write(f"  Range: {session.session_range_pct:.1f}%\n")
            f.write(f"  Cooling: {'YES' if perf.was_cooling else 'NO'}\n")
            if perf.was_cooling:
                f.write(f"    Reasons: {', '.join(session.cooling_reasons)}\n")
            f.write(f"  Trades: {len(perf.trades)}\n")
            f.write(f"  P&L: ${perf.total_pnl:+.2f}\n")

    print(f"\nDetailed report saved to: {output_file}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Momo Advanced Daily Test')
    parser.add_argument('--data', type=str, default='bynd_historical_data.json')
    parser.add_argument('--output', type=str, default='momo_daily_results.txt')

    args = parser.parse_args()

    run_daily_test(args.data, args.output)
