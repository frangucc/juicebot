"""
Murphy Heat Tracker - Real-time Signal Performance Tracking
============================================================
Tracks peak gain, max heat, and duration for all active signals.
Updates every second while signals are active.
"""

import asyncio
import os
from datetime import datetime
from typing import List, Dict
from supabase import create_client, Client
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


class MurphyHeatTracker:
    """Real-time heat and gain tracker for Murphy signals."""

    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY required")

        self.supabase: Client = create_client(url, key)
        self.running = False
        self.price_cache: Dict[str, float] = {}  # {symbol: latest_price}

    async def start(self):
        """Start the heat tracking loop."""
        print("[Murphy Heat Tracker] Starting...")
        self.running = True

        try:
            while self.running:
                await self.tracking_cycle()
                await asyncio.sleep(1)  # Update every second
        except Exception as e:
            print(f"[Murphy Heat Tracker] Error: {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        """Stop the heat tracking loop."""
        self.running = False
        print("[Murphy Heat Tracker] Stopped")

    async def tracking_cycle(self):
        """Run one tracking cycle - update all active signals."""

        # Get all active signals
        try:
            result = self.supabase.table("murphy_signal_records")\
                .select("*")\
                .in_("final_result", ["active", "premature"])\
                .execute()

            if not result.data:
                return

            active_signals = result.data

            # Group by symbol to batch price fetches
            symbols = set(signal['symbol'] for signal in active_signals)

            # Update price cache
            for symbol in symbols:
                price = await self.get_current_price(symbol)
                if price:
                    self.price_cache[symbol] = price

            # Update each signal
            for signal in active_signals:
                await self.update_signal_heat_gain(signal)

        except Exception as e:
            print(f"[Murphy Heat Tracker] Cycle error: {e}")

    async def get_current_price(self, symbol: str) -> float:
        """Get current price from symbol_state."""
        try:
            result = self.supabase.table("symbol_state")\
                .select("current_price")\
                .eq("symbol", symbol.upper())\
                .single()\
                .execute()

            if result.data:
                return float(result.data['current_price'])
        except Exception as e:
            # Don't log every error, too noisy
            pass

        return None

    async def evaluate_multiframe(
        self,
        signal_id: str,
        signal: Dict,
        bars_elapsed: int,
        current_price: float,
        entry_price: float,
        direction: str
    ):
        """Evaluate signal at 5, 10, 20, 50 bar milestones."""

        # Calculate P/L
        pnl_pct = ((current_price - entry_price) / entry_price) * 100

        # Determine if signal was correct
        def is_correct(pnl: float, dir: str) -> str:
            if abs(pnl) < 0.3:
                return 'neutral'
            if dir == 'BULLISH' and pnl > 0:
                return 'correct'
            elif dir == 'BEARISH' and pnl < 0:
                return 'correct'
            else:
                return 'wrong'

        result = is_correct(pnl_pct, direction)
        now = datetime.utcnow()
        update_data = {}

        # Check each milestone
        milestones = [
            (5, 'price_at_5_bars', 'pnl_at_5_bars', 'result_5_bars', 'evaluated_at_5_bars'),
            (10, 'price_at_10_bars', 'pnl_at_10_bars', 'result_10_bars', 'evaluated_at_10_bars'),
            (20, 'price_at_20_bars', 'pnl_at_20_bars', 'result_20_bars', 'evaluated_at_20_bars'),
            (50, 'price_at_50_bars', 'pnl_at_50_bars', 'result_50_bars', 'evaluated_at_50_bars'),
        ]

        for bars, price_col, pnl_col, result_col, time_col in milestones:
            # If we've reached this milestone and haven't evaluated yet
            if bars_elapsed >= bars and not signal.get(result_col):
                update_data[price_col] = current_price
                update_data[pnl_col] = round(pnl_pct, 2)
                update_data[result_col] = result
                update_data[time_col] = now.isoformat()
                update_data['bars_elapsed'] = bars_elapsed

                print(f"[Murphy Multiframe] {signal['symbol']} @ {bars} bars: {direction} → {result} ({pnl_pct:+.2f}%)")

        # Update database if we hit any milestones
        if update_data:
            self.supabase.table("murphy_signal_records")\
                .update(update_data)\
                .eq("id", signal_id)\
                .execute()

    async def update_signal_heat_gain(self, signal: Dict):
        """Update heat and gain tracking for a single signal."""

        signal_id = signal['id']
        symbol = signal['symbol']
        direction = signal['direction']
        entry_price = signal['entry_price']
        timestamp = datetime.fromisoformat(signal['timestamp'].replace('Z', '+00:00'))
        bar_count_at_signal = signal.get('bar_count_at_signal', 0)

        # Get current price
        current_price = self.price_cache.get(symbol)
        if not current_price:
            return

        # Calculate elapsed time in minutes (use as proxy for bars)
        now = datetime.utcnow()
        elapsed_minutes = (now - timestamp.replace(tzinfo=None)).total_seconds() / 60
        # Approximate bars (1 bar per minute)
        bars_elapsed = int(elapsed_minutes)

        # Calculate price change
        price_change_pct = ((current_price - entry_price) / entry_price) * 100

        # Multi-timeframe evaluation at 5, 10, 20, 50 bars
        await self.evaluate_multiframe(
            signal_id=signal_id,
            signal=signal,
            bars_elapsed=bars_elapsed,
            current_price=current_price,
            entry_price=entry_price,
            direction=direction
        )

        # Current peak and heat values
        current_peak_price = signal.get('peak_price', entry_price)
        current_peak_gain = signal.get('peak_gain_pct', 0.0)
        current_worst_price = signal.get('worst_price', entry_price)
        current_max_heat = signal.get('max_heat_pct', 0.0)

        # Update peak (best price in signal direction)
        updated_peak = False
        if direction == 'BULLISH':
            # Peak = highest price
            if current_price > current_peak_price:
                current_peak_price = current_price
                current_peak_gain = price_change_pct
                updated_peak = True
        elif direction == 'BEARISH':
            # Peak = lowest price (for shorts, down is good)
            if current_price < current_peak_price:
                current_peak_price = current_price
                current_peak_gain = abs(price_change_pct)  # Absolute value for shorts
                updated_peak = True

        # Update heat (worst price against signal)
        updated_heat = False
        if direction == 'BULLISH':
            # Heat = lowest price (drawdown for longs)
            if current_price < current_worst_price:
                current_worst_price = current_price
                current_max_heat = abs(price_change_pct)
                updated_heat = True
        elif direction == 'BEARISH':
            # Heat = highest price (drawdown for shorts)
            if current_price > current_worst_price:
                current_worst_price = current_price
                current_max_heat = price_change_pct
                updated_heat = True

        # Calculate duration
        now = datetime.utcnow()
        duration_seconds = int((now - timestamp.replace(tzinfo=None)).total_seconds())

        # Only update if something changed
        if updated_peak or updated_heat or duration_seconds != signal.get('duration_seconds'):
            update_data = {
                'peak_price': current_peak_price,
                'peak_gain_pct': round(current_peak_gain, 2),
                'worst_price': current_worst_price,
                'max_heat_pct': round(current_max_heat, 2),
                'duration_seconds': duration_seconds
            }

            # Add peak/heat reached timestamps if they were just updated
            if updated_peak:
                update_data['peak_reached_at'] = now.isoformat()
            if updated_heat:
                update_data['heat_reached_at'] = now.isoformat()

            self.supabase.table("murphy_signal_records")\
                .update(update_data)\
                .eq("id", signal_id)\
                .execute()

            if updated_peak or updated_heat:
                print(f"[Murphy Heat Tracker] {symbol} {direction}: Peak {current_peak_gain:+.2f}% | Heat {current_max_heat:.2f}% | {duration_seconds}s")

    async def close_signal(self, signal_id: str, exit_price: float, new_direction: str):
        """Close an active signal when direction changes."""

        # Get signal
        result = self.supabase.table("murphy_signal_records")\
            .select("*")\
            .eq("id", signal_id)\
            .single()\
            .execute()

        if not result.data:
            return

        signal = result.data
        entry_price = signal['entry_price']
        direction = signal['direction']

        # Calculate final P/L
        final_pnl_pct = ((exit_price - entry_price) / entry_price) * 100

        # Determine win/loss
        # For BULLISH: win if final P/L > 0
        # For BEARISH: win if final P/L < 0 (price went down)
        final_result = 'neutral'

        if abs(final_pnl_pct) >= 0.3:  # Minimum 0.3% move to count
            if direction == 'BULLISH' and final_pnl_pct > 0:
                final_result = 'win'
            elif direction == 'BEARISH' and final_pnl_pct < 0:
                final_result = 'win'
            else:
                final_result = 'loss'

        # Calculate duration
        timestamp = datetime.fromisoformat(signal['timestamp'].replace('Z', '+00:00'))
        now = datetime.utcnow()
        duration_seconds = int((now - timestamp.replace(tzinfo=None)).total_seconds())

        # Update signal
        update_data = {
            'signal_changed_at': now.isoformat(),
            'exit_price': exit_price,
            'final_pnl_pct': round(final_pnl_pct if direction == 'BULLISH' else -final_pnl_pct, 2),
            'duration_seconds': duration_seconds,
            'final_result': final_result
        }

        self.supabase.table("murphy_signal_records")\
            .update(update_data)\
            .eq("id", signal_id)\
            .execute()

        symbol = signal['symbol']
        peak_gain = signal.get('peak_gain_pct', 0)
        max_heat = signal.get('max_heat_pct', 0)

        print(f"[Murphy Heat Tracker] CLOSED {symbol} {direction}: Entry ${entry_price:.2f} → Exit ${exit_price:.2f} | Peak: +{peak_gain:.2f}% | Heat: -{max_heat:.2f}% | P/L: {final_pnl_pct:+.2f}% | Result: {final_result.upper()}")


# Global tracker instance
try:
    heat_tracker = MurphyHeatTracker()
    print("[Murphy Heat Tracker] ✓ Initialized successfully")
except Exception as e:
    heat_tracker = None
    print(f"[Murphy Heat Tracker] ✗ Failed to initialize: {e}")


async def start_heat_tracker():
    """Start the heat tracker background task."""
    if heat_tracker:
        await heat_tracker.start()
    else:
        print("[Murphy Heat Tracker] Not available")


def stop_heat_tracker():
    """Stop the heat tracker."""
    if heat_tracker:
        heat_tracker.stop()
