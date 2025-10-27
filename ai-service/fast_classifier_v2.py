"""
Fast-path classifier V2 - Database-driven
==========================================
Uses TradeCommandExecutor for all command handling.
No hardcoded commands - everything comes from Supabase.
"""

import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from trade_command_executor import TradeCommandExecutor
from indicator_executor import IndicatorExecutor
import asyncio


@dataclass
class FastResponse:
    """Response from fast path."""
    text: str
    matched_pattern: str


class TradingClassifierV2:
    """
    Database-driven trading classifier.
    All commands loaded from Supabase via TradeCommandExecutor.
    """

    def __init__(self, user_id: str = None, conversation_id: str = None):
        self.conversation_id = conversation_id
        self.executor = TradeCommandExecutor(user_id=user_id, conversation_id=conversation_id)
        self.indicator_executor = IndicatorExecutor()
        self.bar_history = []  # Store last 100 bars for analysis

    @property
    def market_data(self):
        """Expose market_data from executor for backwards compatibility."""
        return self.executor.market_data

    def update_market_data(self, symbol: str, bar: Dict[str, Any]):
        """Update market data from WebSocket."""
        self.executor.update_market_data(symbol, bar)

        # Store in history (keep last 100 bars)
        self.bar_history.append(bar)
        if len(self.bar_history) > 100:
            self.bar_history.pop(0)

        # Update indicator executor's bar history
        self.indicator_executor.update_bar_history(bar)

    async def classify(self, message: str, symbol: str) -> Optional[FastResponse]:
        """
        Classify message and return fast response if applicable.

        Returns:
            FastResponse if fast-path match, None if needs LLM
        """
        # Pass bar_history to executor so it can calculate ranges properly
        self.executor.bar_history = self.bar_history

        # Check for interactive state responses first
        if self.conversation_id:
            from conversation_state import conversation_state
            state = conversation_state.get_state(self.conversation_id)

            if state and state['command'] == 'scaleout_speed_selection':
                # User is responding to scaleout speed prompt
                msg_lower = message.strip().lower()

                # Map user input to speed
                speed_map = {
                    '1': 'fast',
                    'fast': 'fast',
                    '2': 'medium',
                    'medium': 'medium',
                    '3': 'slow',
                    'slow': 'slow'
                }

                if msg_lower in speed_map:
                    speed = speed_map[msg_lower]
                    result = await self.executor.execute_scaleout_with_speed(state['symbol'], speed)

                    return FastResponse(
                        text=result,
                        matched_pattern=f"scaleout_speed:{speed}"
                    )

            if state and state['command'] == 'scalein_speed_selection':
                # User is responding to scalein speed prompt
                msg_lower = message.strip().lower()

                # Map user input to speed
                speed_map = {
                    '1': 'fast',
                    'fast': 'fast',
                    '2': 'medium',
                    'medium': 'medium',
                    '3': 'slow',
                    'slow': 'slow'
                }

                if msg_lower in speed_map:
                    speed = speed_map[msg_lower]
                    result = await self.executor.execute_scalein_with_speed(
                        state['symbol'],
                        state['side'],
                        state['quantity'],
                        speed
                    )

                    return FastResponse(
                        text=result,
                        matched_pattern=f"scalein_speed:{speed}"
                    )

        # Try indicators first (vp, rvol, vwap, voltrend)
        indicator_result = await self.indicator_executor.execute(message, symbol)
        if indicator_result:
            return FastResponse(
                text=indicator_result,
                matched_pattern=f"indicator:{message}"
            )

        # Check for Murphy classifier command
        if message.strip().lower().startswith('murphy'):
            # Check if it's "murphy live" to start background ticker
            if 'live' in message.strip().lower():
                return await self._start_murphy_live(symbol)

            murphy_result = await self._execute_murphy(message, symbol)
            if murphy_result:
                return FastResponse(
                    text=murphy_result,
                    matched_pattern="murphy"
                )

        # Check for Momo classifier command
        if message.strip().lower().startswith('momo'):
            # Check if it's "momo live" to start background ticker
            if 'live' in message.strip().lower():
                return await self._start_momo_live(symbol)

            momo_result = await self._execute_momo(message, symbol)
            if momo_result:
                return FastResponse(
                    text=momo_result,
                    matched_pattern="momo"
                )

        # Try to execute via trade command executor
        result = await self.executor.execute(message, symbol)

        if result:
            # Determine what pattern was matched
            match = self.executor.match_command(message)
            pattern_name = match[0] if match else "unknown"

            return FastResponse(
                text=result,
                matched_pattern=pattern_name
            )

        # No match - needs LLM
        return None

    async def _start_murphy_live(self, symbol: str) -> FastResponse:
        """Start live Murphy ticker - updates every second via event bus."""
        import asyncio
        from event_bus import event_bus

        # Start background task
        asyncio.create_task(self._murphy_live_worker(symbol))

        return FastResponse(
            text=(
                f"✓ Murphy Live started for {symbol}\n\n"
                f"📊 Analyzing bar data every second...\n"
                f"🧪 Test session auto-created (click flask icon to view)\n\n"
                f"⏱️  Note: Murphy needs ~20 bars to warm up before producing signals.\n"
                f"Signals will appear in the widget above the chart when ready.\n\n"
                f"Type 'murphy stop' to end."
            ),
            matched_pattern="murphy_live"
        )

    async def _murphy_live_worker(self, symbol: str):
        """Background worker that publishes Murphy updates every second."""
        import asyncio
        from event_bus import event_bus

        print(f"[Murphy Live] Started for {symbol}")

        # State tracking for signal persistence
        last_published_signal = None  # Store last published signal
        last_direction = None  # Track last direction (BULLISH/BEARISH/NEUTRAL)
        last_grade = 0  # Track last grade
        last_stars = 0  # Track last stars

        # Auto-start test recording (optional, fails gracefully)
        test_session_id = None
        test_recorder = None
        heat_tracker = None
        last_signal_id = None  # Track active signal for closing when direction changes

        try:
            from murphy_test_recorder import murphy_recorder
            if murphy_recorder is not None:
                # Check for existing active session or create new one
                existing_session = murphy_recorder.get_active_session(symbol)
                if existing_session:
                    test_session_id = existing_session.id
                    print(f"[Murphy Live] Using existing test session {test_session_id[:8]}...")
                else:
                    # Auto-create session
                    session = murphy_recorder.create_session(
                        symbol=symbol,
                        notes=f"Auto-started with Murphy Live at {asyncio.get_event_loop().time()}"
                    )
                    test_session_id = session.id
                    print(f"[Murphy Live] Auto-created test session {test_session_id[:8]}...")
                test_recorder = murphy_recorder

                # Load heat tracker for closing signals
                try:
                    from murphy_heat_tracker import heat_tracker as ht
                    heat_tracker = ht
                except Exception:
                    pass
        except Exception as e:
            print(f"[Murphy Live] Test recording disabled: {e}")
            test_recorder = None

        try:
            while True:
                # Get current market data
                data = self.executor.market_data.get(symbol)
                if not data or not self.bar_history or len(self.bar_history) < 20:
                    await asyncio.sleep(1)
                    continue

                # Run Murphy classification
                try:
                    import sys, os
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                    from murphy_classifier_v2 import MurphyClassifier, Bar

                    bars = []
                    for idx, bar_data in enumerate(self.bar_history[-100:]):
                        bars.append(Bar(
                            timestamp=bar_data.get('timestamp', ''),
                            open=bar_data.get('open', 0),
                            high=bar_data.get('high', 0),
                            low=bar_data.get('low', 0),
                            close=bar_data.get('close', 0),
                            volume=int(bar_data.get('volume', 0)),
                            index=idx
                        ))

                    murphy = MurphyClassifier()
                    signal = murphy.classify(
                        bars=bars,
                        signal_index=len(bars) - 1,
                        structure_age_bars=10,
                        level_price=data['price']
                    )

                    # Map to readable strength
                    if signal.stars == 4:
                        strength = "STRONG"
                    elif signal.stars == 3:
                        strength = "MODERATE"
                    elif signal.stars == 2:
                        strength = "WEAK"
                    elif signal.stars == 1:
                        strength = "MINIMAL"
                    else:
                        strength = "CHOP"

                    # Map direction to readable text
                    direction_text = "BULLISH" if signal.direction == "↑" else "BEARISH" if signal.direction == "↓" else "NEUTRAL"

                    # Format stars
                    stars_display = "*" * signal.stars if signal.stars > 0 else "NO SIGNAL"

                    # SMART FILTER: Sticky directional logic
                    # Only update widget if:
                    # 1. First signal (no previous direction)
                    # 2. New signal is STRONGER (higher grade OR more stars) in SAME direction
                    # 3. Direction changed AND new signal is high-conviction (grade >= 7 OR stars >= 3)

                    should_publish = False
                    reason = ""

                    # Base threshold: only consider signals with minimum quality
                    is_significant = (
                        signal.stars >= 3 or
                        signal.grade >= 7 or
                        abs(signal.confidence) >= 1.0
                    )

                    if not is_significant:
                        reason = f"below threshold: {stars_display} [{signal.grade}]"
                    elif last_direction is None:
                        # First signal ever
                        should_publish = True
                        reason = "initial signal"
                    elif direction_text == last_direction:
                        # SAME direction - only update if STRONGER
                        if signal.grade > last_grade or signal.stars > last_stars:
                            should_publish = True
                            reason = f"stronger {direction_text}: grade {last_grade}→{signal.grade}, stars {last_stars}→{signal.stars}"
                        else:
                            reason = f"weaker/same {direction_text}: skipping"
                    else:
                        # DIRECTION CHANGED - require high conviction to flip
                        if signal.grade >= 7 or signal.stars >= 3:
                            should_publish = True
                            reason = f"direction flip {last_direction}→{direction_text} with conviction"
                        else:
                            reason = f"direction flip rejected: not strong enough ({stars_display} [{signal.grade}])"

                    # Record signal to test session (if enabled)
                    if test_recorder and test_session_id:
                        try:
                            # Close previous signal if direction changed
                            if last_signal_id and last_direction and direction_text != last_direction:
                                if heat_tracker:
                                    try:
                                        await heat_tracker.close_signal(
                                            signal_id=last_signal_id,
                                            exit_price=data['price'],
                                            new_direction=direction_text
                                        )
                                    except Exception as e:
                                        print(f"[Murphy Test] Close signal error: {e}")

                            # Record new signal
                            signal_id = test_recorder.record_signal(
                                session_id=test_session_id,
                                symbol=symbol,
                                signal=signal,
                                price=data['price'],
                                bar_count=len(self.bar_history),  # Track bar count
                                passed_filter=should_publish,
                                filter_reason=None if should_publish else reason
                            )

                            # Track this signal ID for closing later
                            if should_publish:
                                last_signal_id = signal_id

                        except Exception as e:
                            print(f"[Murphy Test] Recording error: {e}")

                    if should_publish:
                        # Create 3-line update
                        murphy_update = {
                            'type': 'murphy_live',
                            'symbol': symbol,
                            'line1': f"MURPHY LIVE | Direction: {signal.direction} {direction_text} | Strength: {strength} {stars_display}",
                            'line2': f"Grade: [{signal.grade}] | Confidence: {signal.confidence:.2f} | Price: ${data['price']:.2f}",
                            'line3': f"Signal: {signal.interpretation[:60]}..."
                        }

                        # Update state tracking
                        last_direction = direction_text
                        last_grade = signal.grade
                        last_stars = signal.stars
                        last_published_signal = signal

                        # Publish to event bus
                        print(f"[Murphy Live] ✓ PUBLISH: {reason}")
                        await event_bus.publish(symbol, murphy_update)
                    else:
                        print(f"[Murphy Live] ✗ SKIP: {reason}")

                except Exception as e:
                    print(f"[Murphy Live] Error: {e}")
                    import traceback
                    traceback.print_exc()

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            print(f"[Murphy Live] Stopped for {symbol}")

    async def _execute_murphy(self, message: str, symbol: str) -> Optional[str]:
        """Execute Murphy classifier command - DIRECT EXECUTION."""
        # Get market data for current price
        data = self.executor.market_data.get(symbol)
        if not data:
            return f"⚠️ No market data available for {symbol}"

        # Parse optional price from message (e.g., "murphy 0.66")
        parts = message.strip().split()
        structure_price = float(parts[1]) if len(parts) > 1 and parts[1].replace('.', '').isdigit() else data['price']

        # Prepare bar data from history
        bar_count = len(self.bar_history) if self.bar_history else 0
        print(f"[Murphy] Analyzing {bar_count} bars for {symbol} @ ${structure_price:.2f}")

        if not self.bar_history or len(self.bar_history) < 20:
            return f"⚠️ Insufficient bar data for Murphy analysis (need at least 20 bars, have {bar_count})"

        try:
            # Import Murphy directly
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from murphy_classifier_v2 import MurphyClassifier, Bar

            # Convert bars to Murphy Bar objects
            bars = []
            for idx, bar_data in enumerate(self.bar_history[-100:]):
                bars.append(Bar(
                    timestamp=bar_data.get('timestamp', ''),
                    open=bar_data.get('open', 0),
                    high=bar_data.get('high', 0),
                    low=bar_data.get('low', 0),
                    close=bar_data.get('close', 0),
                    volume=int(bar_data.get('volume', 0)),
                    index=idx
                ))

            # Run Murphy classification directly
            print(f"[Murphy] Running classification on {len(bars)} bars...")
            murphy = MurphyClassifier()

            signal = murphy.classify(
                bars=bars,
                signal_index=len(bars) - 1,
                structure_age_bars=10,
                level_price=structure_price
            )

            label = murphy.format_label(signal)
            print(f"[Murphy] Result: {label} - {signal.interpretation[:50]}...")

            result = (
                f"🔍 Murphy Analysis - {symbol} @ ${structure_price:.2f}\n\n"
                f"Direction: {signal.direction}\n"
                f"Rating: {label}\n"
                f"Confidence: {signal.confidence:.2f}\n\n"
                f"📊 {signal.interpretation}\n"
            )

            # Add V2 enhancements if present
            enhancements = []
            if signal.has_liquidity_sweep:
                enhancements.append("  • Liquidity Sweep: Yes")
            if signal.rejection_type:
                enhancements.append(f"  • Rejection: {signal.rejection_type}")
            if signal.pattern:
                enhancements.append(f"  • Pattern: {signal.pattern}")
            if signal.fvg_momentum:
                enhancements.append(f"  • FVG: {signal.fvg_momentum}")

            if enhancements:
                result += "\n✨ V2 Features:\n" + "\n".join(enhancements)

            return result

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[Murphy] ERROR: {error_detail}")
            return f"❌ Error running Murphy: {str(e)}"

    async def _start_momo_live(self, symbol: str) -> FastResponse:
        """Start live Momo momentum ticker - updates every second via event bus."""
        import asyncio
        from event_bus import event_bus

        # Start background task
        asyncio.create_task(self._momo_live_worker(symbol))

        return FastResponse(
            text=(
                f"✓ Momo Live started for {symbol}\n\n"
                f"🚀 Analyzing momentum across 7 timeframes every second...\n\n"
                f"⏱️  Note: Momo needs ~50 bars to warm up before producing signals.\n"
                f"Signals will appear in the purple widget above the chart when ready.\n\n"
                f"Features:\n"
                f"  • Multi-timeframe alignment (YEST/PRE/OPEN/1H/15M/5M/1M)\n"
                f"  • VWAP positioning (value zones)\n"
                f"  • Leg detection (wave analysis)\n"
                f"  • Time-of-day patterns\n\n"
                f"Type 'momo stop' to end."
            ),
            matched_pattern="momo_live"
        )

    async def _momo_live_worker(self, symbol: str):
        """Background worker that publishes Momo momentum updates every second."""
        import asyncio
        from event_bus import event_bus

        print(f"[Momo Live] Started for {symbol}")

        # State tracking for signal persistence
        last_published_signal = None
        last_action = None
        last_stars = 0

        try:
            while True:
                # Get current market data
                data = self.executor.market_data.get(symbol)
                if not data:
                    await asyncio.sleep(1)
                    continue

                bar_count = len(self.bar_history) if self.bar_history else 0

                # Need at least 50 bars for Momo
                if bar_count < 50:
                    await asyncio.sleep(1)
                    continue

                try:
                    # Import Momo Advanced
                    import sys
                    import os
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                    from momo_advanced import MomoAdvanced
                    from murphy_classifier_v2 import Bar

                    # Convert bars to Bar objects
                    bars = []
                    for idx, bar_data in enumerate(self.bar_history[-100:]):
                        bars.append(Bar(
                            timestamp=bar_data.get('timestamp', ''),
                            open=bar_data.get('open', 0),
                            high=bar_data.get('high', 0),
                            low=bar_data.get('low', 0),
                            close=bar_data.get('close', 0),
                            volume=int(bar_data.get('volume', 0)),
                            index=idx
                        ))

                    # Get yesterday's close (use first bar as proxy if not available)
                    yesterday_close = bars[0].close if bars else None

                    # Run Momo classification
                    momo = MomoAdvanced()
                    signal = momo.classify(
                        bars=bars,
                        signal_index=len(bars) - 1,
                        yesterday_close=yesterday_close
                    )

                    # Determine if we should publish (signal changed)
                    direction_text = "BULLISH" if signal.direction == "↑" else "BEARISH" if signal.direction == "↓" else "NEUTRAL"
                    action = signal.action
                    stars = signal.stars

                    should_publish = False
                    reason = ""

                    # Publish if action changed
                    if action != last_action:
                        should_publish = True
                        reason = f"Action changed: {last_action} → {action}"

                    # Publish if stars changed
                    elif stars != last_stars:
                        should_publish = True
                        reason = f"Stars changed: {last_stars} → {stars}"

                    # Publish if no signal published yet
                    elif last_published_signal is None:
                        should_publish = True
                        reason = "Initial signal"

                    if should_publish:
                        # Format line1: Direction + Action
                        arrow = signal.direction
                        line1 = f"{arrow} {direction_text} | {action}"

                        # Format line2: Stars + Confidence + Price
                        stars_str = "★" * signal.stars
                        conf_pct = int(signal.confidence * 100)
                        line2 = f"Stars: {stars_str} ({signal.stars}/7) | Confidence: {conf_pct}% | Price: ${data['price']:.2f}"

                        # Format line3: VWAP + Leg + Time
                        vwap_zone = signal.vwap_context.zone
                        vwap_dist = signal.vwap_context.distance_pct
                        current_leg = signal.leg_context.current_leg
                        next_leg = current_leg + 1
                        next_leg_prob = int(signal.leg_context.next_leg_probability * 100)
                        time_period = signal.time_period.period

                        line3 = f"VWAP: {vwap_zone} ({vwap_dist:+.1f}%) | Leg: {current_leg} → {next_leg} ({next_leg_prob}%) | Time: {time_period}"

                        # Create 3-line update
                        momo_update = {
                            'type': 'momo_live',
                            'symbol': symbol,
                            'line1': line1,
                            'line2': line2,
                            'line3': line3
                        }

                        # Update state tracking
                        last_action = action
                        last_stars = stars
                        last_published_signal = momo_update

                        print(f"[Momo Live] ✓ Publishing: {line1[:60]}... | {reason}")
                        await event_bus.publish(symbol, momo_update)
                    else:
                        print(f"[Momo Live] ✗ SKIP: No significant change")

                except Exception as e:
                    print(f"[Momo Live] Error: {e}")
                    import traceback
                    traceback.print_exc()

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            print(f"[Momo Live] Stopped for {symbol}")

    async def _execute_momo(self, message: str, symbol: str) -> Optional[str]:
        """Execute Momo momentum classifier command - DIRECT EXECUTION."""
        # Get market data for current price
        data = self.executor.market_data.get(symbol)
        if not data:
            return f"⚠️ No market data available for {symbol}"

        # Prepare bar data from history
        bar_count = len(self.bar_history) if self.bar_history else 0
        print(f"[Momo] Analyzing {bar_count} bars for {symbol} @ ${data['price']:.2f}")

        if not self.bar_history or len(self.bar_history) < 50:
            return f"⚠️ Insufficient bar data for Momo analysis (need at least 50 bars, have {bar_count})"

        try:
            # Import Momo Advanced
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from momo_advanced import MomoAdvanced
            from murphy_classifier_v2 import Bar

            # Convert bars to Bar objects
            bars = []
            for idx, bar_data in enumerate(self.bar_history[-100:]):
                bars.append(Bar(
                    timestamp=bar_data.get('timestamp', ''),
                    open=bar_data.get('open', 0),
                    high=bar_data.get('high', 0),
                    low=bar_data.get('low', 0),
                    close=bar_data.get('close', 0),
                    volume=int(bar_data.get('volume', 0)),
                    index=idx
                ))

            # Get yesterday's close
            yesterday_close = bars[0].close if bars else None

            # Run Momo classification
            print(f"[Momo] Running classification on {len(bars)} bars...")
            momo = MomoAdvanced()

            signal = momo.classify(
                bars=bars,
                signal_index=len(bars) - 1,
                yesterday_close=yesterday_close
            )

            # Format result
            stars_str = "★" * signal.stars
            conf_pct = int(signal.confidence * 100)

            result = (
                f"🚀 Momo Analysis - {symbol} @ ${data['price']:.2f}\n\n"
                f"Direction: {signal.direction}\n"
                f"Stars: {stars_str} ({signal.stars}/7 alignment)\n"
                f"Confidence: {conf_pct}%\n"
                f"Action: {signal.action}\n\n"
                f"📊 VWAP Context:\n"
                f"  Zone: {signal.vwap_context.zone}\n"
                f"  Distance: {signal.vwap_context.distance_pct:+.1f}% from VWAP\n"
                f"  VWAP Price: ${signal.vwap:.2f}\n\n"
                f"🌊 Leg Analysis:\n"
                f"  Current Leg: {signal.leg_context.current_leg}\n"
                f"  Next Leg Probability: {signal.leg_context.next_leg_probability*100:.0f}%\n"
                f"  In Pullback Zone: {'Yes' if signal.leg_context.in_pullback_zone else 'No'}\n\n"
                f"⏰ Time Context:\n"
                f"  Period: {signal.time_period.period}\n"
                f"  Bias: {signal.time_period.bias}\n\n"
                f"💡 {signal.reason}"
            )

            return result

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"[Momo] ERROR: {error_detail}")
            return f"❌ Error running Momo: {str(e)}"

    def get_context(self, symbol: str) -> str:
        """
        Get context string to inject into LLM prompt.
        """
        data = self.executor.market_data.get(symbol)
        context_parts = []

        if data:
            context_parts.append(f"Latest {symbol} data:")
            context_parts.append(f"Price: ${data['price']:.2f} | High: ${data['high']:.2f} | Low: ${data['low']:.2f}")
            context_parts.append(f"Volume: {data['volume']:,}")

        # Get position from storage
        position = self.executor.position_storage.get_open_position(symbol)
        if position and data:
            current_price = data['price']
            realized_pnl, unrealized_pnl = self.executor.position_storage.calculate_pnl(position, current_price)
            context_parts.append(f"\nCurrent position: {position['side'].upper()} {position['quantity']} @ ${position['entry_price']:.2f}")
            context_parts.append(f"Unrealized P&L: ${unrealized_pnl:.2f}")
            if realized_pnl != 0:
                context_parts.append(f"Master P&L: ${realized_pnl + unrealized_pnl:.2f}")

        return "\n".join(context_parts) if context_parts else ""

    def reload_commands(self):
        """Reload commands from database (hot-reload)."""
        self.executor.reload_commands()


# Backwards compatibility - export original name
TradingClassifier = TradingClassifierV2
