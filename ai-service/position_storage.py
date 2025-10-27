"""
Position Storage Service
Handles persistence of positions to Supabase with P&L tracking and reversal logic.
"""

from datetime import datetime
from typing import Dict, Optional, Tuple
import sys
import os

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import supabase


class PositionStorage:
    """Manages position persistence with P&L tracking and reversal logic."""

    def __init__(self, user_id: str = None):
        # Use None for user_id to work without users table for now
        self.user_id = user_id

    def get_open_position(self, symbol: str) -> Optional[Dict]:
        """Get the current open position for a symbol."""
        try:
            query = supabase.table('trades').select('*').eq(
                'symbol', symbol
            ).eq(
                'status', 'open'
            )

            # Only filter by user_id if it's set
            if self.user_id:
                query = query.eq('user_id', self.user_id)

            result = query.order('entry_time', desc=True).limit(1).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error fetching open position: {e}")
            return None

    def calculate_pnl(self, position: Dict, current_price: float) -> Tuple[float, float]:
        """Calculate P&L for a position.

        Returns:
            Tuple[realized_pnl, unrealized_pnl]
        """
        entry_price = position['entry_price']
        quantity = position['quantity']
        side = position['side']

        # Calculate P&L based on side
        if side == 'long':
            pnl = (current_price - entry_price) * quantity
        else:  # short
            pnl = (entry_price - current_price) * quantity

        # Add any realized P&L from previous closes
        realized_pnl = position.get('realized_pnl', 0.0)

        return realized_pnl, pnl

    def record_position(
        self,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
        current_price: float
    ) -> Dict:
        """
        Record a new position with reversal logic.

        If user has opposite position open, close it first and calculate P&L.
        Then open new position.

        Returns:
            Dict with 'fast_response' and 'position' data
        """
        # Check for existing open position
        existing = self.get_open_position(symbol)

        realized_pnl = 0.0
        closed_position_msg = ""

        # Handle reversal if opposite side
        if existing and existing['side'] != side:
            # Close the existing position
            exit_pnl = self._close_position_internal(existing, current_price)
            realized_pnl = existing.get('realized_pnl', 0.0) + exit_pnl

            closed_position_msg = (
                f"✓ CLOSED {existing['side'].upper()} {existing['quantity']} {symbol} @ ${current_price:.2f}\n"
                f"  Entry: ${existing['entry_price']:.2f} | P&L: ${exit_pnl:+.2f}\n\n"
            )

        # Handle adding to existing position (same side)
        elif existing and existing['side'] == side:
            # Average in - calculate new average entry price
            old_qty = existing['quantity']
            old_entry = existing['entry_price']
            new_qty = old_qty + quantity
            new_entry = ((old_qty * old_entry) + (quantity * entry_price)) / new_qty

            # Update existing position
            supabase.table('trades').update({
                'quantity': new_qty,
                'entry_price': new_entry,
                'entry_value': new_qty * new_entry,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', existing['id']).execute()

            return {
                'fast_response': (
                    f"✓ ADDED TO {side.upper()} {symbol}\n"
                    f"  +{quantity} @ ${entry_price:.2f}\n"
                    f"  Total Position: {new_qty} @ ${new_entry:.2f} avg"
                ),
                'position': {
                    'id': existing['id'],
                    'symbol': symbol,
                    'side': side,
                    'quantity': new_qty,
                    'entry_price': new_entry,
                    'realized_pnl': existing.get('realized_pnl', 0.0)
                }
            }

        # Create new position
        entry_value = quantity * entry_price

        now = datetime.utcnow().isoformat()
        position_data = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_value': entry_value,
            'entry_time': now,
            'status': 'open',
            'realized_pnl': realized_pnl,  # Carry over from closed position
            'created_at': now,
            'updated_at': now,
        }

        # Only add user_id if it's set
        if self.user_id:
            position_data['user_id'] = self.user_id

        result = supabase.table('trades').insert(position_data).execute()

        new_position = result.data[0] if result.data else position_data

        fast_response = (
            f"{closed_position_msg}"
            f"✓ {side.upper()} {quantity} {symbol} @ ${entry_price:.2f}\n"
            f"  Position Value: ${entry_value:.2f}"
        )

        if realized_pnl != 0:
            fast_response += f"\n  Master P&L: ${realized_pnl:+.2f}"

        return {
            'fast_response': fast_response,
            'position': new_position
        }

    def _close_position_internal(self, position: Dict, exit_price: float) -> float:
        """Internal method to close a position and return P&L."""
        entry_price = position['entry_price']
        quantity = position['quantity']
        side = position['side']

        # Calculate P&L
        if side == 'long':
            pnl = (exit_price - entry_price) * quantity
        else:  # short
            pnl = (entry_price - exit_price) * quantity

        # Update position to closed
        supabase.table('trades').update({
            'status': 'closed',
            'exit_price': exit_price,
            'exit_time': datetime.utcnow().isoformat(),
            'realized_pnl': position.get('realized_pnl', 0.0) + pnl,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', position['id']).execute()

        return pnl

    def close_position(self, symbol: str, exit_price: float) -> Dict:
        """Close the open position for a symbol."""
        position = self.get_open_position(symbol)

        if not position:
            return {
                'fast_response': f"⚠️ No open position for {symbol}",
                'position': None
            }

        pnl = self._close_position_internal(position, exit_price)
        total_pnl = position.get('realized_pnl', 0.0) + pnl

        fast_response = (
            f"✓ CLOSED {position['side'].upper()} {position['quantity']} {symbol} @ ${exit_price:.2f}\n"
            f"  Entry: ${position['entry_price']:.2f} | P&L: ${pnl:+.2f}\n"
            f"  Master P&L: ${total_pnl:+.2f}"
        )

        return {
            'fast_response': fast_response,
            'position': None,
            'pnl': pnl,
            'total_pnl': total_pnl
        }

    def get_position_status(self, symbol: str, current_price: float) -> Dict:
        """Get current position status with P&L."""
        position = self.get_open_position(symbol)

        if not position:
            return {
                'fast_response': f"No open position for {symbol}",
                'position': None
            }

        realized_pnl, unrealized_pnl = self.calculate_pnl(position, current_price)
        total_pnl = realized_pnl + unrealized_pnl

        entry_price = position['entry_price']
        quantity = position['quantity']
        side = position['side']

        # Calculate percentage
        if side == 'long':
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        fast_response = (
            f"{side.upper()} {quantity} {symbol} @ ${entry_price:.2f}\n"
            f"Current: ${current_price:.2f} | P&L: ${unrealized_pnl:+.2f} ({pnl_pct:+.2f}%)"
        )

        if realized_pnl != 0:
            fast_response += f"\nMaster P&L: ${total_pnl:+.2f}"

        return {
            'fast_response': fast_response,
            'position': position,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': realized_pnl,
            'total_pnl': total_pnl,
            'pnl_pct': pnl_pct
        }

    def get_all_positions(self) -> list:
        """Get all open positions for the user."""
        try:
            result = supabase.table('trades').select('*').eq(
                'user_id', self.user_id
            ).eq(
                'status', 'open'
            ).order('entry_time', desc=True).execute()

            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching all positions: {e}")
            return []

    def get_session_pnl(self, symbol: str) -> float:
        """
        Get total realized P&L for a symbol from all closed trades.
        This is the cumulative profit/loss across all completed trades.
        """
        try:
            result = supabase.table('trades').select('realized_pnl').eq(
                'symbol', symbol
            ).eq(
                'status', 'closed'
            ).execute()

            if not result.data:
                return 0.0

            # Sum all realized P&L from closed trades
            total_pnl = sum(trade.get('realized_pnl', 0.0) for trade in result.data)
            return total_pnl

        except Exception as e:
            print(f"Error fetching session P&L: {e}")
            return 0.0
