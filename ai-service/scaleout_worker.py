"""
Scaleout Worker - Background Position Exit Manager
==================================================
Gradually scales out of positions over time with real-time progress updates.

Modes:
- Fast: 1-3 minutes (6-10 chunks, 10-30s between)
- Medium: 10-15 minutes (8-12 chunks, 60-120s between)
- Slow: 60 minutes (10-15 chunks, 240-480s between)
"""

import asyncio
import random
from datetime import datetime
from typing import Dict, Optional
from event_bus import event_bus
from position_storage import PositionStorage


class ScaleoutWorker:
    """Background worker for gradual position exits."""

    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.position_storage = PositionStorage(user_id=user_id)
        self.market_data = {}

    def update_market_data(self, symbol: str, bar: Dict):
        """Update latest market data."""
        self.market_data[symbol] = bar

    async def start_scaleout(
        self,
        symbol: str,
        speed: str,
        quantity: Optional[int] = None
    ) -> str:
        """
        Start a gradual scaleout process.

        Args:
            symbol: Symbol to scale out
            speed: 'fast' (1-3min), 'medium' (10-15min), 'slow' (60min)
            quantity: Total quantity to scale out (None = all)

        Returns:
            Initial confirmation message
        """
        position = self.position_storage.get_open_position(symbol)

        if not position:
            return "⚠️ No open position to scale out"

        current_qty = position['quantity']
        scaleout_qty = quantity if quantity else current_qty

        if scaleout_qty > current_qty:
            scaleout_qty = current_qty

        # Configure based on speed
        if speed == 'fast':
            num_chunks = random.randint(6, 10)
            delay_range = (10, 30)  # 10-30 seconds between chunks
            duration = "1-3 minutes"
        elif speed == 'medium':
            num_chunks = random.randint(8, 12)
            delay_range = (60, 120)  # 1-2 minutes between chunks
            duration = "10-15 minutes"
        else:  # slow
            num_chunks = random.randint(10, 15)
            delay_range = (240, 480)  # 4-8 minutes between chunks
            duration = "~60 minutes"

        # Create asyncio task
        task = asyncio.create_task(
            self._execute_scaleout(
                symbol=symbol,
                total_qty=scaleout_qty,
                num_chunks=num_chunks,
                delay_range=delay_range
            )
        )

        # Register task with event bus
        event_bus.register_task(symbol, "scaleout", task)

        return (
            f"🔄 SCALEOUT INITIATED\n"
            f"Mode: {speed.upper()} ({duration})\n"
            f"Total Quantity: {scaleout_qty:,}\n"
            f"Chunks: {num_chunks}\n"
            f"Entry: ${position['entry_price']:.2f}\n"
            f"💡 Progress updates will appear in chat automatically"
        )

    async def _execute_scaleout(
        self,
        symbol: str,
        total_qty: int,
        num_chunks: int,
        delay_range: tuple
    ):
        """Execute the scaleout process in background."""
        try:
            chunk_size = max(1, total_qty // num_chunks)
            remaining = total_qty
            chunk_num = 0
            total_pnl = 0.0

            await event_bus.publish(symbol, {
                "type": "scaleout_start",
                "message": f"🔄 Starting scaleout: {total_qty:,} shares in {num_chunks} chunks",
                "data": {
                    "total_qty": total_qty,
                    "num_chunks": num_chunks,
                    "chunk_size": chunk_size
                }
            })

            while remaining > 0:
                chunk_num += 1

                # Get current position
                position = self.position_storage.get_open_position(symbol)
                if not position:
                    await event_bus.publish(symbol, {
                        "type": "scaleout_complete",
                        "message": "✓ SCALEOUT COMPLETE - Position fully closed",
                        "data": {"total_pnl": total_pnl}
                    })
                    break

                # Determine chunk size for this iteration
                if chunk_num == num_chunks:
                    # Last chunk - sell remaining
                    this_chunk = remaining
                else:
                    # Regular chunk
                    this_chunk = min(chunk_size, remaining)

                # Get current price
                market_data = self.market_data.get(symbol)
                if not market_data:
                    await event_bus.publish(symbol, {
                        "type": "scaleout_error",
                        "message": "⚠️ No market data - pausing scaleout",
                        "data": {}
                    })
                    await asyncio.sleep(30)
                    continue

                current_price = market_data.get('price', market_data.get('close'))

                # Calculate P&L for this chunk
                if position['side'] == 'long':
                    chunk_pnl = (current_price - position['entry_price']) * this_chunk
                else:
                    chunk_pnl = (position['entry_price'] - current_price) * this_chunk

                total_pnl += chunk_pnl

                # Update position
                new_qty = position['quantity'] - this_chunk
                realized_pnl = position.get('realized_pnl', 0.0) + chunk_pnl

                if new_qty > 0:
                    # Partial exit
                    from shared.database import supabase
                    supabase.table('trades').update({
                        'quantity': new_qty,
                        'realized_pnl': realized_pnl,
                        'updated_at': datetime.utcnow().isoformat()
                    }).eq('id', position['id']).execute()

                    remaining -= this_chunk

                    # Publish progress event
                    await event_bus.publish(symbol, {
                        "type": "scaleout_progress",
                        "message": (
                            f"✓ Chunk {chunk_num}/{num_chunks}: Sold {this_chunk:,} @ ${current_price:.2f}\n"
                            f"P&L: ${chunk_pnl:+.2f} | Remaining: {new_qty:,} | Total P&L: ${total_pnl:+.2f}"
                        ),
                        "data": {
                            "chunk_num": chunk_num,
                            "quantity": this_chunk,
                            "price": current_price,
                            "pnl": chunk_pnl,
                            "remaining_qty": new_qty,
                            "total_pnl": total_pnl
                        }
                    })
                else:
                    # Final exit
                    self.position_storage.close_position(symbol, current_price)
                    remaining = 0

                    await event_bus.publish(symbol, {
                        "type": "scaleout_complete",
                        "message": (
                            f"🎉 SCALEOUT COMPLETE\n"
                            f"Final Chunk: {this_chunk:,} @ ${current_price:.2f}\n"
                            f"Total P&L: ${total_pnl:+.2f}\n"
                            f"Position: FLAT"
                        ),
                        "data": {
                            "total_pnl": total_pnl,
                            "avg_exit_price": current_price
                        }
                    })
                    break

                # Wait before next chunk
                if remaining > 0:
                    delay = random.uniform(*delay_range)
                    await asyncio.sleep(delay)

        except asyncio.CancelledError:
            await event_bus.publish(symbol, {
                "type": "scaleout_cancelled",
                "message": "⚠️ Scaleout cancelled by user",
                "data": {}
            })
            raise

        except Exception as e:
            await event_bus.publish(symbol, {
                "type": "scaleout_error",
                "message": f"❌ Scaleout error: {str(e)}",
                "data": {"error": str(e)}
            })
            raise

    async def cancel_scaleout(self, symbol: str) -> str:
        """Cancel an active scaleout."""
        cancelled = event_bus.cancel_task(symbol, "scaleout")

        if cancelled:
            await event_bus.publish(symbol, {
                "type": "scaleout_cancelled",
                "message": "⚠️ Scaleout cancelled",
                "data": {}
            })
            return "✓ Scaleout cancelled"
        else:
            return "⚠️ No active scaleout to cancel"

    def get_scaleout_status(self, symbol: str) -> Optional[Dict]:
        """Check if scaleout is active."""
        task = event_bus.get_task(symbol, "scaleout")
        if task and not task.done():
            return {
                "active": True,
                "task": task
            }
        return None
