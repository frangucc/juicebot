"""
Murphy Test Recorder - Session and Signal Recording System
============================================================
Records all Murphy signals (filtered and displayed) with multi-timeframe evaluation
for optimization and performance tracking.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from supabase import create_client, Client
from dataclasses import dataclass, asdict
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


@dataclass
class TestSession:
    """Test session configuration and metadata."""
    id: str
    symbol: str
    started_at: datetime
    ended_at: Optional[datetime]
    status: str  # 'active', 'completed', 'cancelled'
    config: Dict[str, Any]
    metrics: Dict[str, Any]
    notes: Optional[str] = None


@dataclass
class SignalRecord:
    """Individual signal record with evaluation results."""
    id: Optional[str]
    session_id: str
    symbol: str
    timestamp: datetime
    price: float

    # Classification
    direction: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    stars: int
    grade: int
    confidence: float

    # Murphy details
    rvol: float
    volume_efficiency: float
    body_ratio: float
    atr_ratio: float
    interpretation: str

    # V2 enhancements
    has_liquidity_sweep: bool
    rejection_type: Optional[str]
    pattern: Optional[str]
    fvg_momentum: Optional[str]

    # Filtering
    passed_filter: bool
    filter_reason: Optional[str]

    # Evaluations (populated asynchronously)
    eval_2min: Optional[Dict] = None
    eval_5min: Optional[Dict] = None
    eval_10min: Optional[Dict] = None
    eval_30min: Optional[Dict] = None
    final_result: Optional[str] = None  # 'correct', 'wrong', 'pending', 'neutral'

    raw_data: Optional[Dict] = None


class MurphyTestRecorder:
    """Records Murphy test sessions and signals with async evaluation."""

    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables required")

        self.supabase: Client = create_client(url, key)
        self.active_sessions: Dict[str, str] = {}  # {symbol: session_id}

    # ===== SESSION MANAGEMENT =====

    def create_session(
        self,
        symbol: str,
        config: Optional[Dict] = None,
        notes: Optional[str] = None
    ) -> TestSession:
        """Create a new test session."""
        default_config = {
            "min_stars": 3,
            "min_grade": 7,
            "min_confidence": 1.0,
            "sticky_direction": True,
            "require_flip_conviction": True
        }

        session_config = {**default_config, **(config or {})}

        result = self.supabase.table("murphy_test_sessions").insert({
            "symbol": symbol.upper(),
            "status": "active",
            "config": session_config,
            "notes": notes,
            "metrics": {
                "total_signals_generated": 0,
                "signals_displayed": 0,
                "signals_filtered": 0,
                "correct_displayed": 0,
                "correct_filtered": 0,
                "accuracy_displayed": 0,
                "accuracy_filtered": 0,
                "avg_grade_displayed": 0,
                "avg_grade_filtered": 0
            }
        }).execute()

        session_data = result.data[0]
        session_id = session_data['id']

        # Track active session
        self.active_sessions[symbol.upper()] = session_id

        print(f"[Murphy Test] Created session {session_id} for {symbol}")

        return TestSession(
            id=session_id,
            symbol=symbol.upper(),
            started_at=datetime.fromisoformat(session_data['started_at'].replace('Z', '+00:00')),
            ended_at=None,
            status='active',
            config=session_config,
            metrics=session_data['metrics'],
            notes=notes
        )

    def get_active_session(self, symbol: str) -> Optional[TestSession]:
        """Get active session for symbol."""
        # Check cache first
        if symbol.upper() in self.active_sessions:
            session_id = self.active_sessions[symbol.upper()]
            return self.get_session(session_id)

        # Query database
        result = self.supabase.table("murphy_test_sessions")\
            .select("*")\
            .eq("symbol", symbol.upper())\
            .eq("status", "active")\
            .order("started_at", desc=True)\
            .limit(1)\
            .execute()

        if not result.data:
            return None

        session_data = result.data[0]
        self.active_sessions[symbol.upper()] = session_data['id']

        return TestSession(
            id=session_data['id'],
            symbol=session_data['symbol'],
            started_at=datetime.fromisoformat(session_data['started_at'].replace('Z', '+00:00')),
            ended_at=datetime.fromisoformat(session_data['ended_at'].replace('Z', '+00:00')) if session_data.get('ended_at') else None,
            status=session_data['status'],
            config=session_data['config'],
            metrics=session_data['metrics'],
            notes=session_data.get('notes')
        )

    def get_session(self, session_id: str) -> Optional[TestSession]:
        """Get session by ID."""
        result = self.supabase.table("murphy_test_sessions")\
            .select("*")\
            .eq("id", session_id)\
            .single()\
            .execute()

        if not result.data:
            return None

        session_data = result.data
        return TestSession(
            id=session_data['id'],
            symbol=session_data['symbol'],
            started_at=datetime.fromisoformat(session_data['started_at'].replace('Z', '+00:00')),
            ended_at=datetime.fromisoformat(session_data['ended_at'].replace('Z', '+00:00')) if session_data.get('ended_at') else None,
            status=session_data['status'],
            config=session_data['config'],
            metrics=session_data['metrics'],
            notes=session_data.get('notes')
        )

    def end_session(self, session_id: str, status: str = 'completed') -> None:
        """End a test session."""
        self.supabase.table("murphy_test_sessions").update({
            "status": status,
            "ended_at": datetime.utcnow().isoformat()
        }).eq("id", session_id).execute()

        # Remove from active cache
        for symbol, sid in list(self.active_sessions.items()):
            if sid == session_id:
                del self.active_sessions[symbol]
                break

        print(f"[Murphy Test] Ended session {session_id} with status: {status}")

    # ===== SIGNAL RECORDING =====

    def record_signal(
        self,
        session_id: str,
        symbol: str,
        signal: Any,  # MurphySignal object
        price: float,
        bar_count: int,  # NEW: Number of bars when signal fired
        passed_filter: bool,
        filter_reason: Optional[str] = None
    ) -> str:
        """Record a single signal (filtered or displayed) with initial tracking data."""

        signal_data = {
            "session_id": session_id,
            "symbol": symbol.upper(),
            "timestamp": datetime.utcnow().isoformat(),
            "entry_price": price,
            "bar_count_at_signal": bar_count,

            # Classification
            "direction": "BULLISH" if signal.direction == "↑" else "BEARISH" if signal.direction == "↓" else "NEUTRAL",
            "stars": signal.stars,
            "grade": signal.grade,
            "confidence": signal.confidence,

            # Murphy details
            "rvol": signal.rvol,
            "volume_efficiency": signal.volume_efficiency,
            "body_ratio": signal.body_ratio,
            "atr_ratio": signal.atr_ratio,
            "interpretation": signal.interpretation,

            # V2 enhancements
            "has_liquidity_sweep": signal.has_liquidity_sweep,
            "rejection_type": signal.rejection_type,
            "pattern": signal.pattern,
            "fvg_momentum": signal.fvg_momentum,

            # Filtering
            "passed_filter": passed_filter,
            "filter_reason": filter_reason,

            # Initialize heat/gain tracking
            "peak_price": price,  # Start at entry
            "peak_gain_pct": 0.0,
            "worst_price": price,  # Start at entry
            "max_heat_pct": 0.0,

            # Will be updated as signal runs
            "final_result": "premature" if bar_count < 20 else "active",

            # Raw data for debugging
            "raw_data": {
                "stars_display": "*" * signal.stars if signal.stars > 0 else "",
                "label": f"{signal.direction} {'*' * signal.stars} [{signal.grade}]"
            }
        }

        result = self.supabase.table("murphy_signal_records")\
            .insert(signal_data)\
            .execute()

        signal_id = result.data[0]['id']

        # Update session metrics
        self._update_session_metrics(session_id, passed_filter)

        print(f"[Murphy Test] Recorded signal {signal_id}: {signal_data['direction']} [{signal.grade}] passed={passed_filter}")

        return signal_id

    def _update_session_metrics(self, session_id: str, passed_filter: bool) -> None:
        """Update session metrics after recording a signal."""
        # Get current session
        result = self.supabase.table("murphy_test_sessions")\
            .select("metrics")\
            .eq("id", session_id)\
            .single()\
            .execute()

        metrics = result.data['metrics']
        metrics['total_signals_generated'] = metrics.get('total_signals_generated', 0) + 1

        if passed_filter:
            metrics['signals_displayed'] = metrics.get('signals_displayed', 0) + 1
        else:
            metrics['signals_filtered'] = metrics.get('signals_filtered', 0) + 1

        # Update database
        self.supabase.table("murphy_test_sessions")\
            .update({"metrics": metrics})\
            .eq("id", session_id)\
            .execute()

    # ===== PRICE EVALUATION =====

    async def evaluate_signal(
        self,
        signal_id: str,
        current_price: float,
        elapsed_minutes: float
    ) -> None:
        """Evaluate a signal's accuracy after time has passed."""

        # Get signal data
        result = self.supabase.table("murphy_signal_records")\
            .select("*")\
            .eq("id", signal_id)\
            .single()\
            .execute()

        if not result.data:
            return

        signal = result.data
        entry_price = signal['price']
        direction = signal['direction']

        # Calculate price change
        price_change_pct = ((current_price - entry_price) / entry_price) * 100

        # Determine if correct (need at least 0.3% move to count)
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
            "elapsed_minutes": round(elapsed_minutes, 1)
        }

        # Determine which timeframe to update
        update_data = {}

        if 1.5 <= elapsed_minutes < 3.5 and not signal.get('eval_2min'):
            update_data['eval_2min'] = eval_data
        elif 4 <= elapsed_minutes < 7.5 and not signal.get('eval_5min'):
            update_data['eval_5min'] = eval_data
        elif 8 <= elapsed_minutes < 20 and not signal.get('eval_10min'):
            update_data['eval_10min'] = eval_data
        elif elapsed_minutes >= 25 and not signal.get('eval_30min'):
            update_data['eval_30min'] = eval_data
            # 30min is final evaluation
            update_data['final_result'] = 'correct' if correct else 'wrong'

        if update_data:
            self.supabase.table("murphy_signal_records")\
                .update(update_data)\
                .eq("id", signal_id)\
                .execute()

            print(f"[Murphy Test] Evaluated signal {signal_id} at {elapsed_minutes:.1f}min: {price_change_pct:+.2f}% ({'✓' if correct else '✗'})")

            # Update session accuracy metrics if final
            if 'final_result' in update_data:
                await self._update_accuracy_metrics(signal['session_id'])

    async def _update_accuracy_metrics(self, session_id: str) -> None:
        """Recalculate and update session accuracy metrics."""

        # Get all evaluated signals for this session
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

    # ===== QUERY METHODS =====

    def get_session_signals(
        self,
        session_id: str,
        limit: int = 100,
        passed_filter: Optional[bool] = None
    ) -> List[Dict]:
        """Get signals for a session."""

        query = self.supabase.table("murphy_signal_records")\
            .select("*")\
            .eq("session_id", session_id)\
            .order("timestamp", desc=True)\
            .limit(limit)

        if passed_filter is not None:
            query = query.eq("passed_filter", passed_filter)

        result = query.execute()
        return result.data

    def get_recent_sessions(self, symbol: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get recent test sessions."""

        query = self.supabase.table("murphy_test_sessions")\
            .select("*")\
            .order("started_at", desc=True)\
            .limit(limit)

        if symbol:
            query = query.eq("symbol", symbol.upper())

        result = query.execute()
        return result.data


# Global recorder instance (may be None if env vars not set)
try:
    murphy_recorder = MurphyTestRecorder()
    print("[Murphy Test Recorder] ✓ Initialized successfully")
except Exception as e:
    murphy_recorder = None
    print(f"[Murphy Test Recorder] ✗ Failed to initialize: {e}")
    print("[Murphy Test Recorder] Test recording will be disabled")
