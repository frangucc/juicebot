#!/usr/bin/env python3
"""
Execution Strategies - Trading Styles Abstraction
=================================================

Separates INDICATOR (what to trade) from EXECUTION (how to trade).

Four Strategy Types:
1. Fast Scalp:    Quick 1-3% moves, tight stops, 5-15 bars
2. Hit & Run:     Medium 5-10% moves, moderate stops, 20-50 bars
3. Accumulation:  Build on dips, scale out on strength, no stops
4. Diamond Hand:  Conviction hold, patient, exit on reversal only

These can be paired with any indicator system:
- Murphy (SMC): Structure-based bidirectional trading
- Momo (Momentum): Trend-following unidirectional trading
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from abc import ABC, abstractmethod


# ============================================================================
# BASE EXECUTION STRATEGY
# ============================================================================

@dataclass
class StrategyConfig:
    """Configuration for an execution strategy"""
    name: str
    description: str

    # Position sizing
    initial_position_pct: float  # % of capital for initial entry
    max_position_pct: float      # Maximum position size

    # Risk management
    use_stop_loss: bool
    stop_loss_pct: Optional[float]  # % below entry

    # Profit taking
    profit_targets: List[float]  # % targets for scaling out
    scale_out_amounts: List[float]  # % of position to exit at each target

    # Hold time
    min_bars_in_trade: int
    max_bars_in_trade: int

    # Behavior
    scale_in_on_dips: bool
    hold_through_consolidation: bool
    exit_on_direction_change: bool
    exit_on_weak_signal: bool


class ExecutionStrategy(ABC):
    """Base class for execution strategies"""

    def __init__(self, config: StrategyConfig):
        self.config = config

    @abstractmethod
    def should_enter(self, signal, confidence: float, context: Dict) -> tuple[bool, float]:
        """
        Decide if should enter and with what size.

        Returns:
            (should_enter: bool, position_size_pct: float)
        """
        pass

    @abstractmethod
    def should_scale_in(self, signal, position, confidence: float, context: Dict) -> tuple[bool, float]:
        """
        Decide if should add to position and how much.

        Returns:
            (should_add: bool, add_size_pct: float)
        """
        pass

    @abstractmethod
    def should_scale_out(self, signal, position, confidence: float, context: Dict) -> tuple[bool, float]:
        """
        Decide if should take profits and how much.

        Returns:
            (should_exit: bool, exit_size_pct: float)
        """
        pass

    @abstractmethod
    def should_exit_fully(self, signal, position, confidence: float, context: Dict) -> tuple[bool, str]:
        """
        Decide if should exit entire position.

        Returns:
            (should_exit: bool, reason: str)
        """
        pass


# ============================================================================
# FAST SCALP STRATEGY
# ============================================================================

class FastScalp(ExecutionStrategy):
    """
    Fast Scalp: Quick in/out, tight stops, 1-3% targets

    Best for:
    - Murphy (SMC) on structure breaks
    - High frequency trading
    - Quick momentum bursts

    Characteristics:
    - Small profit targets (1-3%)
    - Tight stop losses (0.5-1%)
    - Hold time: 5-15 bars (5-15 minutes)
    - Exit quickly on any sign of reversal
    """

    def __init__(self):
        config = StrategyConfig(
            name="Fast Scalp",
            description="Quick 1-3% moves, tight stops, 5-15 bars",
            initial_position_pct=0.15,  # 15% of capital
            max_position_pct=0.25,      # Max 25%
            use_stop_loss=True,
            stop_loss_pct=0.01,         # 1% stop loss
            profit_targets=[0.015, 0.025, 0.03],  # 1.5%, 2.5%, 3%
            scale_out_amounts=[0.40, 0.40, 0.20],  # Exit 40/40/20
            min_bars_in_trade=3,
            max_bars_in_trade=15,
            scale_in_on_dips=False,      # No averaging down
            hold_through_consolidation=False,
            exit_on_direction_change=True,
            exit_on_weak_signal=True
        )
        super().__init__(config)

    def should_enter(self, signal, confidence: float, context: Dict) -> tuple[bool, float]:
        """Enter only on strong signals"""
        # Need high confidence for scalping
        if confidence < 0.70:
            return False, 0.0

        # For Murphy: Check for tier 1-2 signals
        if hasattr(signal, 'stars'):
            if signal.stars < 3:  # Murphy or Momo stars
                return False, 0.0

        return True, self.config.initial_position_pct

    def should_scale_in(self, signal, position, confidence: float, context: Dict) -> tuple[bool, float]:
        """No scaling in for fast scalps"""
        return False, 0.0

    def should_scale_out(self, signal, position, confidence: float, context: Dict) -> tuple[bool, float]:
        """Take profits at targets"""
        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0.0)

        # Check profit targets
        for i, target in enumerate(self.config.profit_targets):
            target_pct = target * 100
            if unrealized_pnl_pct >= target_pct:
                # Check if we already took profits at this level
                if not position.get(f'scaled_out_{i}', False):
                    return True, self.config.scale_out_amounts[i]

        return False, 0.0

    def should_exit_fully(self, signal, position, confidence: float, context: Dict) -> tuple[bool, str]:
        """Exit on stop loss, max time, or direction change"""
        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0.0)

        # Stop loss
        if unrealized_pnl_pct <= -self.config.stop_loss_pct * 100:
            return True, "stop_loss"

        # Max time in trade
        bars_held = position.get('bars_held', 0)
        if bars_held >= self.config.max_bars_in_trade:
            return True, "max_time"

        # Direction change
        if signal.direction != position.get('entry_direction'):
            return True, "direction_change"

        return False, ""


# ============================================================================
# HIT & RUN STRATEGY
# ============================================================================

class HitAndRun(ExecutionStrategy):
    """
    Hit & Run: Medium-term momentum, 5-10% targets

    Best for:
    - Momo (Momentum) on aligned timeframes
    - Gap-up follow-through
    - Trend continuation

    Characteristics:
    - Medium profit targets (5-10%)
    - Moderate stop losses (2-3%)
    - Hold time: 20-50 bars (20-50 minutes)
    - Exit on momentum loss
    """

    def __init__(self):
        config = StrategyConfig(
            name="Hit & Run",
            description="Medium 5-10% moves, 20-50 bars",
            initial_position_pct=0.25,  # 25% of capital
            max_position_pct=0.40,      # Max 40%
            use_stop_loss=True,
            stop_loss_pct=0.025,        # 2.5% stop loss
            profit_targets=[0.05, 0.08, 0.10],  # 5%, 8%, 10%
            scale_out_amounts=[0.30, 0.40, 0.30],
            min_bars_in_trade=10,
            max_bars_in_trade=50,
            scale_in_on_dips=True,       # Can add on pullbacks
            hold_through_consolidation=False,
            exit_on_direction_change=False,  # Allow small pullbacks
            exit_on_weak_signal=True
        )
        super().__init__(config)

    def should_enter(self, signal, confidence: float, context: Dict) -> tuple[bool, float]:
        """Enter on medium+ confidence"""
        if confidence < 0.60:
            return False, 0.0

        return True, self.config.initial_position_pct

    def should_scale_in(self, signal, position, confidence: float, context: Dict) -> tuple[bool, float]:
        """Add on dips if confidence still high"""
        if position.get('position_pct', 0) >= self.config.max_position_pct:
            return False, 0.0

        # Check for healthy pullback
        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0.0)

        # If down 1-3% from high but confidence still good
        if -3.0 <= unrealized_pnl_pct <= -1.0:
            if confidence >= 0.65:
                # Add 15% more
                return True, 0.15

        return False, 0.0

    def should_scale_out(self, signal, position, confidence: float, context: Dict) -> tuple[bool, float]:
        """Take profits at targets"""
        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0.0)

        for i, target in enumerate(self.config.profit_targets):
            target_pct = target * 100
            if unrealized_pnl_pct >= target_pct:
                if not position.get(f'scaled_out_{i}', False):
                    return True, self.config.scale_out_amounts[i]

        return False, 0.0

    def should_exit_fully(self, signal, position, confidence: float, context: Dict) -> tuple[bool, str]:
        """Exit on stop loss, max time, or confidence drop"""
        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0.0)

        # Stop loss
        if unrealized_pnl_pct <= -self.config.stop_loss_pct * 100:
            return True, "stop_loss"

        # Max time
        bars_held = position.get('bars_held', 0)
        if bars_held >= self.config.max_bars_in_trade:
            return True, "max_time"

        # Confidence dropped
        if confidence < 0.45:
            return True, "low_confidence"

        return False, ""


# ============================================================================
# ACCUMULATION STRATEGY
# ============================================================================

class Accumulation(ExecutionStrategy):
    """
    Accumulation: Build position on dips, scale out on strength

    Best for:
    - Momo (Momentum) on gap-up days
    - High conviction setups
    - Trend continuation with patience

    Characteristics:
    - No stop losses (conviction-based)
    - Scale in aggressively on dips
    - Scale out on strength at resistance
    - Hold time: 30-100 bars (30-100 minutes)
    """

    def __init__(self):
        config = StrategyConfig(
            name="Accumulation",
            description="Build on dips, scale out on strength, no stops",
            initial_position_pct=0.20,  # 20% of capital
            max_position_pct=1.20,      # Can go to 120% (average down!)
            use_stop_loss=False,
            stop_loss_pct=None,
            profit_targets=[0.08, 0.15, 0.25],  # 8%, 15%, 25%
            scale_out_amounts=[0.25, 0.35, 0.40],
            min_bars_in_trade=20,
            max_bars_in_trade=100,
            scale_in_on_dips=True,
            hold_through_consolidation=True,
            exit_on_direction_change=False,
            exit_on_weak_signal=False
        )
        super().__init__(config)

    def should_enter(self, signal, confidence: float, context: Dict) -> tuple[bool, float]:
        """Enter on any positive signal with conviction"""
        if confidence < 0.55:
            return False, 0.0

        return True, self.config.initial_position_pct

    def should_scale_in(self, signal, position, confidence: float, context: Dict) -> tuple[bool, float]:
        """Aggressively buy dips"""
        if position.get('position_pct', 0) >= self.config.max_position_pct:
            return False, 0.0

        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0.0)

        # Buy dips: down 3-10% from high
        if -10.0 <= unrealized_pnl_pct <= -3.0:
            if confidence >= 0.60:  # Still have conviction
                # Size based on dip size
                if unrealized_pnl_pct <= -7:
                    return True, 0.35  # Big dip = big add
                elif unrealized_pnl_pct <= -5:
                    return True, 0.25  # Medium dip
                else:
                    return True, 0.15  # Small dip

        return False, 0.0

    def should_scale_out(self, signal, position, confidence: float, context: Dict) -> tuple[bool, float]:
        """Take profits at major targets"""
        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0.0)

        for i, target in enumerate(self.config.profit_targets):
            target_pct = target * 100
            if unrealized_pnl_pct >= target_pct:
                # Also check for weakness at target
                if confidence < 0.55 or signal.direction == "−":
                    if not position.get(f'scaled_out_{i}', False):
                        return True, self.config.scale_out_amounts[i]

        return False, 0.0

    def should_exit_fully(self, signal, position, confidence: float, context: Dict) -> tuple[bool, str]:
        """Exit only on clear reversal or max time"""
        bars_held = position.get('bars_held', 0)

        # Max time
        if bars_held >= self.config.max_bars_in_trade:
            return True, "max_time"

        # Strong reversal signal
        if confidence < 0.35:
            if signal.direction != position.get('entry_direction'):
                return True, "reversal"

        return False, ""


# ============================================================================
# DIAMOND HAND STRATEGY
# ============================================================================

class DiamondHand(ExecutionStrategy):
    """
    Diamond Hand: Conviction hold, patient, exit on reversal only

    Best for:
    - High conviction setups (JuiceBot scanner picks)
    - Gap-up momentum days
    - Strong trend days

    Characteristics:
    - No stop losses
    - Hold through consolidation
    - No scaling in (all-in conviction)
    - Exit only on clear reversal
    - Hold time: 50-200 bars (50-200 minutes)
    """

    def __init__(self):
        config = StrategyConfig(
            name="Diamond Hand",
            description="Conviction hold, exit on reversal only",
            initial_position_pct=0.40,  # 40% of capital (big bet)
            max_position_pct=0.40,      # No scaling in
            use_stop_loss=False,
            stop_loss_pct=None,
            profit_targets=[0.15, 0.30, 0.50],  # 15%, 30%, 50%
            scale_out_amounts=[0.20, 0.30, 0.50],
            min_bars_in_trade=30,
            max_bars_in_trade=200,
            scale_in_on_dips=False,      # No averaging down
            hold_through_consolidation=True,
            exit_on_direction_change=False,
            exit_on_weak_signal=False
        )
        super().__init__(config)

    def should_enter(self, signal, confidence: float, context: Dict) -> tuple[bool, float]:
        """Enter only on very high conviction"""
        if confidence < 0.75:
            return False, 0.0

        # For Momo: need MAX JUICE (all timeframes aligned)
        if hasattr(signal, 'juice_score'):
            if signal.juice_score < 0.80:
                return False, 0.0

        return True, self.config.initial_position_pct

    def should_scale_in(self, signal, position, confidence: float, context: Dict) -> tuple[bool, float]:
        """No scaling in - all-in conviction"""
        return False, 0.0

    def should_scale_out(self, signal, position, confidence: float, context: Dict) -> tuple[bool, float]:
        """Only take profits at major milestones"""
        unrealized_pnl_pct = position.get('unrealized_pnl_pct', 0.0)

        for i, target in enumerate(self.config.profit_targets):
            target_pct = target * 100
            if unrealized_pnl_pct >= target_pct:
                # Only exit if also showing weakness
                if confidence < 0.50:
                    if not position.get(f'scaled_out_{i}', False):
                        return True, self.config.scale_out_amounts[i]

        return False, 0.0

    def should_exit_fully(self, signal, position, confidence: float, context: Dict) -> tuple[bool, str]:
        """Exit only on clear reversal or end of day"""
        bars_held = position.get('bars_held', 0)

        # Max time (end of day)
        if bars_held >= self.config.max_bars_in_trade:
            return True, "end_of_day"

        # Very strong reversal
        if confidence < 0.30:
            return True, "strong_reversal"

        # Opposing signal with high confidence
        if signal.direction != position.get('entry_direction'):
            if confidence > 0.70:  # Strong opposing signal
                return True, "high_confidence_reversal"

        return False, ""


# ============================================================================
# STRATEGY FACTORY
# ============================================================================

STRATEGY_MAP = {
    'fast_scalp': FastScalp,
    'hit_and_run': HitAndRun,
    'accumulation': Accumulation,
    'diamond_hand': DiamondHand
}


def get_strategy(strategy_name: str) -> ExecutionStrategy:
    """Get strategy instance by name"""
    strategy_class = STRATEGY_MAP.get(strategy_name.lower())
    if strategy_class is None:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(STRATEGY_MAP.keys())}")

    return strategy_class()


def list_strategies() -> Dict[str, str]:
    """List all available strategies"""
    return {
        name: cls().config.description
        for name, cls in STRATEGY_MAP.items()
    }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("EXECUTION STRATEGIES")
    print("=" * 80)

    for name, description in list_strategies().items():
        strategy = get_strategy(name)
        print(f"\n{strategy.config.name}:")
        print(f"  Description: {strategy.config.description}")
        print(f"  Initial Position: {strategy.config.initial_position_pct*100:.0f}%")
        print(f"  Max Position: {strategy.config.max_position_pct*100:.0f}%")
        print(f"  Stop Loss: {f'{strategy.config.stop_loss_pct*100:.1f}%' if strategy.config.use_stop_loss else 'None'}")
        print(f"  Profit Targets: {[f'{t*100:.0f}%' for t in strategy.config.profit_targets]}")
        print(f"  Hold Time: {strategy.config.min_bars_in_trade}-{strategy.config.max_bars_in_trade} bars")
        print(f"  Scale In: {'Yes' if strategy.config.scale_in_on_dips else 'No'}")
        print(f"  Hold Through Chop: {'Yes' if strategy.config.hold_through_consolidation else 'No'}")

    print("\n" + "=" * 80)
