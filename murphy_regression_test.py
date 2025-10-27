#!/usr/bin/env python3
"""
Murphy Classifier Regression Test - Trading Simulation
========================================================

Tests Murphy's classification algorithm against historical BYND data to validate:
1. Prediction accuracy at multiple timeframes (5/10/20/50 bars)
2. Signal quality by grade and star rating
3. Filter effectiveness (shown vs hidden signals)
4. Trading performance simulation (P&L if following signals)

Simulates a trader who:
- Takes position on every signal (or filtered signals only)
- Position size weighted by signal strength (stars/grade)
- Exits when direction changes or after N bars
- Tracks cumulative P&L, win rate, max drawdown

This script runs independently and generates detailed reports.
"""

import json
import statistics
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import sys

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
    """Represents a Murphy signal at a specific bar"""
    bar_index: int
    timestamp: str
    entry_price: float

    # Murphy classification
    direction: str  # ↑/↓/−
    stars: int  # 0-4
    grade: int  # 1-10
    confidence: float
    interpretation: str

    # V2 enhancements
    has_liquidity_sweep: bool
    rejection_type: Optional[str]
    pattern: Optional[str]
    fvg_momentum: Optional[str]

    # Filter decision
    passed_filter: bool
    filter_reason: Optional[str]

    # Multi-timeframe results
    price_at_5_bars: Optional[float] = None
    pnl_at_5_bars: Optional[float] = None
    result_5_bars: Optional[str] = None  # 'correct', 'wrong', 'neutral'

    price_at_10_bars: Optional[float] = None
    pnl_at_10_bars: Optional[float] = None
    result_10_bars: Optional[str] = None

    price_at_20_bars: Optional[float] = None
    pnl_at_20_bars: Optional[float] = None
    result_20_bars: Optional[str] = None

    price_at_50_bars: Optional[float] = None
    pnl_at_50_bars: Optional[float] = None
    result_50_bars: Optional[str] = None

    # Best result across all timeframes
    best_result: Optional[str] = None
    best_timeframe: Optional[str] = None

    # Trading simulation
    trade_taken: bool = False
    trade_exit_bar: Optional[int] = None
    trade_exit_price: Optional[float] = None
    trade_pnl: Optional[float] = None
    trade_bars_held: Optional[int] = None


@dataclass
class Trade:
    """Represents a simulated trade"""
    entry_bar: int
    entry_price: float
    side: str  # 'long' or 'short'
    signal: SignalEvent
    size: float  # Position size (weighted by signal strength)

    exit_bar: Optional[int] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    bars_held: Optional[int] = None
    exit_reason: Optional[str] = None  # 'direction_change', 'stop', 'target', 'time_limit'


class MurphyFilter:
    """Implements the sticky directional filter logic"""

    def __init__(self):
        self.last_direction = None
        self.last_grade = 0
        self.last_stars = 0

    def should_display(self, signal: MurphySignal) -> Tuple[bool, Optional[str]]:
        """Determine if signal passes filter (sticky directional logic)"""

        direction_text = "BULLISH" if signal.direction == "↑" else "BEARISH" if signal.direction == "↓" else "NEUTRAL"

        # Base threshold: only consider signals with minimum quality
        is_significant = (
            signal.stars >= 3 or
            signal.grade >= 7 or
            abs(signal.confidence) >= 1.0
        )

        if not is_significant:
            return False, f"below threshold: {signal.stars}* [{signal.grade}]"

        if self.last_direction is None:
            # First signal ever
            self.last_direction = direction_text
            self.last_grade = signal.grade
            self.last_stars = signal.stars
            return True, "initial signal"

        if direction_text == self.last_direction:
            # SAME direction - only update if STRONGER
            if signal.grade > self.last_grade or signal.stars > self.last_stars:
                self.last_grade = signal.grade
                self.last_stars = signal.stars
                return True, f"stronger {direction_text}: grade {self.last_grade}→{signal.grade}"
            else:
                return False, f"weaker/same {direction_text}"
        else:
            # DIRECTION CHANGED - require high conviction to flip
            if signal.grade >= 7 or signal.stars >= 3:
                self.last_direction = direction_text
                self.last_grade = signal.grade
                self.last_stars = signal.stars
                return True, f"direction flip {self.last_direction}→{direction_text} with conviction"
            else:
                return False, f"direction flip rejected: not strong enough"


