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
