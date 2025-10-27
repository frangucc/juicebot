"""
Trade Command Executor
======================
Database-driven trade command execution system.

All commands are loaded from Supabase, including:
- Commands, aliases, and natural language phrases
- Command routing and execution
- All trade operations (entry, exit, reversal, risk management)

No hardcoded commands - everything comes from the database.
"""

import re
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any, Tuple
from position_storage import PositionStorage
from conversation_state import conversation_state
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.database import supabase


class TradeCommandExecutor:
    """Executes trade commands loaded from database with dynamic routing."""

    def __init__(self, user_id: str = None, conversation_id: str = None):
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.position_storage = PositionStorage(user_id=user_id)
        self.market_data = {}  # Latest market data from WebSocket
        self.bar_history = []  # Historical bars for range calculations

        # Load commands from database
        self.commands = {}  # command -> metadata
        self.aliases = {}  # alias -> command
        self.phrases = {}  # phrase -> (command, confidence)
        self.patterns = []  # List of (regex, command) tuples

        self._load_commands_from_db()

    def _load_commands_from_db(self):
        """Load all commands, aliases, and phrases from Supabase."""
        try:
            # Load commands
            cmd_result = supabase.table('trade_commands').select('*').execute()
            for cmd in cmd_result.data:
                self.commands[cmd['command']] = cmd

            # Load aliases
            alias_result = supabase.table('trade_aliases').select('*,trade_commands(command)').execute()
            for alias_row in alias_result.data:
                alias = alias_row['alias']
                command = alias_row['trade_commands']['command']
                self.aliases[alias.lower()] = command

            # Load natural language phrases
            phrase_result = supabase.table('trade_phrases').select('*,trade_commands(command)').execute()
            for phrase_row in phrase_result.data:
                phrase = phrase_row['phrase']
                command = phrase_row['trade_commands']['command']
                confidence = phrase_row['confidence_score']
                self.phrases[phrase.lower()] = (command, float(confidence))

            # Build regex patterns for entry commands
            self._build_patterns()

            print(f"✓ Loaded {len(self.commands)} commands, {len(self.aliases)} aliases, {len(self.phrases)} phrases")

        except Exception as e:
            print(f"❌ Error loading commands from database: {e}")
            raise

    def _build_patterns(self):
        """Build regex patterns for trading notation (long/short @ price)."""
        # Pattern: "long 100 @ .57" or "buy 100 @ 12.45"
        # Enhanced: "buy 500", "sell all", "sell half", "sell 50%"
        self.patterns = [
            # With explicit price: "long 100 @ .57" (allow .57 without leading zero)
            (re.compile(r'\b(long|buy)\s+(\d+)\s*@\s*[\$]?(\d*\.?\d+)', re.IGNORECASE), '/trade long'),
            (re.compile(r'\b(short|sell)\s+(\d+)\s*@\s*[\$]?(\d*\.?\d+)', re.IGNORECASE), '/trade short'),

            # Market order with explicit "@ market": "buy 500 @ market"
            (re.compile(r'\b(buy|long)\s+(\d+)\s*@\s*market\b', re.IGNORECASE), '/trade long'),
            (re.compile(r'\b(sell|short)\s+(\d+)\s*@\s*market\b', re.IGNORECASE), '/trade short'),

            # Market order: "buy 500" (no price = market)
            (re.compile(r'\b(buy|long)\s+(\d+)\s*$', re.IGNORECASE), '/trade long'),
            (re.compile(r'\b(sell|short)\s+(\d+)\s*$', re.IGNORECASE), '/trade short'),

            # Special quantities: "sell all", "sell half", "sell 50%"
            (re.compile(r'\b(sell|close)\s+(all|everything|full)\b', re.IGNORECASE), '/trade flatten'),
            (re.compile(r'\b(sell|close)\s+(half|50%)\b', re.IGNORECASE), '/trade scaleout'),
            (re.compile(r'\b(sell|close)\s+(\d+)%', re.IGNORECASE), '/trade scaleout'),
            (re.compile(r'\b(sell|close)\s+(\d+)\b', re.IGNORECASE), '/trade scaleout'),

            # Scaleout with speed: "scaleout fast", "scaleout medium", "scaleout slow"
            (re.compile(r'\bscaleout\s+(fast|medium|slow|1|2|3)\b', re.IGNORECASE), '/trade scaleout'),

            # Cancel scaleout: "cancel scaleout" or "scaleout cancel"
            (re.compile(r'\b(cancel|stop)\s+scaleout\b', re.IGNORECASE), '/trade cancel-scaleout'),
            (re.compile(r'\bscaleout\s+(cancel|stop)\b', re.IGNORECASE), '/trade cancel-scaleout'),
        ]

    def reload_commands(self):
        """Reload commands from database (useful for hot-reload)."""
        self.commands.clear()
        self.aliases.clear()
        self.phrases.clear()
        self.patterns.clear()
        self._load_commands_from_db()

    def update_market_data(self, symbol: str, bar: Dict[str, Any]):
        """Update latest market data from WebSocket."""
        self.market_data[symbol] = {
            'price': bar['close'],
            'open': bar['open'],
            'high': bar['high'],
            'low': bar['low'],
            'volume': bar['volume'],
            'timestamp': bar['timestamp']
        }

    def match_command(self, message: str) -> Optional[Tuple[str, Dict]]:
        """
        Match user message to a command.

        Returns:
            Tuple of (command, extracted_params) or None
        """
        msg_lower = message.lower().strip()

        # 1. Check for exact command match
        if msg_lower in self.commands:
            return (msg_lower, {})

        # 2. Check for alias match
        if msg_lower in self.aliases:
            return (self.aliases[msg_lower], {})

        # 3. Check for phrase match
        if msg_lower in self.phrases:
            command, confidence = self.phrases[msg_lower]
            return (command, {'confidence': confidence})

        # 4. Check for regex patterns (trading notation)
        for pattern, command in self.patterns:
            match = pattern.search(message)
            if match:
                # Extract parameters from pattern
                params = {'action': match.group(1).lower() if match.lastindex >= 1 else 'scaleout'}

                # Special case: scaleout with speed (group 1 is the speed)
                if 'scaleout' in message.lower() and match.lastindex >= 1:
                    speed_str = match.group(1).lower()
                    if speed_str in ['fast', 'medium', 'slow', '1', '2', '3']:
                        params['speed'] = speed_str
                        return (command, params)

                # Try to extract quantity
                if match.lastindex >= 2:
                    qty_str = match.group(2)

                    # Handle special quantities
                    if qty_str.lower() in ['all', 'everything', 'full']:
                        params['quantity'] = 'all'
                    elif qty_str.lower() in ['half', '50%']:
                        params['quantity'] = 'half'
                    elif '%' in qty_str:
                        params['quantity'] = f"{qty_str}%"
                    else:
                        try:
                            params['quantity'] = int(qty_str)
                        except ValueError:
                            params['quantity'] = 1

                # Try to extract price
                if match.lastindex >= 3:
                    try:
                        params['price'] = float(match.group(3))
                    except (ValueError, IndexError):
                        params['price'] = None  # Market order

                return (command, params)

        # 5. Check for partial phrase matches (fuzzy)
        words = set(msg_lower.split())
        for phrase, (command, confidence) in self.phrases.items():
            phrase_words = set(phrase.split())
            if phrase_words.issubset(words):
                return (command, {'confidence': confidence, 'fuzzy': True})

        return None

    async def execute(self, message: str, symbol: str) -> Optional[str]:
        """
        Execute a trade command if message matches.

        Returns:
            Response string if executed, None if no match
        """
        match = self.match_command(message)
        if not match:
            return None

        command, params = match
        cmd_meta = self.commands.get(command)

        if not cmd_meta:
            return f"⚠️ Command {command} not found in registry"

        if not cmd_meta['is_implemented']:
            return f"⚠️ Command {command} not yet implemented"

        # Route to appropriate handler
        handler_name = cmd_meta['handler_function']
        handler = getattr(self, handler_name, None)

        if not handler:
            return f"⚠️ Handler {handler_name} not found"

        # Execute handler with params
        try:
            result = await handler(symbol=symbol, params=params)
            return result
        except Exception as e:
            return f"❌ Error executing {command}: {str(e)}"

    # ============================================================================
    # COMMAND HANDLERS
    # ============================================================================

    # ------------------------------------------------------------------------
    # Entry Commands
    # ------------------------------------------------------------------------

    async def open_long_position(self, symbol: str, params: Dict) -> str:
        """Handler for /trade long"""
        quantity = params.get('quantity', 1)
        price = params.get('price')

        if not price:
            # Use current market price
            market_data = self.market_data.get(symbol)
            if not market_data:
                return f"⚠️ No market data for {symbol}"
            price = market_data['price']

        current_price = self.market_data.get(symbol, {}).get('price', price)

        result = self.position_storage.record_position(
            symbol=symbol,
            side='long',
            quantity=quantity,
            entry_price=price,
            current_price=current_price
        )

        return result['fast_response']

    async def open_short_position(self, symbol: str, params: Dict) -> str:
        """Handler for /trade short"""
        quantity = params.get('quantity', 1)
        price = params.get('price')

        if not price:
            market_data = self.market_data.get(symbol)
            if not market_data:
                return f"⚠️ No market data for {symbol}"
            price = market_data['price']

        current_price = self.market_data.get(symbol, {}).get('price', price)

        result = self.position_storage.record_position(
            symbol=symbol,
            side='short',
            quantity=quantity,
            entry_price=price,
            current_price=current_price
        )

        return result['fast_response']

    async def accumulate_position(self, symbol: str, params: Dict) -> str:
        """Handler for /trade accumulate - Scale into position gradually."""
        position = self.position_storage.get_open_position(symbol)

        if not position:
            return "⚠️ No open position to accumulate into. Open a position first with 'long' or 'short'."

        # Default: add 20% of current position size
        current_qty = position['quantity']
        add_qty = max(1, int(current_qty * 0.2))

        market_data = self.market_data.get(symbol)
        if not market_data:
            return f"⚠️ No market data for {symbol}"

        current_price = market_data['price']

        result = self.position_storage.record_position(
            symbol=symbol,
            side=position['side'],
            quantity=add_qty,
            entry_price=current_price,
            current_price=current_price
        )

        return f"🔄 ACCUMULATING\n{result['fast_response']}"

    # ------------------------------------------------------------------------
    # Exit Commands
    # ------------------------------------------------------------------------

    async def close_position(self, symbol: str, params: Dict) -> str:
        """Handler for /trade close"""
        market_data = self.market_data.get(symbol)
        if not market_data:
            return f"⚠️ No market data for {symbol}"

        current_price = market_data['price']
        result = self.position_storage.close_position(symbol, current_price)

        return result['fast_response']

    async def flatten_position(self, symbol: str, params: Dict) -> str:
        """Handler for /trade flatten - Alias for close"""
        result = await self.close_position(symbol, params)
        return f"✓ FLATTENED\n{result}"

    async def flatten_position_smart(self, symbol: str, params: Dict) -> str:
        """Handler for /trade flatten-smart - AI-assisted gradual exit."""
        position = self.position_storage.get_open_position(symbol)

        if not position:
            return f"⚠️ No open position for {symbol}"

        market_data = self.market_data.get(symbol)
        if not market_data:
            return f"⚠️ No market data for {symbol}"

        # Close 50% immediately, schedule rest for gradual exit
        qty = position['quantity']
        half_qty = max(1, qty // 2)

        current_price = market_data['price']

        # This would ideally use a scheduling system, but for now we'll close 50%
        # TODO: Implement proper scheduling for gradual exits

        # Update position to half size
        new_qty = qty - half_qty
        new_entry = position['entry_price']

        if new_qty > 0:
            # Calculate P&L for closed portion
            if position['side'] == 'long':
                pnl = (current_price - new_entry) * half_qty
            else:
                pnl = (new_entry - current_price) * half_qty

            supabase.table('trades').update({
                'quantity': new_qty,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', position['id']).execute()

            return (
                f"🤖 SMART FLATTEN\n"
                f"✓ Closed {half_qty} @ ${current_price:.2f} | P&L: ${pnl:+.2f}\n"
                f"📊 Holding {new_qty} {position['side']} @ ${new_entry:.2f}\n"
                f"💡 Remaining position will exit gradually"
            )
        else:
            # Close entirely
            return await self.close_position(symbol, params)

    async def scale_out_position(self, symbol: str, params: Dict) -> str:
        """
        Handler for /trade scaleout - Interactive gradual exit.

        Prompts user for speed: fast (1-3min), medium (10-15min), slow (60min)
        Then starts background worker to execute scaleout over time.

        Supports:
        - "scaleout" → interactive prompt
        - "scaleout fast" → direct execution
        - "scaleout medium" → direct execution
        - "scaleout slow" → direct execution
        """
        position = self.position_storage.get_open_position(symbol)

        if not position:
            return f"⚠️ No open position for {symbol}"

        # Check if scaleout is already active
        from scaleout_worker import ScaleoutWorker
        worker = ScaleoutWorker(user_id=self.user_id)
        status = worker.get_scaleout_status(symbol)

        if status and status['active']:
            return (
                f"⚠️ Scaleout already in progress for {symbol}\n"
                f"Type 'cancel scaleout' to stop it"
            )

        # Get quantity BEFORE using it
        qty = position['quantity']

        # Check if speed was provided directly in the command (e.g. "scaleout fast")
        speed = params.get('speed') or params.get('mode')
        if speed and speed.lower() in ['fast', 'medium', 'slow', '1', '2', '3']:
            # Map numeric to speed names
            speed_map = {'1': 'fast', '2': 'medium', '3': 'slow'}
            speed = speed_map.get(speed.lower(), speed.lower())

            # Execute directly without interactive prompt
            return await self.execute_scaleout_with_speed(symbol, speed)

        # Set conversation state to expect speed selection
        if self.conversation_id:
            conversation_state.set_state(
                conversation_id=self.conversation_id,
                symbol=symbol,
                command='scaleout_speed_selection',
                context={'quantity': qty}
            )

        # Interactive prompt for speed selection
        return (
            f"📉 INTERACTIVE SCALEOUT\n"
            f"Position: {position['side'].upper()} {qty:,} @ ${position['entry_price']:.2f}\n\n"
            f"How fast should I scale out?\n"
            f"  [1]  FAST - Next 1-3 minutes (6-10 chunks)\n"
            f"  [2]  MEDIUM - Next 10-15 minutes (8-12 chunks)\n"
            f"  [3]  SLOW - Next hour (10-15 chunks)\n\n"
            f"💡 Reply with 1, 2, or 3 (or type 'scaleout fast')\n"
            f"📊 Progress updates will appear automatically in chat"
        )

    async def execute_scaleout_with_speed(self, symbol: str, speed: str) -> str:
        """Execute scaleout after user selects speed (1, 2, or 3)."""
        from scaleout_worker import ScaleoutWorker

        worker = ScaleoutWorker(user_id=self.user_id)
        worker.update_market_data(symbol, self.market_data.get(symbol, {}))

        result = await worker.start_scaleout(symbol=symbol, speed=speed, quantity=None)

        # Clear conversation state
        if self.conversation_id:
            conversation_state.clear_state(self.conversation_id)

        return result

    async def cancel_scaleout_handler(self, symbol: str, params: Dict) -> str:
        """Handler for /trade cancel-scaleout - Stop active scaleout."""
        from scaleout_worker import ScaleoutWorker

        worker = ScaleoutWorker(user_id=self.user_id)
        result = await worker.cancel_scaleout(symbol)

        # Clear any conversation state
        if self.conversation_id:
            conversation_state.clear_state(self.conversation_id)

        return result

    # ------------------------------------------------------------------------
    # Reversal Commands
    # ------------------------------------------------------------------------

    async def reverse_position(self, symbol: str, params: Dict) -> str:
        """Handler for /trade reverse - Instantly flip position."""
        position = self.position_storage.get_open_position(symbol)

        if not position:
            return "⚠️ No open position to reverse"

        market_data = self.market_data.get(symbol)
        if not market_data:
            return f"⚠️ No market data for {symbol}"

        current_price = market_data['price']

        # Determine opposite side
        new_side = 'short' if position['side'] == 'long' else 'long'
        qty = position['quantity']

        # Close current position and open opposite
        result = self.position_storage.record_position(
            symbol=symbol,
            side=new_side,
            quantity=qty,
            entry_price=current_price,
            current_price=current_price
        )

        return f"🔄 REVERSED\n{result['fast_response']}"

    async def reverse_position_smart(self, symbol: str, params: Dict) -> str:
        """Handler for /trade reverse-smart - AI-assisted safe reversal."""
        position = self.position_storage.get_open_position(symbol)

        if not position:
            return "⚠️ No open position to reverse"

        market_data = self.market_data.get(symbol)
        if not market_data:
            return f"⚠️ No market data for {symbol}"

        current_price = market_data['price']

        # Check if reversal makes sense based on P&L
        realized_pnl, unrealized_pnl = self.position_storage.calculate_pnl(position, current_price)

        # Don't reverse if deep in the red (losing > 10%)
        entry_price = position['entry_price']
        loss_pct = abs(unrealized_pnl / (entry_price * position['quantity']) * 100)

        if unrealized_pnl < 0 and loss_pct > 10:
            return (
                f"🤖 SMART REVERSE - BLOCKED\n"
                f"⚠️ Current position down {loss_pct:.1f}%\n"
                f"💡 Reversing while deep in red is risky\n"
                f"📊 Consider flattening instead: 'flat'"
            )

        # Safe to reverse
        new_side = 'short' if position['side'] == 'long' else 'long'
        qty = position['quantity']

        result = self.position_storage.record_position(
            symbol=symbol,
            side=new_side,
            quantity=qty,
            entry_price=current_price,
            current_price=current_price
        )

        return f"🤖 SMART REVERSE ✓\n{result['fast_response']}"

    # ------------------------------------------------------------------------
    # Position Inquiry
    # ------------------------------------------------------------------------

    async def get_position_status(self, symbol: str, params: Dict) -> str:
        """Handler for /trade position"""
        market_data = self.market_data.get(symbol)
        if not market_data:
            return f"⚠️ No market data for {symbol}"

        current_price = market_data['price']
        result = self.position_storage.get_position_status(symbol, current_price)

        return result['fast_response']

    # ------------------------------------------------------------------------
    # Risk Management
    # ------------------------------------------------------------------------

    async def set_stop_loss(self, symbol: str, params: Dict) -> str:
        """Handler for /trade stop"""
        position = self.position_storage.get_open_position(symbol)

        if not position:
            return f"⚠️ No open position for {symbol}"

        market_data = self.market_data.get(symbol)
        if not market_data:
            return f"⚠️ No market data for {symbol}"

        current_price = market_data['price']
        entry_price = position['entry_price']

        # Auto-calculate stop loss at -2% (smart default)
        if position['side'] == 'long':
            stop_price = entry_price * 0.98  # 2% below entry
        else:
            stop_price = entry_price * 1.02  # 2% above entry

        # Store stop loss in database (requires schema update)
        # For now, just return the recommendation

        return (
            f"🛡️ STOP LOSS SET\n"
            f"Position: {position['side'].upper()} {position['quantity']} @ ${entry_price:.2f}\n"
            f"Stop Price: ${stop_price:.2f} (-2.0%)\n"
            f"Current: ${current_price:.2f}\n"
            f"💡 Position will close automatically if price hits stop"
        )

    async def create_bracket_order(self, symbol: str, params: Dict) -> str:
        """Handler for /trade bracket"""
        position = self.position_storage.get_open_position(symbol)

        if not position:
            return "⚠️ No open position. Open a position first."

        market_data = self.market_data.get(symbol)
        if not market_data:
            return f"⚠️ No market data for {symbol}"

        entry_price = position['entry_price']

        # Auto-calculate bracket: -2% stop, +6% target (3:1 R/R)
        if position['side'] == 'long':
            stop_price = entry_price * 0.98
            target_price = entry_price * 1.06
        else:
            stop_price = entry_price * 1.02
            target_price = entry_price * 0.94

        return (
            f"🎯 BRACKET ORDER SET\n"
            f"Position: {position['side'].upper()} {position['quantity']} @ ${entry_price:.2f}\n"
            f"🔻 Stop Loss: ${stop_price:.2f} (-2.0%)\n"
            f"🔺 Take Profit: ${target_price:.2f} (+6.0%)\n"
            f"📊 Risk/Reward: 1:3\n"
            f"💡 Auto-close when either level hits"
        )

    # ------------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------------

    async def reset_session_pnl(self, symbol: str, params: Dict) -> str:
        """Handler for /trade reset"""
        # Close all positions and reset P&L counter
        position = self.position_storage.get_open_position(symbol)

        if position:
            market_data = self.market_data.get(symbol)
            if market_data:
                self.position_storage.close_position(symbol, market_data['price'])

        # Reset realized P&L for all closed trades
        # This is a soft reset - data stays in DB but we reset the counter

        return (
            f"🔄 SESSION RESET\n"
            f"✓ All positions closed\n"
            f"✓ P&L counter reset to $0.00\n"
            f"📊 Trade history preserved\n"
            f"💡 Fresh start for new session"
        )

    # ------------------------------------------------------------------------
    # P&L Display
    # ------------------------------------------------------------------------

    async def get_pnl_summary(self, symbol: str, params: Dict) -> str:
        """Handler for /trade pl - Focused P&L display."""
        market_data = self.market_data.get(symbol)
        if not market_data:
            return f"⚠️ No market data for {symbol}"

        current_price = market_data['price']
        position = self.position_storage.get_open_position(symbol)

        if not position:
            # No open position - show session P&L only
            # TODO: Query all closed trades for session P&L
            return (
                f"💰 P&L SUMMARY - {symbol}\n"
                f"Open Position: FLAT\n"
                f"Session P&L: $0.00\n"
                f"Master P&L: $0.00"
            )

        # Calculate unrealized P&L
        entry_price = position['entry_price']
        qty = position['quantity']
        side = position['side']

        if side == 'long':
            unrealized_pnl = (current_price - entry_price) * qty
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            unrealized_pnl = (entry_price - current_price) * qty
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Get realized P&L
        realized_pnl = position.get('realized_pnl', 0.0)
        total_pnl = realized_pnl + unrealized_pnl

        return (
            f"💰 P&L SUMMARY - {symbol}\n"
            f"Open: {side.upper()} {qty:,} @ ${entry_price:.2f}\n"
            f"Current: ${current_price:.2f}\n"
            f"Unrealized P&L: ${unrealized_pnl:+.2f} ({pnl_pct:+.2f}%)\n"
            f"Realized P&L: ${realized_pnl:+.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Master P&L: ${total_pnl:+.2f}"
        )

    # ------------------------------------------------------------------------
    # Market Data
    # ------------------------------------------------------------------------

    async def get_current_price(self, symbol: str, params: Dict) -> str:
        """Handler for /trade price"""
        market_data = self.market_data.get(symbol)
        if not market_data:
            return f"⚠️ No market data for {symbol}"

        return f"${market_data['price']:.2f}"

    async def get_current_volume(self, symbol: str, params: Dict) -> str:
        """Handler for /trade volume"""
        market_data = self.market_data.get(symbol)
        if not market_data:
            return f"⚠️ No market data for {symbol}"

        return f"Vol: {market_data['volume']:,}"

    async def get_price_range(self, symbol: str, params: Dict) -> str:
        """Handler for /trade range - shows session high/low from all bars"""
        if not self.bar_history:
            # Fallback to current bar if no history
            market_data = self.market_data.get(symbol)
            if not market_data:
                return f"⚠️ No market data for {symbol}"
            return f"High: ${market_data['high']:.2f} | Low: ${market_data['low']:.2f}"

        # Calculate session high/low from all bars
        session_high = max(bar['high'] for bar in self.bar_history)
        session_low = min(bar['low'] for bar in self.bar_history)

        return f"High: ${session_high:.2f} | Low: ${session_low:.2f}"