class TradingSimulator:
    """Simulates trading based on Murphy signals"""

    def __init__(self, starting_capital: float = 100000, use_filter: bool = True):
        self.capital = starting_capital
        self.starting_capital = starting_capital
        self.use_filter = use_filter
        self.trades: List[Trade] = []
        self.open_trade: Optional[Trade] = None
        self.equity_curve: List[Tuple[int, float]] = [(0, starting_capital)]

    def calculate_position_size(self, signal: SignalEvent, price: float) -> float:
        """Calculate position size based on signal strength"""
        # Base position: 10% of capital
        base_size_pct = 0.10

        # Weight by signal strength
        # Stars: 0-4 → 0.5x to 1.5x
        star_weight = 0.5 + (signal.stars / 4.0)

        # Grade: 1-10 → 0.5x to 1.5x
        grade_weight = 0.5 + ((signal.grade - 1) / 9.0)

        # Combined weight
        total_weight = (star_weight + grade_weight) / 2.0

        # Calculate shares
        position_value = self.capital * base_size_pct * total_weight
        shares = position_value / price

        return shares

    def should_take_trade(self, signal: SignalEvent) -> bool:
        """Decide if we should trade this signal"""
        if self.use_filter:
            return signal.passed_filter
        return True  # Trade all signals if filter disabled

    def enter_trade(self, signal: SignalEvent, bar_index: int, price: float):
        """Enter a new trade"""
        # Close existing trade first if any
        if self.open_trade:
            return  # Skip if already in trade

        if signal.direction == "−":
            return  # Don't trade neutral signals

        side = 'long' if signal.direction == "↑" else 'short'
        size = self.calculate_position_size(signal, price)

        trade = Trade(
            entry_bar=bar_index,
            entry_price=price,
            side=side,
            signal=signal,
            size=size
        )

        self.open_trade = trade
        signal.trade_taken = True

    def check_exit(self, current_bar: int, current_price: float, new_signal: Optional[SignalEvent] = None) -> bool:
        """Check if we should exit current trade"""
        if not self.open_trade:
            return False

        # Exit if direction changes
        if new_signal and new_signal.direction != "−":
            new_direction = "BULLISH" if new_signal.direction == "↑" else "BEARISH"
            current_direction = "BULLISH" if self.open_trade.side == "long" else "BEARISH"

            if new_direction != current_direction:
                self.exit_trade(current_bar, current_price, "direction_change")
                return True

        # Exit after 50 bars max
        bars_held = current_bar - self.open_trade.entry_bar
        if bars_held >= 50:
            self.exit_trade(current_bar, current_price, "time_limit")
            return True

        return False

    def exit_trade(self, bar_index: int, price: float, reason: str):
        """Exit current trade"""
        if not self.open_trade:
            return

        trade = self.open_trade
        trade.exit_bar = bar_index
        trade.exit_price = price
        trade.exit_reason = reason
        trade.bars_held = bar_index - trade.entry_bar

        # Calculate P&L
        if trade.side == 'long':
            trade.pnl = (price - trade.entry_price) * trade.size
        else:  # short
            trade.pnl = (trade.entry_price - price) * trade.size

        trade.pnl_pct = (trade.pnl / (trade.entry_price * trade.size)) * 100

        # Update capital
        self.capital += trade.pnl

        # Store trade
        self.trades.append(trade)

        # Update equity curve
        self.equity_curve.append((bar_index, self.capital))

        # Update signal with trade results
        trade.signal.trade_exit_bar = bar_index
        trade.signal.trade_exit_price = price
        trade.signal.trade_pnl = trade.pnl_pct
        trade.signal.trade_bars_held = trade.bars_held

        self.open_trade = None

    def get_performance_metrics(self) -> Dict:
        """Calculate trading performance metrics"""
        if not self.trades:
            return {'total_trades': 0, 'error': 'No trades executed'}

        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]

        total_pnl = sum(t.pnl for t in self.trades)
        total_pnl_pct = ((self.capital - self.starting_capital) / self.starting_capital) * 100

        # Max drawdown
        peak = self.starting_capital
        max_dd = 0
        for _, equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = ((peak - equity) / peak) * 100
            if dd > max_dd:
                max_dd = dd

        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(self.trades)) * 100,

            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'avg_win': statistics.mean([t.pnl for t in winning_trades]) if winning_trades else 0,
            'avg_loss': statistics.mean([t.pnl for t in losing_trades]) if losing_trades else 0,
            'largest_win': max([t.pnl for t in winning_trades]) if winning_trades else 0,
            'largest_loss': min([t.pnl for t in losing_trades]) if losing_trades else 0,

            'avg_bars_held': statistics.mean([t.bars_held for t in self.trades]),
            'max_drawdown_pct': max_dd,

            'starting_capital': self.starting_capital,
            'ending_capital': self.capital,
            'profit_factor': (
                sum(t.pnl for t in winning_trades) / abs(sum(t.pnl for t in losing_trades))
                if losing_trades and sum(t.pnl for t in losing_trades) != 0
                else float('inf') if winning_trades else 0
            )
        }


