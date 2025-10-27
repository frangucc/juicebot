#!/usr/bin/env python3
"""
Murphy Regression Test V2 - With Proper Trading Logic
======================================================

Improvements over V1:
1. Stop losses (-2% max loss)
2. Scale in/out (40/30/30 entry, 25/25/25/25 exit)
3. Risk modes (high/medium/low)
4. V2 feature position weighting
5. Smart reversal logic (go flat on weak signals)
6. Take profit targets

Test modes:
- high:   Aggressive (trade more, let winners ride)
- medium: Balanced (standard risk management)
- low:    Conservative (only premium signals, quick profits)
"""

import json
import statistics
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import sys
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from murphy_classifier_v2 import MurphyClassifier, Bar as MurphyBar, MurphySignal


@dataclass
class Bar:
    """Represents a single price bar"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    index: int


@dataclass
class SignalEvent:
    """Represents a Murphy signal with tier classification"""
    bar_index: int
    timestamp: str
    entry_price: float

    # Murphy classification
    direction: str
    stars: int
    grade: int
    confidence: float
    interpretation: str

    # V2 enhancements
    has_liquidity_sweep: bool
    rejection_type: Optional[str]
    pattern: Optional[str]
    fvg_momentum: Optional[str]

    # Tier classification (1=Premium, 2=Strong, 3=Standard, 4=Skip)
    tier: int = 3
    tier_name: str = "Standard"

    # Filter decision
    passed_filter: bool = False
    filter_reason: Optional[str] = None

    # Multi-timeframe results
    price_at_5_bars: Optional[float] = None
    pnl_at_5_bars: Optional[float] = None
    result_5_bars: Optional[str] = None

    price_at_10_bars: Optional[float] = None
    pnl_at_10_bars: Optional[float] = None
    result_10_bars: Optional[str] = None

    price_at_20_bars: Optional[float] = None
    pnl_at_20_bars: Optional[float] = None
    result_20_bars: Optional[str] = None

    price_at_50_bars: Optional[float] = None
    pnl_at_50_bars: Optional[float] = None
    result_50_bars: Optional[str] = None

    best_result: Optional[str] = None
    best_timeframe: Optional[int] = None

    # Trade results
    trade_taken: bool = False
    trade_entry_fills: List[Tuple[int, float, float]] = field(default_factory=list)  # (bar, price, size)
    trade_exit_fills: List[Tuple[int, float, float, str]] = field(default_factory=list)  # (bar, price, size, reason)
    trade_pnl: Optional[float] = None
    trade_stopped_out: bool = False


def classify_signal_tier(signal: MurphySignal) -> Tuple[int, str]:
    """
    Classify signal into tier based on V2 features and strength
    
    Tier 1 (Premium): Rejection + Pattern, or Rejection + high stars/grade
    Tier 2 (Strong): Single V2 feature with good fundamentals
    Tier 3 (Standard): Good fundamentals, minimal V2
    Tier 4 (Skip): Weak signals
    """
    
    # Tier 1: Premium signals
    if signal.rejection_type and signal.pattern:
        return 1, "Premium"
    if signal.rejection_type and signal.stars >= 3:
        return 1, "Premium"
    if signal.pattern and signal.grade >= 9:
        return 1, "Premium"
    
    # Tier 2: Strong signals
    if signal.rejection_type:
        return 2, "Strong"
    if signal.pattern:
        return 2, "Strong"
    if signal.has_liquidity_sweep and signal.grade >= 8:
        return 2, "Strong"
    
    # Tier 3: Standard signals
    if signal.stars >= 3 or signal.grade >= 7:
        return 3, "Standard"
    
    # Tier 4: Skip
    return 4, "Skip"




# ============================================================================
# RISK CONFIGURATIONS
# ============================================================================

RISK_MODES = {
    'high': {
        'name': 'Aggressive',
        'min_tier': 2,  # Trade Tier 2+ signals (Strong + Premium)
        'position_size_base': 0.12,  # 12% of capital base
        'stop_loss_pct': 0.025,  # -2.5% stop
        'scale_in_schedule': [0.40, 0.30, 0.30],  # How to build position
        'scale_in_triggers': [0, 0.01, 0.02],  # +0%, +1%, +2% to add
        'scale_out_targets': [0, 0, 0, 1.0],  # No profit taking, let it ride
        'scale_out_prices': [0.02, 0.04, 0.06, 0.08],  # Exit levels
        'allow_weak_reversals': True,  # Can reverse on Tier 3 signals
        'max_bars_in_trade': 75,  # Hold longer
    },
    'medium': {
        'name': 'Balanced',
        'min_tier': 1,  # Trade Tier 1+ (Premium + Strong)
        'position_size_base': 0.10,  # 10% of capital base
        'stop_loss_pct': 0.02,  # -2% stop
        'scale_in_schedule': [0.40, 0.30, 0.30],
        'scale_in_triggers': [0, 0.01, 0.015],
        'scale_out_targets': [0.25, 0.25, 0.25, 0.25],  # Equal profit taking
        'scale_out_prices': [0.02, 0.04, 0.06, 0.08],
        'allow_weak_reversals': False,  # Go flat on weak signals
        'max_bars_in_trade': 50,
    },
    'low': {
        'name': 'Conservative',
        'min_tier': 1,  # ONLY Premium signals
        'position_size_base': 0.08,  # 8% of capital base
        'stop_loss_pct': 0.015,  # -1.5% stop
        'scale_in_schedule': [0.30, 0.30, 0.40],  # Build slowly
        'scale_in_triggers': [0, 0.015, 0.025],  # Need more confirmation
        'scale_out_targets': [0.30, 0.30, 0.30, 0.10],  # Take profits early
        'scale_out_prices': [0.015, 0.025, 0.04, 0.06],  # Lower targets
        'allow_weak_reversals': False,
        'max_bars_in_trade': 40,  # Exit faster
    }
}


# ============================================================================
# TRADING SIMULATOR V2
# ============================================================================

@dataclass
class Position:
    """Represents an open position with partial fills"""
    signal: SignalEvent
    side: str  # 'long' or 'short'
    entry_bar: int
    entry_fills: List[Tuple[int, float, float]]  # [(bar, price, size), ...]
    total_size: float = 0
    avg_entry_price: float = 0
    
    # Scale in state
    scale_in_step: int = 0  # 0, 1, 2 (how many times we've added)
    
    # Scale out state
    remaining_size: float = 0
    scale_out_step: int = 0  # How many profit targets hit
    realized_pnl: float = 0
    
    # Stop loss
    stop_price: Optional[float] = None
    
    def update_avg_price(self):
        """Recalculate average entry price"""
        total_cost = sum(price * size for _, price, size in self.entry_fills)
        self.total_size = sum(size for _, _, size in self.entry_fills)
        self.remaining_size = self.total_size
        if self.total_size > 0:
            self.avg_entry_price = total_cost / self.total_size


class TradingSimulatorV2:
    """Enhanced trading simulator with proper risk management"""
    
    def __init__(self, starting_capital: float, risk_mode: str = 'medium'):
        self.capital = starting_capital
        self.starting_capital = starting_capital
        self.risk_mode = risk_mode
        self.config = RISK_MODES[risk_mode]
        
        self.position: Optional[Position] = None
        self.closed_trades: List[Position] = []
        self.equity_curve: List[Tuple[int, float]] = [(0, starting_capital)]
        
        # Stats
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        
    def calculate_position_size(self, signal: SignalEvent, price: float) -> float:
        """Calculate base position size with V2 weighting"""
        base_pct = self.config['position_size_base']
        
        # Tier multiplier
        tier_multipliers = {1: 1.5, 2: 1.3, 3: 1.0, 4: 0}
        tier_mult = tier_multipliers.get(signal.tier, 1.0)
        
        # V2 feature bonuses
        v2_bonus = 1.0
        if signal.rejection_type:
            v2_bonus += 0.3
        if signal.pattern:
            v2_bonus += 0.2
        if signal.has_liquidity_sweep:
            v2_bonus += 0.1
        
        # Final size
        total_mult = tier_mult * v2_bonus
        position_value = self.capital * base_pct * total_mult
        shares = position_value / price
        
        return shares
    
    def should_enter(self, signal: SignalEvent) -> bool:
        """Decide if we should enter this trade"""
        # Already in position
        if self.position:
            return False
        
        # Check tier vs risk mode minimum
        if signal.tier > self.config['min_tier']:
            return False  # Signal not strong enough for this risk mode
        
        # Skip neutral signals
        if signal.direction == "−":
            return False
        
        # For low risk mode, ONLY trade Tier 1 (Premium)
        if self.risk_mode == 'low' and signal.tier != 1:
            return False
        
        return True
    
    def enter_position(self, signal: SignalEvent, bar_index: int, price: float):
        """Enter first tranche of position"""
        side = 'long' if signal.direction == "↑" else 'short'
        
        # Calculate total position size
        total_size = self.calculate_position_size(signal, price)
        
        # First fill (40% or 30% depending on risk mode)
        first_fill_pct = self.config['scale_in_schedule'][0]
        first_fill_size = total_size * first_fill_pct
        
        # Create position
        position = Position(
            signal=signal,
            side=side,
            entry_bar=bar_index,
            entry_fills=[(bar_index, price, first_fill_size)],
            scale_in_step=0
        )
        position.update_avg_price()
        
        # Set stop loss
        if side == 'long':
            position.stop_price = price * (1 - self.config['stop_loss_pct'])
        else:
            position.stop_price = price * (1 + self.config['stop_loss_pct'])
        
        self.position = position
        signal.trade_taken = True
        signal.trade_entry_fills.append((bar_index, price, first_fill_size))
        
    def check_scale_in(self, bar_index: int, price: float):
        """Check if we should add to position"""
        if not self.position:
            return
        
        # Already fully scaled in?
        if self.position.scale_in_step >= len(self.config['scale_in_schedule']) - 1:
            return
        
        # Calculate unrealized P/L %
        if self.position.side == 'long':
            pnl_pct = (price - self.position.avg_entry_price) / self.position.avg_entry_price
        else:
            pnl_pct = (self.position.avg_entry_price - price) / self.position.avg_entry_price
        
        # Check if we hit the next scale in trigger
        next_step = self.position.scale_in_step + 1
        trigger = self.config['scale_in_triggers'][next_step]
        
        if pnl_pct >= trigger:
            # Add next tranche
            total_planned_size = self.calculate_position_size(self.position.signal, self.position.avg_entry_price)
            next_fill_pct = self.config['scale_in_schedule'][next_step]
            next_fill_size = total_planned_size * next_fill_pct
            
            self.position.entry_fills.append((bar_index, price, next_fill_size))
            self.position.update_avg_price()
            self.position.scale_in_step = next_step
            
            self.position.signal.trade_entry_fills.append((bar_index, price, next_fill_size))
    
    def check_scale_out(self, bar_index: int, price: float):
        """Check if we should take profits"""
        if not self.position:
            return
        
        # Calculate unrealized P/L %
        if self.position.side == 'long':
            pnl_pct = (price - self.position.avg_entry_price) / self.position.avg_entry_price
        else:
            pnl_pct = (self.position.avg_entry_price - price) / self.position.avg_entry_price
        
        # Check each profit target
        for i, target in enumerate(self.config['scale_out_prices']):
            # Already took profit at this level?
            if i < self.position.scale_out_step:
                continue
            
            # Hit target?
            if pnl_pct >= target:
                target_pct = self.config['scale_out_targets'][i]
                if target_pct == 0:
                    continue  # No exit at this level
                
                # Calculate size to exit
                exit_size = self.position.total_size * target_pct
                
                # Execute partial exit
                if self.position.side == 'long':
                    exit_pnl = (price - self.position.avg_entry_price) * exit_size
                else:
                    exit_pnl = (self.position.avg_entry_price - price) * exit_size
                
                self.position.realized_pnl += exit_pnl
                self.position.remaining_size -= exit_size
                self.position.scale_out_step = i + 1
                
                self.position.signal.trade_exit_fills.append((bar_index, price, exit_size, f"target_{int(target*100)}%"))
                
                # Update capital immediately
                self.capital += exit_pnl
    
    def check_stop_loss(self, bar_index: int, low: float, high: float) -> bool:
        """Check if stop loss was hit"""
        if not self.position:
            return False
        
        stop_hit = False
        if self.position.side == 'long':
            if low <= self.position.stop_price:
                stop_hit = True
                exit_price = self.position.stop_price
        else:
            if high >= self.position.stop_price:
                stop_hit = True
                exit_price = self.position.stop_price
        
        if stop_hit:
            self.close_position(bar_index, exit_price, "stop_loss")
            return True
        
        return False
    
    def check_direction_change(self, bar_index: int, price: float, new_signal: Optional[SignalEvent]) -> bool:
        """Check if Murphy changed direction"""
        if not self.position or not new_signal:
            return False
        
        current_direction = "BULLISH" if self.position.side == "long" else "BEARISH"
        new_direction = "BULLISH" if new_signal.direction == "↑" else "BEARISH" if new_signal.direction == "↓" else "NEUTRAL"
        
        if new_direction == "NEUTRAL":
            return False
        
        if current_direction != new_direction:
            # Direction changed!
            # If weak signal and we don't allow weak reversals, close position
            if not self.config['allow_weak_reversals'] and new_signal.tier >= 3:
                self.close_position(bar_index, price, "direction_change_weak")
                return True
            
            # Strong signal, close and potentially reverse later
            self.close_position(bar_index, price, "direction_change")
            return True
        
        return False
    
    def check_time_limit(self, bar_index: int, price: float) -> bool:
        """Check if position held too long"""
        if not self.position:
            return False
        
        bars_held = bar_index - self.position.entry_bar
        if bars_held >= self.config['max_bars_in_trade']:
            self.close_position(bar_index, price, "time_limit")
            return True
        
        return False
    
    def close_position(self, bar_index: int, price: float, reason: str):
        """Close entire position"""
        if not self.position:
            return
        
        # Calculate final P/L for remaining size
        remaining_size = self.position.remaining_size
        if remaining_size > 0:
            if self.position.side == 'long':
                final_pnl = (price - self.position.avg_entry_price) * remaining_size
            else:
                final_pnl = (self.position.avg_entry_price - price) * remaining_size
            
            self.position.realized_pnl += final_pnl
            self.capital += final_pnl
            
            self.position.signal.trade_exit_fills.append((bar_index, price, remaining_size, reason))
        
        # Record trade stats
        total_pnl = self.position.realized_pnl
        total_pnl_pct = (total_pnl / (self.position.avg_entry_price * self.position.total_size)) * 100
        
        self.position.signal.trade_pnl = total_pnl_pct
        self.position.signal.trade_stopped_out = (reason == "stop_loss")
        
        self.total_trades += 1
        if total_pnl > 0:
            self.wins += 1
        else:
            self.losses += 1
        
        self.closed_trades.append(self.position)
        self.equity_curve.append((bar_index, self.capital))
        self.position = None
    
    def get_performance_metrics(self) -> Dict:
        """Calculate trading performance"""
        if self.total_trades == 0:
            return {}
        
        win_rate = (self.wins / self.total_trades) * 100
        total_pnl = self.capital - self.starting_capital
        total_pnl_pct = (total_pnl / self.starting_capital) * 100
        
        # Calculate average win/loss
        wins = [t.realized_pnl for t in self.closed_trades if t.realized_pnl > 0]
        losses = [t.realized_pnl for t in self.closed_trades if t.realized_pnl <= 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Max drawdown
        peak = self.starting_capital
        max_dd = 0
        for _, equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        return {
            'total_trades': self.total_trades,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'final_capital': self.capital
        }



# ============================================================================
# MAIN EXECUTION
# ============================================================================

def load_historical_bars() -> List[Bar]:
    """Load BYND historical data"""
    print("Loading historical bars from bynd_historical_data.json...")
    
    with open('bynd_historical_data.json', 'r') as f:
        bars_data = json.load(f)
    
    bars = []
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
        bars.append(bar)
    
    print(f"✓ Loaded {len(bars)} bars")
    return bars


def run_murphy_test_v2(bars: List[Bar], risk_mode: str = 'medium') -> Tuple[List[SignalEvent], Dict]:
    """Run Murphy test with enhanced trading logic"""
    
    config = RISK_MODES[risk_mode]
    print(f"\nRunning Murphy Test V2 with {config['name']} risk mode...")
    print(f"  Min tier: {config['min_tier']}")
    print(f"  Position size: {config['position_size_base']*100:.1f}% base")
    print(f"  Stop loss: {config['stop_loss_pct']*100:.1f}%")
    print(f"  Scale in: {config['scale_in_schedule']}")
    print(f"  Scale out: {config['scale_out_targets']}")
    print()
    
    murphy = MurphyClassifier()
    trader = TradingSimulatorV2(starting_capital=100000, risk_mode=risk_mode)
    
    signals: List[SignalEvent] = []
    
    # Process each bar
    for i in range(20, len(bars)):
        current_bar = bars[i]
        
        # Build Murphy bars (last 100 bars)
        murphy_bars = []
        for idx, bar_data in enumerate(bars[max(0, i-100):i+1]):
            murphy_bars.append(MurphyBar(
                timestamp=bar_data.timestamp,
                open=bar_data.open,
                high=bar_data.high,
                low=bar_data.low,
                close=bar_data.close,
                volume=bar_data.volume,
                index=idx
            ))
        
        # Classify with Murphy
        signal = murphy.classify(
            bars=murphy_bars,
            signal_index=len(murphy_bars) - 1,
            structure_age_bars=10,
            level_price=None  # Auto-detect prior levels
        )
        
        # Classify signal tier
        tier, tier_name = classify_signal_tier(signal)
        
        # Create signal event
        signal_event = SignalEvent(
            bar_index=i,
            timestamp=current_bar.timestamp,
            entry_price=current_bar.close,
            direction=signal.direction,
            stars=signal.stars,
            grade=signal.grade,
            confidence=signal.confidence,
            interpretation=signal.interpretation,
            has_liquidity_sweep=signal.has_liquidity_sweep,
            rejection_type=signal.rejection_type,
            pattern=signal.pattern,
            fvg_momentum=signal.fvg_momentum,
            tier=tier,
            tier_name=tier_name,
            passed_filter=(tier <= config['min_tier'])  # Passes if tier good enough
        )
        
        signals.append(signal_event)
        
        # ======= TRADING LOGIC =======
        
        # Check stop loss FIRST (uses bar high/low)
        if trader.position:
            trader.check_stop_loss(i, current_bar.low, current_bar.high)
        
        # Check scale in
        if trader.position:
            trader.check_scale_in(i, current_bar.close)
        
        # Check scale out
        if trader.position:
            trader.check_scale_out(i, current_bar.close)
        
        # Check direction change
        if trader.position:
            trader.check_direction_change(i, current_bar.close, signal_event)
        
        # Check time limit
        if trader.position:
            trader.check_time_limit(i, current_bar.close)
        
        # Enter new trade if signal qualifies
        if trader.should_enter(signal_event):
            trader.enter_position(signal_event, i, current_bar.close)
        
        # Progress indicator
        if i % 500 == 0:
            print(f"  Processed {i}/{len(bars)} bars...")
    
    # Close any open position
    if trader.position:
        trader.close_position(len(bars)-1, bars[-1].close, "end_of_data")
    
    print(f"✓ Generated {len(signals)} signals")
    
    # Evaluate signals at multiple timeframes
    print("Evaluating signals at 5/10/20/50 bars...")
    for signal in signals:
        for timeframe in [5, 10, 20, 50]:
            future_index = signal.bar_index + timeframe
            if future_index < len(bars):
                future_price = bars[future_index].close
                pnl_pct = ((future_price - signal.entry_price) / signal.entry_price) * 100
                
                # Determine if correct
                def is_correct(pnl: float, direction: str) -> str:
                    if abs(pnl) < 0.3:
                        return 'neutral'
                    if direction == "↑" and pnl > 0:
                        return 'correct'
                    elif direction == "↓" and pnl < 0:
                        return 'correct'
                    else:
                        return 'wrong'
                
                result = is_correct(pnl_pct, signal.direction)
                
                setattr(signal, f'price_at_{timeframe}_bars', future_price)
                setattr(signal, f'pnl_at_{timeframe}_bars', pnl_pct)
                setattr(signal, f'result_{timeframe}_bars', result)
    
    # Get performance metrics
    perf = trader.get_performance_metrics()
    
    return signals, perf


def calculate_signal_metrics(signals: List[SignalEvent]) -> Dict:
    """Calculate accuracy metrics by tier and V2 features"""
    
    metrics = {
        'total_signals': len(signals),
        'by_tier': {},
        'by_v2_features': {},
        'by_timeframe': {}
    }
    
    # By tier
    for tier in [1, 2, 3, 4]:
        tier_signals = [s for s in signals if s.tier == tier]
        if tier_signals:
            eval_20 = [s for s in tier_signals if s.result_20_bars]
            correct = len([s for s in eval_20 if s.result_20_bars == 'correct'])
            
            metrics['by_tier'][tier] = {
                'count': len(tier_signals),
                'accuracy_20b': (correct / len(eval_20) * 100) if eval_20 else 0,
                'traded': len([s for s in tier_signals if s.trade_taken])
            }
    
    # By V2 features
    for feature_name, feature_filter in [
        ('rejection', lambda s: s.rejection_type),
        ('pattern', lambda s: s.pattern),
        ('liq_sweep', lambda s: s.has_liquidity_sweep),
        ('any_v2', lambda s: s.rejection_type or s.pattern or s.has_liquidity_sweep)
    ]:
        feature_signals = [s for s in signals if feature_filter(s)]
        if feature_signals:
            eval_20 = [s for s in feature_signals if s.result_20_bars]
            correct = len([s for s in eval_20 if s.result_20_bars == 'correct'])
            
            metrics['by_v2_features'][feature_name] = {
                'count': len(feature_signals),
                'accuracy_20b': (correct / len(eval_20) * 100) if eval_20 else 0
            }
    
    # By timeframe
    for tf in ['5', '10', '20', '50']:
        col = f'result_{tf}_bars'
        evaluated = [s for s in signals if getattr(s, col)]
        
        if evaluated:
            correct = len([s for s in evaluated if getattr(s, col) == 'correct'])
            traded_eval = [s for s in evaluated if s.trade_taken]
            traded_correct = len([s for s in traded_eval if getattr(s, col) == 'correct'])
            
            metrics['by_timeframe'][f'{tf}bars'] = {
                'total_evaluated': len(evaluated),
                'correct': correct,
                'accuracy': (correct / len(evaluated)) * 100,
                'traded_accuracy': (traded_correct / len(traded_eval) * 100) if traded_eval else 0
            }
    
    return metrics


def generate_report(bars: List[Bar], signals: List[SignalEvent], metrics: Dict, perf: Dict, risk_mode: str) -> str:
    """Generate comprehensive test report"""
    
    config = RISK_MODES[risk_mode]
    
    report = []
    report.append("=" * 100)
    report.append(f"MURPHY REGRESSION TEST V2 - {config['name'].upper()} RISK MODE")
    report.append("=" * 100)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Dataset: BYND - {len(bars)} bars ({bars[0].timestamp} to {bars[-1].timestamp})")
    report.append(f"Risk Mode: {risk_mode.upper()} ({config['name']})")
    report.append("")
    
    # Configuration
    report.append("RISK CONFIGURATION")
    report.append("-" * 100)
    report.append(f"Minimum signal tier:     {config['min_tier']}")
    report.append(f"Position size base:      {config['position_size_base']*100:.1f}% of capital")
    report.append(f"Stop loss:               {config['stop_loss_pct']*100:.1f}%")
    report.append(f"Scale in schedule:       {config['scale_in_schedule']}")
    report.append(f"Scale out targets:       {config['scale_out_targets']}")
    report.append(f"Allow weak reversals:    {'Yes' if config['allow_weak_reversals'] else 'No'}")
    report.append(f"Max bars in trade:       {config['max_bars_in_trade']}")
    report.append("")
    
    # Signal Summary
    report.append("SIGNAL SUMMARY")
    report.append("-" * 100)
    report.append(f"Total signals generated: {metrics['total_signals']}")
    for tier in [1, 2, 3, 4]:
        if tier in metrics['by_tier']:
            t = metrics['by_tier'][tier]
            tier_names = {1: 'Premium', 2: 'Strong', 3: 'Standard', 4: 'Skip'}
            report.append(f"  Tier {tier} ({tier_names[tier]:8s}): {t['count']:4d} signals, {t['accuracy_20b']:5.1f}% accurate, {t['traded']:4d} traded")
    report.append("")
    
    # V2 Feature Performance
    report.append("V2 FEATURE ACCURACY (@ 20 bars)")
    report.append("-" * 100)
    for feature, data in metrics['by_v2_features'].items():
        report.append(f"{feature:12s}: {data['count']:4d} signals, {data['accuracy_20b']:5.1f}% accurate")
    report.append("")
    
    # Multi-timeframe Accuracy
    report.append("MULTI-TIMEFRAME ACCURACY")
    report.append("-" * 100)
    for tf, data in metrics['by_timeframe'].items():
        report.append(f"{tf:8s}: {data['accuracy']:5.1f}% ({data['correct']}/{data['total_evaluated']}) | Traded: {data['traded_accuracy']:5.1f}%")
    report.append("")
    
    # Trading Performance
    report.append("TRADING SIMULATION PERFORMANCE")
    report.append("-" * 100)
    report.append(f"Total trades:        {perf['total_trades']}")
    report.append(f"Win rate:            {perf['win_rate']:.1f}% ({perf['wins']}W / {perf['losses']}L)")
    report.append("")
    report.append(f"Total P&L:           ${perf['total_pnl']:,.2f} ({perf['total_pnl_pct']:+.2f}%)")
    report.append(f"Starting capital:    ${100000:,.2f}")
    report.append(f"Ending capital:      ${perf['final_capital']:,.2f}")
    report.append("")
    report.append(f"Avg win:             ${perf['avg_win']:,.2f}")
    report.append(f"Avg loss:            ${perf['avg_loss']:,.2f}")
    report.append(f"Profit factor:       {perf['profit_factor']:.2f}")
    report.append("")
    report.append(f"Max drawdown:        {perf['max_drawdown']:.2f}%")
    report.append("")
    report.append("=" * 100)
    
    return "\n".join(report)


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Murphy Regression Test V2 with proper trading logic')
    parser.add_argument('--risk', choices=['high', 'medium', 'low'], default='medium',
                       help='Risk mode: high (aggressive), medium (balanced), low (conservative)')
    parser.add_argument('--all', action='store_true',
                       help='Run all three risk modes and compare')
    
    args = parser.parse_args()
    
    # Load data
    bars = load_historical_bars()
    print()
    
    if args.all:
        # Run all three modes
        print("=" * 100)
        print("RUNNING ALL RISK MODES")
        print("=" * 100)
        print()
        
        results = {}
        for risk_mode in ['low', 'medium', 'high']:
            print(f"\n{'='*100}")
            print(f"TESTING: {risk_mode.upper()} RISK")
            print('='*100)
            
            signals, perf = run_murphy_test_v2(bars, risk_mode)
            metrics = calculate_signal_metrics(signals)
            report = generate_report(bars, signals, metrics, perf, risk_mode)
            
            results[risk_mode] = {
                'signals': signals,
                'perf': perf,
                'metrics': metrics,
                'report': report
            }
            
            print()
            print(report)
            
            # Save individual report
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"murphy_v2_report_{risk_mode}_{timestamp}.txt"
            with open(filename, 'w') as f:
                f.write(report)
            print(f"\n✓ Report saved to: {filename}")
        
        # Generate comparison
        print("\n\n")
        print("=" * 100)
        print("RISK MODE COMPARISON")
        print("=" * 100)
        print()
        print(f"{'Metric':<30s} {'Low Risk':<20s} {'Medium Risk':<20s} {'High Risk':<20s}")
        print("-" * 100)
        
        for metric in ['total_trades', 'win_rate', 'total_pnl_pct', 'profit_factor', 'max_drawdown']:
            values = []
            for risk_mode in ['low', 'medium', 'high']:
                perf = results[risk_mode]['perf']
                if metric in perf:
                    val = perf[metric]
                    if metric == 'win_rate' or metric == 'total_pnl_pct' or metric == 'max_drawdown':
                        values.append(f"{val:+.2f}%")
                    elif metric == 'profit_factor':
                        values.append(f"{val:.2f}")
                    else:
                        values.append(f"{val}")
            
            metric_name = metric.replace('_', ' ').title()
            print(f"{metric_name:<30s} {values[0]:<20s} {values[1]:<20s} {values[2]:<20s}")
        
        print()
        print("=" * 100)
        
    else:
        # Run single mode
        signals, perf = run_murphy_test_v2(bars, args.risk)
        metrics = calculate_signal_metrics(signals)
        report = generate_report(bars, signals, metrics, perf, args.risk)
        
        print()
        print(report)
        
        # Save report
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"murphy_v2_report_{args.risk}_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"\n✓ Report saved to: {filename}")
        
        # Save detailed JSON
        json_filename = f"murphy_v2_signals_{args.risk}_{timestamp}.json"
        signals_data = []
        for sig in signals:
            signals_data.append({
                'bar_index': sig.bar_index,
                'timestamp': sig.timestamp,
                'entry_price': sig.entry_price,
                'direction': sig.direction,
                'stars': sig.stars,
                'grade': sig.grade,
                'tier': sig.tier,
                'tier_name': sig.tier_name,
                'has_liquidity_sweep': sig.has_liquidity_sweep,
                'rejection_type': sig.rejection_type,
                'pattern': sig.pattern,
                'fvg_momentum': sig.fvg_momentum,
                'passed_filter': sig.passed_filter,
                'trade_taken': sig.trade_taken,
                'trade_pnl': sig.trade_pnl,
                'trade_stopped_out': sig.trade_stopped_out,
                'result_20_bars': sig.result_20_bars
            })
        
        with open(json_filename, 'w') as f:
            json.dump({
                'risk_mode': args.risk,
                'config': RISK_MODES[args.risk],
                'performance': perf,
                'metrics': metrics,
                'signals': signals_data
            }, f, indent=2)
        
        print(f"✓ Detailed data saved to: {json_filename}")


if __name__ == "__main__":
    main()
