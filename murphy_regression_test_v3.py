#!/usr/bin/env python3
"""
Murphy Regression Test V3 - CONVICTION TRADING STRATEGY
========================================================

Tests Murphy as a TACTICAL ADVISOR for high-conviction directional bets.

KEY PARADIGM:
- Scanner picks direction (bullish on gap-ups)
- User allocates capital with conviction ($5k, willing to lose it all)
- Murphy provides TIMING for entries (buy dips at support) and exits (take profits at resistance)

STRATEGY:
- NO STOP LOSSES (dips are buying opportunities)
- Scale in on healthy dips when Murphy confirms support
- Scale out at resistance when Murphy shows weakness
- Hold through consolidation (based on conviction level)

RISK MODES REDEFINED:
- High Risk = High CONVICTION + High PATIENCE (aggressive dip buying, max 150% position)
- Medium Risk = Moderate conviction + balanced approach (max 100% position)
- Low Risk = Conservative + quick profits (max 80% position)

SUCCESS METRICS:
- NOT: Win rate, profit factor, traditional metrics
- MEASURE: % of move captured, entry efficiency, exit timing
"""

import json
import sys
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import statistics

# Add ai-service to path for Murphy imports
sys.path.insert(0, str(Path(__file__).parent / 'ai-service'))

from murphy_classifier_v2 import MurphyClassifier, Bar, MurphySignal


# ============================================================================
# CONVICTION RISK MODES
# ============================================================================

CONVICTION_RISK_MODES = {
    'high': {
        'name': 'HIGH CONVICTION',
        'description': 'Very high conviction, very patient, willing to average down aggressively',
        'initial_entry_pct': 0.20,      # Start with 20% of allocated capital
        'max_position_pct': 1.50,       # Can go to 150% (averaging down!)
        'dip_buying': 'AGGRESSIVE',     # Buy every confirmed dip
        'profit_taking': 'PATIENT',     # Let winners run, hold through chop
        'hold_through_consolidation': True,
        'min_tier': 3,                  # Will take Tier 3 signals if they align
        'dip_threshold_min': 0.03,      # 3% min pullback to consider
        'dip_threshold_max': 0.15,      # 15% max (larger dips OK with conviction)
        'scale_out_first': 0.20,        # Take 20% on first weakness
        'scale_out_second': 0.30,       # Take 30% on clear weakness
        'scale_out_final': 0.50,        # Hold 50% longer
    },
    'medium': {
        'name': 'MEDIUM CONVICTION',
        'description': 'Moderate conviction, balanced approach',
        'initial_entry_pct': 0.30,
        'max_position_pct': 1.00,
        'dip_buying': 'SELECTIVE',
        'profit_taking': 'BALANCED',
        'hold_through_consolidation': False,
        'min_tier': 2,                  # Only Tier 1-2 signals
        'dip_threshold_min': 0.03,
        'dip_threshold_max': 0.10,
        'scale_out_first': 0.30,
        'scale_out_second': 0.40,
        'scale_out_final': 0.30,
    },
    'low': {
        'name': 'LOW CONVICTION',
        'description': 'Conservative, quick profits, limited averaging down',
        'initial_entry_pct': 0.40,
        'max_position_pct': 0.80,
        'dip_buying': 'CONSERVATIVE',
        'profit_taking': 'QUICK',
        'hold_through_consolidation': False,
        'min_tier': 1,                  # ONLY Premium (Tier 1) signals
        'dip_threshold_min': 0.02,
        'dip_threshold_max': 0.08,
        'scale_out_first': 0.40,
        'scale_out_second': 0.40,
        'scale_out_final': 0.20,
    }
}


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ConvictionPosition:
    """Tracks a conviction-based position"""
    symbol: str
    direction: str  # "LONG" (no shorts in conviction mode)
    entries: List[Tuple[int, float, int]] = field(default_factory=list)  # [(bar_idx, price, shares)]
    exits: List[Tuple[int, float, int, str]] = field(default_factory=list)  # [(bar_idx, price, shares, reason)]
    allocated_capital: float = 0.0
    capital_deployed: float = 0.0
    shares_held: int = 0
    avg_entry_price: float = 0.0
    highest_high: float = 0.0  # Track highest price seen
    recent_high_bar: int = 0   # Bar index of recent high

    def add_entry(self, bar_idx: int, price: float, shares: int):
        """Add to position"""
        self.entries.append((bar_idx, price, shares))
        cost = price * shares
        self.capital_deployed += cost
        self.shares_held += shares

        # Recalculate avg entry
        total_cost = sum(p * s for _, p, s in self.entries) - sum(p * s for _, p, s, _ in self.exits)
        if self.shares_held > 0:
            self.avg_entry_price = total_cost / self.shares_held

    def add_exit(self, bar_idx: int, price: float, shares: int, reason: str):
        """Remove from position"""
        self.exits.append((bar_idx, price, shares, reason))
        self.shares_held -= shares

        # Recalculate avg entry for remaining shares
        if self.shares_held > 0:
            total_cost = sum(p * s for _, p, s in self.entries) - sum(p * s for _, p, s, _ in self.exits)
            self.avg_entry_price = total_cost / self.shares_held

    def update_high(self, bar_idx: int, high: float):
        """Update highest high seen"""
        if high > self.highest_high:
            self.highest_high = high
            self.recent_high_bar = bar_idx

    def get_current_value(self, current_price: float) -> float:
        """Get current position value"""
        return self.shares_held * current_price

    def get_unrealized_pnl(self, current_price: float) -> float:
        """Get unrealized P&L"""
        if self.shares_held == 0:
            return 0.0
        return (current_price - self.avg_entry_price) * self.shares_held

    def get_unrealized_pnl_pct(self, current_price: float) -> float:
        """Get unrealized P&L %"""
        if self.shares_held == 0 or self.avg_entry_price == 0:
            return 0.0
        return ((current_price - self.avg_entry_price) / self.avg_entry_price) * 100

    def get_position_pct(self) -> float:
        """Get current position size as % of allocated capital"""
        return (self.capital_deployed / self.allocated_capital) if self.allocated_capital > 0 else 0.0

    def get_realized_pnl(self) -> float:
        """Get realized P&L from exits"""
        total_cost = sum(p * s for _, p, s, _ in self.exits)
        total_proceeds = sum(p * s for _, p, s, _ in self.exits)

        # Calculate cost basis for shares sold
        realized_cost = 0.0
        shares_sold = sum(s for _, _, s, _ in self.exits)

        if shares_sold > 0:
            # Use FIFO accounting
            remaining_to_account = shares_sold
            for _, entry_price, entry_shares in self.entries:
                if remaining_to_account <= 0:
                    break
                shares_from_this_entry = min(remaining_to_account, entry_shares)
                realized_cost += entry_price * shares_from_this_entry
                remaining_to_account -= shares_from_this_entry

        return total_proceeds - realized_cost