def load_historical_bars(filename: str = "bynd_historical_data.json") -> List[Bar]:
    """Load historical bars from JSON file"""
    print(f"Loading historical bars from {filename}...")

    with open(filename, 'r') as f:
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


def run_murphy_regression(bars: List[Bar], simulate_trading: bool = True) -> Tuple[List[SignalEvent], Dict, Optional[Dict]]:
    """Run Murphy classifier on all bars and evaluate"""

    print(f"Running Murphy classifier on {len(bars)} bars...")

    murphy = MurphyClassifier()
    filter_engine = MurphyFilter()

    signals: List[SignalEvent] = []

    # Trading simulator
    trader = TradingSimulator(starting_capital=100000, use_filter=True) if simulate_trading else None

    # Process each bar
    for i in range(20, len(bars)):  # Start at bar 20 (need history)
        current_bar = bars[i]

        # Build Murphy bars
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

        # Classify (level_price=None triggers auto-detection of prior levels)
        signal = murphy.classify(
            bars=murphy_bars,
            signal_index=len(murphy_bars) - 1,
            structure_age_bars=10,
            level_price=None  # Auto-detect nearest prior swing high/low
        )

        # DEBUG: Print V2 features for bar 100
        if i == 100:
            print(f"\n[DEBUG] Bar 100 Murphy Signal:")
            print(f"  Direction: {signal.direction} Stars: {signal.stars} Grade: {signal.grade}")
            print(f"  has_liquidity_sweep: {signal.has_liquidity_sweep} (type: {type(signal.has_liquidity_sweep)})")
            print(f"  rejection_type: {signal.rejection_type} (type: {type(signal.rejection_type)})")
            print(f"  pattern: {signal.pattern} (type: {type(signal.pattern)})")
            print(f"  fvg_momentum: {signal.fvg_momentum} (type: {type(signal.fvg_momentum)})")

        # Apply filter
        passed, reason = filter_engine.should_display(signal)

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
            passed_filter=passed,
            filter_reason=reason
        )

        signals.append(signal_event)

        # Trading simulation
        if trader:
            # Check if we should exit current trade
            trader.check_exit(i, current_bar.close, signal_event)

            # Enter new trade if signal passes
            if trader.should_take_trade(signal_event):
                trader.enter_trade(signal_event, i, current_bar.close)

        # Progress indicator
        if i % 500 == 0:
            print(f"  Processed {i}/{len(bars)} bars...")

    # Close any open trade at end
    if trader and trader.open_trade:
        trader.exit_trade(len(bars)-1, bars[-1].close, "end_of_data")

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

                # Store results
                setattr(signal, f'price_at_{timeframe}_bars', future_price)
                setattr(signal, f'pnl_at_{timeframe}_bars', pnl_pct)
                setattr(signal, f'result_{timeframe}_bars', result)

        # Determine best result
        results = [
            ('5B', signal.result_5_bars),
            ('10B', signal.result_10_bars),
            ('20B', signal.result_20_bars),
            ('50B', signal.result_50_bars)
        ]
        results = [(tf, r) for tf, r in results if r]
        if results:
            # Prefer 'correct' over 'neutral' over 'wrong'
            best = max(results, key=lambda x: {'correct': 2, 'neutral': 1, 'wrong': 0}.get(x[1], 0))
            signal.best_result = best[1]
            signal.best_timeframe = best[0]

    # Calculate metrics
    metrics = calculate_metrics(signals)

    # Trading performance
    trading_perf = trader.get_performance_metrics() if trader else None

    return signals, metrics, trading_perf


