"""
Fast-path classifier for instant responses.

Detects reserved keywords and trading shorthand to bypass LLM calls.
"""

import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from position_storage import PositionStorage


@dataclass
class FastResponse:
    """Response from fast path."""
    text: str
    matched_pattern: str


class TradingClassifier:
    """
    Classifies user input to determine if it needs fast-path or LLM response.

    Fast-path patterns:
    - "last" / "price" / "current" → current price
    - "position" / "pos" → current position
    - "long 500 @ .53" → record long position
    - "short 100 @ 12.45" → record short position
    - "close" / "exit" → close position
    - "volume" / "vol" → current volume
    - "high" / "low" → today's high/low
    """

    # Reserved keywords that trigger fast path
    FAST_KEYWORDS = {
        'last', 'price', 'current', 'now',
        'position', 'pos', 'positions',
        'volume', 'vol',
        'high', 'low', 'range',
        'close', 'exit', 'sell',
    }

    # Trading notation patterns
    LONG_PATTERN = re.compile(r'\b(long|buy)\s+(\d+)\s*@\s*[\$]?(\d+\.?\d*)', re.IGNORECASE)
    SHORT_PATTERN = re.compile(r'\b(short|sell)\s+(\d+)\s*@\s*[\$]?(\d+\.?\d*)', re.IGNORECASE)
    CLOSE_PATTERN = re.compile(r'\b(close|exit|sell)\s+(all|position|pos)\b', re.IGNORECASE)

    def __init__(self, user_id: str = "default_user"):
        self.market_data = {}  # Store latest market data from WebSocket
        self.bar_history = []  # Store last 100 bars for analysis
        self.position_storage = PositionStorage(user_id=user_id)

    def update_market_data(self, symbol: str, bar: Dict[str, Any]):
        """Update market data from WebSocket."""
        self.market_data[symbol] = {
            'price': bar['close'],
            'open': bar['open'],
            'high': bar['high'],
            'low': bar['low'],
            'volume': bar['volume'],
            'timestamp': bar['timestamp']
        }

        # Store in history (keep last 100 bars)
        self.bar_history.append(bar)
        if len(self.bar_history) > 100:
            self.bar_history.pop(0)

    def classify(self, message: str, symbol: str) -> Optional[FastResponse]:
        """
        Classify message and return fast response if applicable.

        Returns:
            FastResponse if fast-path match, None if needs LLM
        """
        msg_lower = message.lower().strip()

        # Check for trading notation first (most specific)
        long_match = self.LONG_PATTERN.search(message)
        if long_match:
            action, qty, price = long_match.groups()
            qty = int(qty)
            price = float(price)
            current_price = self.market_data.get(symbol, {}).get('price', price)

            result = self.position_storage.record_position(
                symbol=symbol,
                side='long',
                quantity=qty,
                entry_price=price,
                current_price=current_price
            )
            return FastResponse(
                text=result['fast_response'],
                matched_pattern="long_notation"
            )

        short_match = self.SHORT_PATTERN.search(message)
        if short_match:
            action, qty, price = short_match.groups()
            qty = int(qty)
            price = float(price)
            current_price = self.market_data.get(symbol, {}).get('price', price)

            result = self.position_storage.record_position(
                symbol=symbol,
                side='short',
                quantity=qty,
                entry_price=price,
                current_price=current_price
            )
            return FastResponse(
                text=result['fast_response'],
                matched_pattern="short_notation"
            )

        close_match = self.CLOSE_PATTERN.search(message)
        if close_match:
            current_price = self.market_data.get(symbol, {}).get('price')
            if current_price:
                result = self.position_storage.close_position(symbol, current_price)
                return FastResponse(
                    text=result['fast_response'],
                    matched_pattern="close_position"
                )

        # Check for reserved keywords
        words = set(msg_lower.split())
        if words & self.FAST_KEYWORDS:
            data = self.market_data.get(symbol)

            if not data:
                return FastResponse(
                    text=f"⚠️ No live data for {symbol} yet",
                    matched_pattern="no_data"
                )

            # Price queries
            if any(w in words for w in ['last', 'price', 'current', 'now']):
                return FastResponse(
                    text=f"${data['price']:.2f}",
                    matched_pattern="last_price"
                )

            # Position query
            if any(w in words for w in ['position', 'pos', 'positions']):
                current_price = data['price']
                result = self.position_storage.get_position_status(symbol, current_price)
                return FastResponse(
                    text=result['fast_response'],
                    matched_pattern="position_status"
                )

            # Volume query
            if any(w in words for w in ['volume', 'vol']):
                vol = data['volume']
                return FastResponse(
                    text=f"Vol: {vol:,}",
                    matched_pattern="volume"
                )

            # High/low query
            if 'high' in words or 'low' in words:
                return FastResponse(
                    text=f"High: ${data['high']:.2f} | Low: ${data['low']:.2f}",
                    matched_pattern="high_low"
                )

        # No fast-path match, needs LLM
        return None

    def _calculate_pnl(self, current_price: float) -> float:
        """Calculate P&L for current position."""
        if not self.position:
            return 0.0

        entry_value = self.position['entry_value']
        current_value = self.position['quantity'] * current_price

        if self.position['side'] == 'long':
            return current_value - entry_value
        else:  # short
            return entry_value - current_value

    def get_context(self, symbol: str) -> str:
        """
        Get context string to inject into LLM prompt.
        This gives the LLM access to latest market data without tool calls.
        """
        data = self.market_data.get(symbol)
        context_parts = []

        if data:
            context_parts.append(f"Latest {symbol} data:")
            context_parts.append(f"Price: ${data['price']:.2f} | High: ${data['high']:.2f} | Low: ${data['low']:.2f}")
            context_parts.append(f"Volume: {data['volume']:,}")

        # Get position from storage
        position = self.position_storage.get_open_position(symbol)
        if position and data:
            current_price = data['price']
            realized_pnl, unrealized_pnl = self.position_storage.calculate_pnl(position, current_price)
            context_parts.append(f"\nCurrent position: {position['side'].upper()} {position['quantity']} @ ${position['entry_price']:.2f}")
            context_parts.append(f"Unrealized P&L: ${unrealized_pnl:.2f}")
            if realized_pnl != 0:
                context_parts.append(f"Master P&L: ${realized_pnl + unrealized_pnl:.2f}")

        return "\n".join(context_parts) if context_parts else ""
