"""
Murphy Test Evaluator - Background worker for signal evaluation
================================================================
Continuously evaluates recorded Murphy signals at multiple timeframes
(2min, 5min, 10min, 30min) to measure accuracy.
"""

import asyncio
import os
from datetime import datetime
from typing import List, Dict
from supabase import create_client, Client


class MurphyTestEvaluator:
    """Background evaluator for Murphy test signals."""

    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        self.supabase: Client = create_client(url, key)
        self.running = False

    async def start(self):
        """Start the evaluation loop."""
        print("[Murphy Evaluator] Starting background evaluator...")
        self.running = True

        try:
            while self.running:
                await self.evaluation_cycle()
                await asyncio.sleep(10)  # Check every 10 seconds
        except Exception as e:
            print(f"[Murphy Evaluator] Error: {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        """Stop the evaluation loop."""
        self.running = False
        print("[Murphy Evaluator] Stopped")

    async def evaluation_cycle(self):
        """Run one evaluation cycle - check all pending signals."""

        # Get active sessions
        result = self.supabase.table("murphy_test_sessions")\
            .select("id, symbol")\
            .eq("status", "active")\
            .execute()

        if not result.data:
            return

        print(f"[Murphy Evaluator] Found {len(result.data)} active sessions")

        for session in result.data:
            session_id = session['id']
            symbol = session['symbol']

            # Get current price for this symbol
            current_price = await self.get_current_price(symbol)
            if not current_price:
                continue

            # Get signals that need evaluation
            pending_signals = await self.get_pending_signals(session_id)

            for signal in pending_signals:
                await self.evaluate_signal(signal, current_price)

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
            print(f"[Murphy Evaluator] Failed to get price for {symbol}: {e}")

        return None

    async def get_pending_signals(self, session_id: str) -> List[Dict]:
        """Get signals that need evaluation."""

        # Query signals that:
        # 1. Belong to this session
        # 2. Don't have final_result yet (still pending)
        # 3. Are at least 2 minutes old

        result = self.supabase.table("murphy_signal_records")\
            .select("*")\
            .eq("session_id", session_id)\
            .is_("final_result", "pending")\
            .execute()

        if not result.data:
            return []

        # Filter by age (at least 2 minutes old)
        now = datetime.utcnow()
        pending = []

        for signal in result.data:
            timestamp = datetime.fromisoformat(signal['timestamp'].replace('Z', '+00:00'))
            age_minutes = (now - timestamp.replace(tzinfo=None)).total_seconds() / 60

            if age_minutes >= 2:
                pending.append(signal)

        return pending

    async def evaluate_signal(self, signal: Dict, current_price: float):
        """Evaluate a signal's accuracy at the appropriate timeframe."""

        signal_id = signal['id']
        timestamp = datetime.fromisoformat(signal['timestamp'].replace('Z', '+00:00'))
        entry_price = signal['price']
        direction = signal['direction']

        # Calculate age
        now = datetime.utcnow()
        age_minutes = (now - timestamp.replace(tzinfo=None)).total_seconds() / 60

        # Calculate price change
        price_change_pct = ((current_price - entry_price) / entry_price) * 100

        # Determine correctness (need at least 0.3% move to count)
        correct = False
        if abs(price_change_pct) >= 0.3:
            if direction == 'BULLISH' and price_change_pct > 0:
                correct = True
            elif direction == 'BEARISH' and price_change_pct < 0:
                correct = True

        # Create evaluation record
        eval_data = {
            "price": current_price,
            "change_pct": round(price_change_pct, 2),
            "correct": correct,
            "evaluated_at": datetime.utcnow().isoformat(),
            "elapsed_minutes": round(age_minutes, 1)
        }

        # Determine which timeframe to update
        update_data = {}

        if 1.5 <= age_minutes < 3.5 and not signal.get('eval_2min'):
            update_data['eval_2min'] = eval_data
            print(f"[Murphy Evaluator] 2min eval: {signal_id[:8]}... {price_change_pct:+.2f}% {'✓' if correct else '✗'}")

        elif 4 <= age_minutes < 7.5 and not signal.get('eval_5min'):
            update_data['eval_5min'] = eval_data
            print(f"[Murphy Evaluator] 5min eval: {signal_id[:8]}... {price_change_pct:+.2f}% {'✓' if correct else '✗'}")

        elif 8 <= age_minutes < 20 and not signal.get('eval_10min'):
            update_data['eval_10min'] = eval_data
            print(f"[Murphy Evaluator] 10min eval: {signal_id[:8]}... {price_change_pct:+.2f}% {'✓' if correct else '✗'}")

        elif age_minutes >= 25 and not signal.get('eval_30min'):
            update_data['eval_30min'] = eval_data
            update_data['final_result'] = 'correct' if correct else 'wrong'
            print(f"[Murphy Evaluator] 30min FINAL eval: {signal_id[:8]}... {price_change_pct:+.2f}% {'✓' if correct else '✗'}")

        # Update database
        if update_data:
            self.supabase.table("murphy_signal_records")\
                .update(update_data)\
                .eq("id", signal_id)\
                .execute()

            # If final evaluation, update session metrics
            if 'final_result' in update_data:
                await self._update_session_metrics(signal['session_id'])

    async def _update_session_metrics(self, session_id: str):
        """Recalculate and update session accuracy metrics."""

        # Get all evaluated signals
        result = self.supabase.table("murphy_signal_records")\
            .select("*")\
            .eq("session_id", session_id)\
            .in_("final_result", ["correct", "wrong"])\
            .execute()

        signals = result.data

        if not signals:
            return

        # Calculate metrics
        displayed = [s for s in signals if s['passed_filter']]
        filtered = [s for s in signals if not s['passed_filter']]

        correct_displayed = len([s for s in displayed if s['final_result'] == 'correct'])
        correct_filtered = len([s for s in filtered if s['final_result'] == 'correct'])

        accuracy_displayed = (correct_displayed / len(displayed) * 100) if displayed else 0
        accuracy_filtered = (correct_filtered / len(filtered) * 100) if filtered else 0

        avg_grade_displayed = sum(s['grade'] for s in displayed) / len(displayed) if displayed else 0
        avg_grade_filtered = sum(s['grade'] for s in filtered) / len(filtered) if filtered else 0

        # Get current metrics
        session_result = self.supabase.table("murphy_test_sessions")\
            .select("metrics")\
            .eq("id", session_id)\
            .single()\
            .execute()

        metrics = session_result.data['metrics']
        metrics.update({
            "correct_displayed": correct_displayed,
            "correct_filtered": correct_filtered,
            "accuracy_displayed": round(accuracy_displayed, 1),
            "accuracy_filtered": round(accuracy_filtered, 1),
            "avg_grade_displayed": round(avg_grade_displayed, 1),
            "avg_grade_filtered": round(avg_grade_filtered, 1)
        })

        # Update database
        self.supabase.table("murphy_test_sessions")\
            .update({"metrics": metrics})\
            .eq("id", session_id)\
            .execute()

        print(f"[Murphy Evaluator] Updated session {session_id[:8]}... metrics: {metrics['accuracy_displayed']:.1f}% displayed, {metrics['accuracy_filtered']:.1f}% filtered")


# Global evaluator instance
evaluator = MurphyTestEvaluator()


async def start_evaluator():
    """Start the evaluator background task."""
    await evaluator.start()


def stop_evaluator():
    """Stop the evaluator."""
    evaluator.stop()


if __name__ == "__main__":
    # Run standalone for testing
    print("Starting Murphy Test Evaluator...")
    asyncio.run(start_evaluator())