def calculate_metrics(signals: List[SignalEvent]) -> Dict:
    """Calculate comprehensive accuracy metrics"""

    total = len(signals)
    shown = [s for s in signals if s.passed_filter]
    hidden = [s for s in signals if not s.passed_filter]

    metrics = {
        'total_signals': total,
        'shown_signals': len(shown),
        'hidden_signals': len(hidden),
        'by_timeframe': {},
        'by_grade': {},
        'by_stars': {},
        'early_but_right': []
    }

    # Analyze by timeframe
    for tf in ['5', '10', '20', '50']:
        col = f'result_{tf}_bars'
        evaluated = [s for s in signals if getattr(s, col)]

        if evaluated:
            correct = len([s for s in evaluated if getattr(s, col) == 'correct'])
            shown_eval = [s for s in evaluated if s.passed_filter]
            shown_correct = len([s for s in shown_eval if getattr(s, col) == 'correct'])

            metrics['by_timeframe'][f'{tf}bars'] = {
                'total_evaluated': len(evaluated),
                'correct': correct,
                'accuracy': (correct / len(evaluated)) * 100,
                'shown_accuracy': (shown_correct / len(shown_eval) * 100) if shown_eval else 0
            }

    # Analyze by grade
    for grade in range(1, 11):
        sigs = [s for s in signals if s.grade == grade]
        if sigs:
            eval_20 = [s for s in sigs if s.result_20_bars]
            correct_20 = len([s for s in eval_20 if s.result_20_bars == 'correct'])

            metrics['by_grade'][grade] = {
                'count': len(sigs),
                'accuracy_20bars': (correct_20 / len(eval_20) * 100) if eval_20 else 0
            }

    # Analyze by stars
    for stars in range(0, 5):
        sigs = [s for s in signals if s.stars == stars]
        if sigs:
            eval_20 = [s for s in sigs if s.result_20_bars]
            correct_20 = len([s for s in eval_20 if s.result_20_bars == 'correct'])

            metrics['by_stars'][stars] = {
                'count': len(sigs),
                'accuracy_20bars': (correct_20 / len(eval_20) * 100) if eval_20 else 0
            }

    # Early but right
    early_right = [
        s for s in signals
        if s.result_5_bars == 'wrong' and s.result_20_bars == 'correct'
    ]
    metrics['early_but_right'] = len(early_right)

    return metrics