@dataclass
class ConvictionTrade:
    """Summary of a completed conviction trade"""
    symbol: str
    entry_bar: int
    exit_bar: int
    bars_held: int

    entries: List[Tuple[int, float, int]]
    exits: List[Tuple[int, float, int, str]]

    avg_entry_price: float
    avg_exit_price: float

    total_shares: int
    allocated_capital: float
    capital_deployed: float
    max_position_pct: float

    realized_pnl: float
    realized_pnl_pct: float

    exit_reason: str

    # Conviction-specific metrics
    move_captured_pct: float  # % of total move captured
    entry_efficiency: float   # How good was avg entry vs open
    exit_efficiency: float    # How good was avg exit vs close


# ============================================================================
# CONVICTION TRADER
# ============================================================================

class ConvictionTrader:
    """
    Conviction-based trader that uses Murphy for tactical timing.

    Key principles:
    - Scanner already decided direction (BULLISH)
    - Allocated capital with conviction (willing to lose it all)
    - Murphy helps with WHEN to add (dips) and WHEN to exit (weakness)
    - NO STOP LOSSES - dips are buying opportunities!
    """

    def __init__(self, allocated_capital: float, risk_mode: str = 'medium'):
        self.allocated_capital = allocated_capital
        self.risk_mode = risk_mode
        self.config = CONVICTION_RISK_MODES[risk_mode]

        self.position: Optional[ConvictionPosition] = None
        self.completed_trades: List[ConvictionTrade] = []

        # Price tracking for dip detection
        self.recent_bars: List[Bar] = []
        self.lookback = 20

    def is_healthy_dip(self, current_bar: Bar, bar_index: int) -> Tuple[bool, float]:
        """
        Detect healthy pullback from recent high.

        Returns: (is_dip, pullback_pct)
        """
        if not self.position:
            return False, 0.0

        # Need position to have established a high
        if self.position.highest_high == 0:
            return False, 0.0

        current_price = current_bar.close
        pullback_pct = (self.position.highest_high - current_price) / self.position.highest_high

        # Check if pullback is in healthy range
        if pullback_pct < self.config['dip_threshold_min']:
            return False, pullback_pct

        if pullback_pct > self.config['dip_threshold_max']:
            # Too big of a dip - might be breakdown
            return False, pullback_pct

        # Check volume - should NOT be spiking red (panic selling)
        if len(self.recent_bars) >= 5:
            avg_volume = statistics.mean([b.volume for b in self.recent_bars[-5:]])
            if current_bar.volume > avg_volume * 2.0:
                # High volume on red bar = panic, not healthy dip
                if current_bar.close < current_bar.open:
                    return False, pullback_pct

        return True, pullback_pct

    def murphy_confirms_support(self, signal: MurphySignal, current_bar: Bar) -> bool:
        """
        Check if Murphy confirms this is a good support level to buy.

        Bullish confirmations:
        - Liquidity sweep (stop hunt at low, bouncing)
        - Bullish rejection (wick rejection at support)
        - Bullish pattern (three soldiers)
        - Near BoS/CHoCH level with bullish signal
        """
        if signal.direction != "↑":
            return False

        # Premium signals (Tier 1) are strong confirmations
        if signal.stars >= 4 or signal.grade in ['A', 'A+', 'A-']:
            if signal.rejection_type == 'bullish_rejection':
                return True
            if signal.pattern in ['three_soldiers', 'morning_star']:
                return True

        # Liquidity sweep is a strong bullish sign at dips
        if signal.has_liquidity_sweep:
            return True

        # Strong signals (Tier 2) with structure
        if signal.grade in ['B+', 'B', 'A-']:
            if signal.has_bos or signal.has_choch:
                return True

        return False

    def murphy_shows_weakness(self, signal: MurphySignal, current_bar: Bar, bar_index: int) -> Tuple[bool, str]:
        """
        Check if Murphy shows weakness at resistance.

        Bearish signals:
        - Bearish rejection at resistance
        - Neutral signal (momentum fading)
        - Bearish signal (reversal warning)

        Returns: (shows_weakness, reason)
        """
        if not self.position:
            return False, ""

        # Check if at/near resistance (approaching previous high)
        current_price = current_bar.close
        resistance_threshold = self.position.highest_high * 0.98  # Within 2% of high

        at_resistance = current_price >= resistance_threshold

        # Bearish rejection at resistance
        if signal.rejection_type == 'bearish_rejection' and at_resistance:
            return True, "bearish_rejection_at_resistance"

        # Neutral signal at resistance
        if signal.direction == "−" and at_resistance:
            return True, "neutral_at_resistance"

        # Strong bearish signal
        if signal.direction == "↓":
            if signal.stars >= 3 or signal.grade in ['A', 'A+', 'A-', 'B+']:
                return True, "strong_bearish_signal"

        return False, ""

    def momentum_fading(self, current_bar: Bar, bar_index: int) -> Tuple[bool, str]:
        """
        Detect if momentum is fading (exit signal).

        Signs:
        - Volume declining for 3+ bars
        - Consolidating sideways for 5+ bars
        - Murphy showing neutral or weak opposing signals

        Returns: (is_fading, reason)
        """
        if len(self.recent_bars) < 10:
            return False, ""

        # Volume declining
        recent_5_bars = self.recent_bars[-5:]
        volumes = [b.volume for b in recent_5_bars]
        if len(volumes) >= 3:
            if volumes[-1] < volumes[-2] < volumes[-3]:
                avg_volume = statistics.mean([b.volume for b in self.recent_bars[-20:]])
                if volumes[-1] < avg_volume * 0.6:
                    return True, "volume_declining"

        # Consolidation detection
        recent_10_bars = self.recent_bars[-10:]
        highs = [b.high for b in recent_10_bars]
        lows = [b.low for b in recent_10_bars]
        range_pct = (max(highs) - min(lows)) / min(lows)

        if range_pct < 0.02:  # Less than 2% range over 10 bars
            return True, "consolidating"

        return False, ""

    def breakout_confirmed(self, signal: MurphySignal, current_bar: Bar, bar_index: int) -> bool:
        """
        Check if we're seeing a confirmed breakout (add remaining capital).

        Confirmations:
        - Price breaking above recent resistance
        - Volume spiking (1.5x avg)
        - Murphy bullish (Tier 1-2)
        """
        if not self.position:
            return False

        if len(self.recent_bars) < 20:
            return False

        # Check for new high
        recent_highs = [b.high for b in self.recent_bars[-20:]]
        current_high = current_bar.high

        if current_high <= max(recent_highs):
            return False

        # Check volume
        avg_volume = statistics.mean([b.volume for b in self.recent_bars[-20:]])
        if current_bar.volume < avg_volume * 1.5:
            return False

        # Check Murphy
        if signal.direction != "↑":
            return False

        if signal.stars < 3:
            return False

        return True

    def check_time_based_exit(self, bar_index: int, total_bars: int) -> bool:
        """
        Check if we should exit based on time (end of session).
        """
        # If in last 5% of bars, consider exiting
        if bar_index >= total_bars * 0.95:
            return True

        return False

    def should_enter_initial(self, signal: MurphySignal, current_bar: Bar) -> bool:
        """
        Decide if we should make initial entry.

        Entry conditions:
        - Murphy bullish (↑)
        - Signal meets minimum tier requirement
        - Not a skip signal
        """
        # Check tier requirement
        tier = self.classify_signal_tier(signal)
        if tier > self.config['min_tier']:
            return False

        # Must be bullish
        if signal.direction != "↑":
            return False

        return True

    def classify_signal_tier(self, signal: MurphySignal) -> int:
        """
        Classify signal into tiers (1=Premium, 2=Strong, 3=Standard, 4=Skip).
        """
        # Tier 1: Premium signals with V2 features + strong fundamentals
        if signal.rejection_type and signal.pattern:
            return 1
        if signal.rejection_type and signal.stars >= 4:
            return 1
        if signal.pattern and signal.grade in ['A', 'A+']:
            return 1

        # Tier 2: Strong signals with at least one V2 feature
        if signal.rejection_type or signal.pattern or signal.has_liquidity_sweep:
            if signal.stars >= 3 or signal.grade in ['B+', 'A-', 'B']:
                return 2

        # Tier 3: Standard signals
        if signal.stars >= 2 or signal.grade in ['C+', 'B-']:
            return 3

        # Tier 4: Skip
        return 4

    def execute_trade(
        self,
        bars: List[Bar],
        signals: List[MurphySignal],
        start_bar: int = 0,
        session_open_price: float = None,
        session_close_price: float = None,
        session_high: float = None,
        session_low: float = None
    ) -> None:
        """
        Execute conviction trading strategy on the provided bars.

        Args:
            bars: List of price bars
            signals: List of Murphy signals (one per bar)
            start_bar: Bar index to start trading
            session_open_price: Session open price for efficiency metrics
            session_close_price: Session close price for efficiency metrics
            session_high: Session high for move capture metrics
            session_low: Session low for move capture metrics
        """
        self.position = None
        self.recent_bars = []

        for i in range(start_bar, len(bars)):
            bar = bars[i]
            signal = signals[i] if i < len(signals) else None

            # Update recent bars
            self.recent_bars.append(bar)
            if len(self.recent_bars) > self.lookback:
                self.recent_bars.pop(0)

            # Update position high
            if self.position:
                self.position.update_high(i, bar.high)

            # Check for initial entry
            if not self.position and signal:
                if self.should_enter_initial(signal, bar):
                    self._enter_initial(i, bar, signal)

            # If we have a position, check for adds or exits
            if self.position and signal:
                # Check scale in opportunities
                self._check_scale_in(i, bar, signal)

                # Check scale out opportunities
                self._check_scale_out(i, bar, signal)

                # Check time-based exit
                if self.check_time_based_exit(i, len(bars)):
                    self._exit_all(i, bar, "end_of_session")

        # Close any remaining position at end
        if self.position and len(bars) > 0:
            self._exit_all(len(bars) - 1, bars[-1], "end_of_data")

    def _enter_initial(self, bar_index: int, bar: Bar, signal: MurphySignal):
        """Make initial entry (20-40% of allocated capital)"""
        entry_pct = self.config['initial_entry_pct']
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

    def _check_scale_in(self, bar_index: int, bar: Bar, signal: MurphySignal):
        """Check if we should add to position on a dip"""
        if not self.position:
            return

        # Check if we're at max position
        position_pct = self.position.get_position_pct()
        if position_pct >= self.config['max_position_pct']:
            return

        # Check for healthy dip
        is_dip, pullback_pct = self.is_healthy_dip(bar, bar_index)
        if not is_dip:
            return

        # Check Murphy confirmation
        if not self.murphy_confirms_support(signal, bar):
            return

        # Determine add size based on risk mode and pullback size
        remaining_capital = self.allocated_capital * self.config['max_position_pct'] - self.position.capital_deployed

        if self.config['dip_buying'] == 'AGGRESSIVE':
            # Add 30-40% of remaining
            add_pct = 0.35 if pullback_pct > 0.05 else 0.25
        elif self.config['dip_buying'] == 'SELECTIVE':
            # Add 20-30% of remaining
            add_pct = 0.25 if pullback_pct > 0.05 else 0.20
        else:  # CONSERVATIVE
            # Add 15-20% of remaining
            add_pct = 0.20 if pullback_pct > 0.05 else 0.15

        add_capital = remaining_capital * add_pct
        shares = int(add_capital / bar.close)

        if shares > 0:
            self.position.add_entry(bar_index, bar.close, shares)

    def _check_scale_out(self, bar_index: int, bar: Bar, signal: MurphySignal):
        """Check if we should take profits"""
        if not self.position or self.position.shares_held == 0:
            return

        # Check for weakness at resistance
        shows_weakness, reason = self.murphy_shows_weakness(signal, bar, bar_index)

        if shows_weakness:
            # First scale out
            if reason in ['bearish_rejection_at_resistance', 'neutral_at_resistance']:
                shares_to_sell = int(self.position.shares_held * self.config['scale_out_first'])
                if shares_to_sell > 0:
                    self.position.add_exit(bar_index, bar.close, shares_to_sell, reason)
                return

            # Second scale out (stronger weakness)
            if reason == 'strong_bearish_signal':
                shares_to_sell = int(self.position.shares_held * self.config['scale_out_second'])
                if shares_to_sell > 0:
                    self.position.add_exit(bar_index, bar.close, shares_to_sell, reason)
                return

        # Check for momentum fading
        is_fading, fade_reason = self.momentum_fading(bar, bar_index)
        if is_fading:
            # Exit based on profit taking style
            if self.config['profit_taking'] == 'QUICK':
                # Exit most of position
                shares_to_sell = int(self.position.shares_held * 0.70)
            elif self.config['profit_taking'] == 'BALANCED':
                shares_to_sell = int(self.position.shares_held * 0.50)
            else:  # PATIENT
                # Only exit if no consolidation tolerance
                if not self.config['hold_through_consolidation']:
                    shares_to_sell = int(self.position.shares_held * 0.30)
                else:
                    return  # Hold through chop

            if shares_to_sell > 0:
                self.position.add_exit(bar_index, bar.close, shares_to_sell, fade_reason)

    def _exit_all(self, bar_index: int, bar: Bar, reason: str):
        """Exit entire position"""
        if not self.position or self.position.shares_held == 0:
            return

        shares_to_sell = self.position.shares_held
        self.position.add_exit(bar_index, bar.close, shares_to_sell, reason)

        # Create completed trade record
        if len(self.position.entries) > 0 and len(self.position.exits) > 0:
            trade = self._create_trade_record()
            self.completed_trades.append(trade)

        self.position = None

    def _create_trade_record(self) -> ConvictionTrade:
        """Create a completed trade record from current position"""
        if not self.position:
            return None

        # Calculate averages
        total_shares_entered = sum(s for _, _, s in self.position.entries)
        total_shares_exited = sum(s for _, _, s, _ in self.position.exits)

        total_entry_cost = sum(p * s for _, p, s in self.position.entries)
        avg_entry = total_entry_cost / total_shares_entered if total_shares_entered > 0 else 0

        total_exit_proceeds = sum(p * s for _, p, s, _ in self.position.exits)
        avg_exit = total_exit_proceeds / total_shares_exited if total_shares_exited > 0 else 0

        # P&L
        realized_pnl = total_exit_proceeds - (avg_entry * total_shares_exited)
        realized_pnl_pct = (realized_pnl / (avg_entry * total_shares_exited)) * 100 if total_shares_exited > 0 else 0

        # Max position size
        max_deployed = max(
            sum(p * s for _, p, s in self.position.entries[:i+1])
            for i in range(len(self.position.entries))
        )
        max_position_pct = (max_deployed / self.position.allocated_capital) * 100

        # Exit reason (last exit)
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
            move_captured_pct=0.0,  # Will be calculated by test runner
            entry_efficiency=0.0,
            exit_efficiency=0.0
        )

    def get_performance_summary(self) -> Dict:
        """Get performance summary for all completed trades"""
        if not self.completed_trades:
            return {
                'total_trades': 0,
                'total_pnl': 0.0,
                'total_pnl_pct': 0.0,
                'avg_pnl': 0.0,
                'avg_pnl_pct': 0.0,
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

def run_conviction_test(
    data_file: str,
    risk_mode: str = 'medium',
    allocated_capital: float = 100000.0,
    output_dir: str = ".",
    focus_date: Optional[str] = None
) -> Dict:
    """
    Run conviction trading test on historical data.

    Args:
        data_file: Path to JSON file with bars and signals
        risk_mode: 'high', 'medium', or 'low'
        allocated_capital: Amount allocated to this conviction bet
        output_dir: Directory for output files
        focus_date: Optional date to focus on (e.g., "2025-10-20" for gap up day)

    Returns:
        Dict with test results
    """
    print(f"\n{'='*100}")
    print(f"MURPHY CONVICTION TRADING TEST V3 - {CONVICTION_RISK_MODES[risk_mode]['name']}")
    print(f"{'='*100}\n")

    # Load data
    print(f"Loading data from: {data_file}")
    with open(data_file, 'r') as f:
        data = json.load(f)

    # Convert to Bar objects
    bars = []
    # Handle both dict with 'bars' key and direct array
    bars_data = data['bars'] if isinstance(data, dict) and 'bars' in data else data

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

    print(f"Loaded {len(bars)} bars")
    print(f"Date range: {bars[0].timestamp} to {bars[-1].timestamp}\n")

    # Generate Murphy signals
    print("Generating Murphy signals...")
    classifier = MurphyClassifier()
    signals = []

    for i in range(len(bars)):
        signal = classifier.classify(
            bars=bars,
            signal_index=i,
            structure_age_bars=50,
            level_price=None  # Auto-detect
        )
        signals.append(signal)

    print(f"Generated {len(signals)} signals\n")

    # Focus on specific date if requested
    start_bar = 0
    session_open = None
    session_close = None
    session_high = None
    session_low = None

    if focus_date:
        print(f"Focusing on date: {focus_date}")
        # Find bars for this date
        focus_bars = []
        for i, bar in enumerate(bars):
            if focus_date in bar.timestamp:
                if not focus_bars:
                    start_bar = i
                focus_bars.append(i)

        if focus_bars:
            print(f"Found {len(focus_bars)} bars for {focus_date}")
            print(f"Starting at bar {start_bar} ({bars[start_bar].timestamp})")

            # Get session metrics
            session_bars = [bars[i] for i in focus_bars]
            session_open = session_bars[0].open
            session_close = session_bars[-1].close
            session_high = max(b.high for b in session_bars)
            session_low = min(b.low for b in session_bars)

            print(f"Session open: ${session_open:.2f}")
            print(f"Session close: ${session_close:.2f}")
            print(f"Session high: ${session_high:.2f}")
            print(f"Session low: ${session_low:.2f}")
            print(f"Session range: {((session_high - session_low) / session_low * 100):.2f}%\n")
        else:
            print(f"WARNING: No bars found for {focus_date}, using all data\n")

    # Run conviction trading simulation
    print("Running conviction trading simulation...")
    trader = ConvictionTrader(allocated_capital=allocated_capital, risk_mode=risk_mode)

    trader.execute_trade(
        bars=bars,
        signals=signals,
        start_bar=start_bar,
        session_open_price=session_open,
        session_close_price=session_close,
        session_high=session_high,
        session_low=session_low
    )

    # Calculate efficiency metrics for trades
    if session_open and session_close and session_high and session_low:
        for trade in trader.completed_trades:
            # Entry efficiency: How good was avg entry vs session open?
            trade.entry_efficiency = ((session_open - trade.avg_entry_price) / session_open) * 100

            # Exit efficiency: How good was avg exit vs session close?
            trade.exit_efficiency = ((trade.avg_exit_price - session_close) / session_close) * 100

            # Move captured: What % of the session range did we capture?
            session_range = session_high - session_low
            trade_profit_per_share = trade.avg_exit_price - trade.avg_entry_price
            trade.move_captured_pct = (trade_profit_per_share / session_range) * 100 if session_range > 0 else 0

    # Get performance summary
    perf = trader.get_performance_summary()

    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"{output_dir}/murphy_v3_conviction_{risk_mode}_{timestamp}.txt"

    _generate_conviction_report(
        report_file=report_file,
        bars=bars,
        signals=signals,
        trader=trader,
        performance=perf,
        risk_mode=risk_mode,
        focus_date=focus_date,
        session_metrics={
            'open': session_open,
            'close': session_close,
            'high': session_high,
            'low': session_low
        }
    )

    print(f"\n{'='*100}")
    print(f"TEST COMPLETE")
    print(f"{'='*100}")
    print(f"Report saved to: {report_file}\n")

    return {
        'performance': perf,
        'trades': trader.completed_trades,
        'report_file': report_file
    }


def _generate_conviction_report(
    report_file: str,
    bars: List[Bar],
    signals: List[MurphySignal],
    trader: ConvictionTrader,
    performance: Dict,
    risk_mode: str,
    focus_date: Optional[str],
    session_metrics: Dict
):
    """Generate detailed conviction trading report"""

    with open(report_file, 'w') as f:
        f.write("=" * 100 + "\n")
        f.write("MURPHY CONVICTION TRADING TEST V3\n")
        f.write("=" * 100 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Risk Mode: {CONVICTION_RISK_MODES[risk_mode]['name']}\n")
        f.write(f"Allocated Capital: ${trader.allocated_capital:,.2f}\n")

        if focus_date:
            f.write(f"Focus Date: {focus_date}\n")

        f.write(f"\nDataset: {len(bars)} bars ({bars[0].timestamp} to {bars[-1].timestamp})\n")

        # Risk configuration
        f.write("\n" + "-" * 100 + "\n")
        f.write("CONVICTION RISK CONFIGURATION\n")
        f.write("-" * 100 + "\n")
        config = trader.config
        f.write(f"Description:             {config['description']}\n")
        f.write(f"Initial entry:           {config['initial_entry_pct']*100:.0f}% of allocated capital\n")
        f.write(f"Max position:            {config['max_position_pct']*100:.0f}% of allocated capital\n")
        f.write(f"Dip buying:              {config['dip_buying']}\n")
        f.write(f"Profit taking:           {config['profit_taking']}\n")
        f.write(f"Hold through chop:       {'Yes' if config['hold_through_consolidation'] else 'No'}\n")
        f.write(f"Min signal tier:         {config['min_tier']}\n")
        f.write(f"Dip threshold:           {config['dip_threshold_min']*100:.0f}%-{config['dip_threshold_max']*100:.0f}%\n")
        f.write(f"Stop losses:             NONE (conviction mode)\n")

        # Session metrics (if available)
        if session_metrics['open'] is not None:
            f.write("\n" + "-" * 100 + "\n")
            f.write("SESSION METRICS\n")
            f.write("-" * 100 + "\n")
            f.write(f"Open:                    ${session_metrics['open']:.2f}\n")
            f.write(f"Close:                   ${session_metrics['close']:.2f}\n")
            f.write(f"High:                    ${session_metrics['high']:.2f}\n")
            f.write(f"Low:                     ${session_metrics['low']:.2f}\n")

            session_range = session_metrics['high'] - session_metrics['low']
            session_move = ((session_metrics['close'] - session_metrics['open']) / session_metrics['open']) * 100
            f.write(f"Range:                   {session_range:.2f} ({(session_range/session_metrics['low'])*100:.2f}%)\n")
            f.write(f"Move (open to close):    {session_move:+.2f}%\n")

        # Signal summary
        f.write("\n" + "-" * 100 + "\n")
        f.write("MURPHY SIGNAL SUMMARY\n")
        f.write("-" * 100 + "\n")

        # Count tiers
        tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for sig in signals:
            tier = trader.classify_signal_tier(sig)
            tier_counts[tier] += 1

        f.write(f"Total signals:           {len(signals)}\n")
        f.write(f"  Tier 1 (Premium):      {tier_counts[1]}\n")
        f.write(f"  Tier 2 (Strong):       {tier_counts[2]}\n")
        f.write(f"  Tier 3 (Standard):     {tier_counts[3]}\n")
        f.write(f"  Tier 4 (Skip):         {tier_counts[4]}\n")

        # Performance
        f.write("\n" + "-" * 100 + "\n")
        f.write("CONVICTION TRADING PERFORMANCE\n")
        f.write("-" * 100 + "\n")
        f.write(f"Total trades:            {performance['total_trades']}\n")

        if performance['total_trades'] > 0:
            f.write(f"\nTotal P&L:               ${performance['total_pnl']:,.2f} ({performance['total_pnl_pct']:+.2f}%)\n")
            f.write(f"Avg P&L per trade:       ${performance['avg_pnl']:,.2f} ({performance['avg_pnl_pct']:+.2f}%)\n")
            f.write(f"Avg bars held:           {performance['avg_bars_held']:.1f}\n")
            f.write(f"Avg entries per trade:   {performance['avg_entries_per_trade']:.1f}\n")
            f.write(f"Avg max position:        {performance['avg_max_position_pct']:.1f}% of allocated\n")

            # Conviction-specific metrics
            if session_metrics['open'] is not None and trader.completed_trades:
                avg_entry_eff = statistics.mean([t.entry_efficiency for t in trader.completed_trades])
                avg_exit_eff = statistics.mean([t.exit_efficiency for t in trader.completed_trades])
                avg_move_captured = statistics.mean([t.move_captured_pct for t in trader.completed_trades])

                f.write(f"\nCONVICTION EFFICIENCY METRICS:\n")
                f.write(f"Avg entry efficiency:    {avg_entry_eff:+.2f}% vs session open\n")
                f.write(f"Avg exit efficiency:     {avg_exit_eff:+.2f}% vs session close\n")
                f.write(f"Avg move captured:       {avg_move_captured:.1f}% of session range\n")

        # Trade details
        if trader.completed_trades:
            f.write("\n" + "-" * 100 + "\n")
            f.write("TRADE DETAILS\n")
            f.write("-" * 100 + "\n")

            for idx, trade in enumerate(trader.completed_trades, 1):
                f.write(f"\nTrade #{idx}:\n")
                f.write(f"  Entry bar: {trade.entry_bar} ({bars[trade.entry_bar].timestamp})\n")
                f.write(f"  Exit bar:  {trade.exit_bar} ({bars[trade.exit_bar].timestamp})\n")
                f.write(f"  Bars held: {trade.bars_held}\n")
                f.write(f"  \n")
                f.write(f"  Entries ({len(trade.entries)}):\n")
                for entry_bar, entry_price, entry_shares in trade.entries:
                    f.write(f"    Bar {entry_bar}: {entry_shares} shares @ ${entry_price:.2f}\n")
                f.write(f"  \n")
                f.write(f"  Exits ({len(trade.exits)}):\n")
                for exit_bar, exit_price, exit_shares, reason in trade.exits:
                    f.write(f"    Bar {exit_bar}: {exit_shares} shares @ ${exit_price:.2f} ({reason})\n")
                f.write(f"  \n")
                f.write(f"  Avg entry:        ${trade.avg_entry_price:.2f}\n")
                f.write(f"  Avg exit:         ${trade.avg_exit_price:.2f}\n")
                f.write(f"  Total shares:     {trade.total_shares}\n")
                f.write(f"  Max position:     {trade.max_position_pct:.1f}% of allocated\n")
                f.write(f"  P&L:              ${trade.realized_pnl:,.2f} ({trade.realized_pnl_pct:+.2f}%)\n")

                if session_metrics['open'] is not None:
                    f.write(f"  \n")
                    f.write(f"  Entry efficiency: {trade.entry_efficiency:+.2f}% vs session open\n")
                    f.write(f"  Exit efficiency:  {trade.exit_efficiency:+.2f}% vs session close\n")
                    f.write(f"  Move captured:    {trade.move_captured_pct:.1f}% of session range\n")

        f.write("\n" + "=" * 100 + "\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Murphy Conviction Trading Test V3')
    parser.add_argument('--data', type=str, default='bynd_historical_data.json',
                        help='Path to historical data JSON file')
    parser.add_argument('--risk', type=str, default='medium', choices=['low', 'medium', 'high'],
                        help='Risk mode (conviction level)')
    parser.add_argument('--capital', type=float, default=100000.0,
                        help='Allocated capital for conviction bet')
    parser.add_argument('--output', type=str, default='.',
                        help='Output directory for reports')
    parser.add_argument('--date', type=str, default=None,
                        help='Focus on specific date (e.g., 2025-10-20)')
    parser.add_argument('--all', action='store_true',
                        help='Run all three risk modes')

    args = parser.parse_args()

    if args.all:
        print("\nRunning all three conviction risk modes...\n")
        for risk_mode in ['low', 'medium', 'high']:
            results = run_conviction_test(
                data_file=args.data,
                risk_mode=risk_mode,
                allocated_capital=args.capital,
                output_dir=args.output,
                focus_date=args.date
            )
            print(f"\n{risk_mode.upper()} mode: {results['performance']['total_pnl_pct']:+.2f}%")
    else:
        results = run_conviction_test(
            data_file=args.data,
            risk_mode=args.risk,
            allocated_capital=args.capital,
            output_dir=args.output,
            focus_date=args.date
        )


if __name__ == '__main__':
    main()