def generate_report(bars: List[Bar], signals: List[SignalEvent], metrics: Dict, trading_perf: Optional[Dict]) -> str:
    """Generate comprehensive test report"""

    report = []
    report.append("=" * 100)
    report.append("MURPHY CLASSIFIER REGRESSION TEST REPORT")
    report.append("=" * 100)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Dataset: BYND - {len(bars)} bars ({bars[0].timestamp} to {bars[-1].timestamp})")
    report.append("")

    # Signal summary
    report.append("SIGNAL SUMMARY")
    report.append("-" * 100)
    report.append(f"Total signals generated: {metrics['total_signals']}")
    report.append(f"  Shown (passed filter): {metrics['shown_signals']}")
    report.append(f"  Hidden (filtered out): {metrics['hidden_signals']}")
    report.append("")

    # Multi-timeframe accuracy
    report.append("MULTI-TIMEFRAME ACCURACY")
    report.append("-" * 100)
    for tf, data in metrics['by_timeframe'].items():
        report.append(f"{tf:8s}: {data['accuracy']:5.1f}% ({data['correct']}/{data['total_evaluated']}) | Shown: {data['shown_accuracy']:5.1f}%")
    report.append("")

    # Grade analysis
    report.append("ACCURACY BY GRADE (@ 20 bars)")
    report.append("-" * 100)
    for grade in range(10, 0, -1):
        if grade in metrics['by_grade']:
            data = metrics['by_grade'][grade]
            report.append(f"[{grade:2d}]: {data['count']:4d} signals, {data['accuracy_20bars']:5.1f}% accurate")
    report.append("")

    # Star analysis
    report.append("ACCURACY BY STARS (@ 20 bars)")
    report.append("-" * 100)
    for stars in range(4, -1, -1):
        if stars in metrics['by_stars']:
            data = metrics['by_stars'][stars]
            star_display = '★' * stars if stars > 0 else '☆'
            report.append(f"{star_display:4s}: {data['count']:4d} signals, {data['accuracy_20bars']:5.1f}% accurate")
    report.append("")

    # Early but right
    report.append(f"'EARLY BUT RIGHT' SIGNALS: {metrics['early_but_right']}")
    report.append("")

    # Trading performance
    if trading_perf:
        report.append("TRADING SIMULATION PERFORMANCE")
        report.append("-" * 100)
        report.append(f"Total trades: {trading_perf['total_trades']}")
        report.append(f"Win rate: {trading_perf['win_rate']:.1f}% ({trading_perf['winning_trades']}W / {trading_perf['losing_trades']}L)")
        report.append(f"")
        report.append(f"Total P&L: ${trading_perf['total_pnl']:,.2f} ({trading_perf['total_pnl_pct']:+.2f}%)")
        report.append(f"Starting capital: ${trading_perf['starting_capital']:,.2f}")
        report.append(f"Ending capital: ${trading_perf['ending_capital']:,.2f}")
        report.append(f"")
        report.append(f"Avg win: ${trading_perf['avg_win']:,.2f}")
        report.append(f"Avg loss: ${trading_perf['avg_loss']:,.2f}")
        report.append(f"Largest win: ${trading_perf['largest_win']:,.2f}")
        report.append(f"Largest loss: ${trading_perf['largest_loss']:,.2f}")
        report.append(f"Profit factor: {trading_perf['profit_factor']:.2f}")
        report.append(f"")
        report.append(f"Avg bars held: {trading_perf['avg_bars_held']:.1f}")
        report.append(f"Max drawdown: {trading_perf['max_drawdown_pct']:.2f}%")
        report.append("")

    report.append("=" * 100)

    return "\n".join(report)


def main():
    """Run Murphy regression test"""
    print("Murphy Classifier Regression Test")
    print("=" * 100)
    print()

    # Load data
    bars = load_historical_bars()
    print()

    # Run regression test
    signals, metrics, trading_perf = run_murphy_regression(bars, simulate_trading=True)
    print()

    # Generate report
    report = generate_report(bars, signals, metrics, trading_perf)
    print(report)

    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"murphy_regression_report_{timestamp}.txt"
    with open(report_file, 'w') as f:
        f.write(report)

    print(f"\n✓ Report saved to: {report_file}")

    # Save signals as JSON
    signals_data = []
    for sig in signals:
        signals_data.append({
            'bar_index': sig.bar_index,
            'timestamp': sig.timestamp,
            'entry_price': sig.entry_price,
            'direction': sig.direction,
            'stars': sig.stars,
            'grade': sig.grade,
            'confidence': sig.confidence,
            'passed_filter': sig.passed_filter,
            # V2 enhancements
            'has_liquidity_sweep': sig.has_liquidity_sweep,
            'rejection_type': sig.rejection_type,
            'pattern': sig.pattern,
            'fvg_momentum': sig.fvg_momentum,
            # Multi-timeframe results
            'result_5_bars': sig.result_5_bars,
            'result_10_bars': sig.result_10_bars,
            'result_20_bars': sig.result_20_bars,
            'result_50_bars': sig.result_50_bars,
            'best_result': sig.best_result,
            'trade_taken': sig.trade_taken,
            'trade_pnl': sig.trade_pnl
        })

    json_file = f"murphy_signals_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump({
            'config': {
                'total_bars': len(bars),
                'starting_bar': 20
            },
            'metrics': metrics,
            'trading_performance': trading_perf,
            'signals': signals_data
        }, f, indent=2)

    print(f"✓ Signals saved to: {json_file}")


if __name__ == "__main__":
    main()
