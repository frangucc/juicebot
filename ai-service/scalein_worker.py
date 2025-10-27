"""
Scalein Worker - Background Position Entry Manager
==================================================
Gradually scales into positions over time with real-time progress updates.

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


class ScaleinWorker:
    """Background worker for gradual position entries."""

    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.position_storage = PositionStorage(user_id=user_id)
        self.market_data = {}

    def update_market_data(self, symbol: str, bar: Dict):
        """Update latest market data."""
        self.market_data[symbol] = bar

    async def start_scalein(
        self,
        symbol: str,
        side: str,
        speed: str,
        quantity: int
    ) -> str:
        """
        Start a gradual scalein process.

        Args:
            symbol: Symbol to scale into
            side: 'long' or 'short'
            speed: 'fast' (1-3min), 'medium' (10-15min), 'slow' (60min)
            quantity: Total quantity to scale in

        Returns:
            Initial confirmation message
        """
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

        # Get current price for reference
        market_data = self.market_data.get(symbol)
        current_price = market_data.get('price', market_data.get('close')) if market_data else None

        # Create asyncio task
        task = asyncio.create_task(
            self._execute_scalein(
                symbol=symbol,
                side=side,
                total_qty=quantity,
                num_chunks=num_chunks,
                delay_range=delay_range
            )
        )

        # Register task with event bus
        event_bus.register_task(symbol, "scalein", task)

        return (
            f"🔄 SCALEIN INITIATED\n"
            f"Mode: {speed.upper()} ({duration})\n"
            f"Side: {side.upper()}\n"
            f"Total Quantity: {quantity:,}\n"
            f"Chunks: {num_chunks}\n"
            f"Current Price: ${current_price:.2f}\n" if current_price else ""
            f"💡 Progress updates will appear in chat automatically"
        )

    async def _execute_scalein(
        self,
        symbol: str,
        side: str,
        total_qty: int,
        num_chunks: int,
        delay_range: tuple
    ):
        """Execute the scalein process in background."""
        try:
            print(f"[Scalein] STARTING scalein for {symbol}: {total_qty} shares in {num_chunks} chunks")
            chunk_size = max(1, total_qty // num_chunks)
            remaining = total_qty
            chunk_num = 0
            total_cost = 0.0

            print(f"[Scalein] Publishing scalein_start event...")
            await event_bus.publish(symbol, {
                "type": "scalein_start",
                "message": f"🔄 Starting scalein: {total_qty:,} shares in {num_chunks} chunks",
                "data": {
                    "total_qty": total_qty,
                    "num_chunks": num_chunks,
                    "chunk_size": chunk_size,
                    "side": side
                }
            })
            print(f"[Scalein] scalein_start event published")

            while remaining > 0:
                chunk_num += 1

                # Determine chunk size for this iteration
                if chunk_num == num_chunks:
                    # Last chunk - buy remaining
                    this_chunk = remaining
                else:
                    # Regular chunk
                    this_chunk = min(chunk_size, remaining)

                # Get FRESH current price from API for this chunk
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"http://localhost:8000/bars/{symbol}/historical?limit=1")
                        if response.status_code == 200:
                            bars = response.json()
                            if bars and len(bars) > 0:
                                latest_bar = bars[0]
                                current_price = latest_bar['close']
                                print(f"[Scalein] Chunk {chunk_num}: Using fresh price ${current_price:.2f}")
                            else:
                                # Fallback to cached data
                                market_data = self.market_data.get(symbol)
                                current_price = market_data.get('price', market_data.get('close')) if market_data else None
                        else:
                            # Fallback to cached data
                            market_data = self.market_data.get(symbol)
                            current_price = market_data.get('price', market_data.get('close')) if market_data else None
                except Exception as e:
                    print(f"[Scalein] Error fetching fresh price: {e}, using cached")
                    market_data = self.market_data.get(symbol)
                    current_price = market_data.get('price', market_data.get('close')) if market_data else None

                if not current_price:
                    await event_bus.publish(symbol, {
                        "type": "scalein_error",
                        "message": "⚠️ No market data - pausing scalein",
                        "data": {}
                    })
                    await asyncio.sleep(30)
                    continue

                # Calculate cost for this chunk
                chunk_cost = current_price * this_chunk
                total_cost += chunk_cost

                # Get current position (if any)
                position = self.position_storage.get_open_position(symbol)

                # Add to position
                result = self.position_storage.record_position(
                    symbol=symbol,
                    side=side,
                    quantity=this_chunk,
                    entry_price=current_price,
                    current_price=current_price
                )

                # Get updated position info
                updated_position = self.position_storage.get_open_position(symbol)
                new_qty = updated_position['quantity']
                avg_entry = updated_position['entry_price']

                remaining -= this_chunk

                # Publish progress event
                if remaining > 0:
                    await event_bus.publish(symbol, {
                        "type": "scalein_progress",
                        "message": (
                            f"✓ Chunk {chunk_num}/{num_chunks}: Bought {this_chunk:,} @ ${current_price:.2f}\n"
                            f"Cost: ${chunk_cost:.2f} | Position: {new_qty:,} @ ${avg_entry:.2f} avg | Total Cost: ${total_cost:.2f}"
                        ),
                        "data": {
                            "chunk_num": chunk_num,
                            "total_chunks": num_chunks,
                            "quantity": this_chunk,
                            "price": current_price,
                            "cost": chunk_cost,
                            "position_qty": new_qty,
                            "avg_entry": avg_entry,
                            "total_cost": total_cost
                        }
                    })
                else:
                    # Final entry
                    await event_bus.publish(symbol, {
                        "type": "scalein_complete",
                        "message": (
                            f"🎉 SCALEIN COMPLETE\n"
                            f"Final Chunk: {this_chunk:,} @ ${current_price:.2f}\n"
                            f"Total Position: {new_qty:,} @ ${avg_entry:.2f} avg\n"
                            f"Total Cost: ${total_cost:.2f}"
                        ),
                        "data": {
                            "total_cost": total_cost,
                            "avg_entry_price": avg_entry,
                            "final_qty": new_qty
                        }
                    })
                    break

                # Wait before next chunk
                if remaining > 0:
                    delay = random.uniform(*delay_range)
                    await asyncio.sleep(delay)

        except asyncio.CancelledError:
            await event_bus.publish(symbol, {
                "type": "scalein_cancelled",
                "message": "⚠️ Scalein cancelled by user",
                "data": {}
            })
            raise

        except Exception as e:
            await event_bus.publish(symbol, {
                "type": "scalein_error",
                "message": f"❌ Scalein error: {str(e)}",
                "data": {"error": str(e)}
            })
            raise

    async def cancel_scalein(self, symbol: str) -> str:
        """Cancel an active scalein."""
        cancelled = event_bus.cancel_task(symbol, "scalein")

        if cancelled:
            await event_bus.publish(symbol, {
                "type": "scalein_cancelled",
                "message": "⚠️ Scalein cancelled",
                "data": {}
            })
            return "✓ Scalein cancelled"
        else:
            return "⚠️ No active scalein to cancel"

    def get_scalein_status(self, symbol: str) -> Optional[Dict]:
        """Check if scalein is active."""
        task = event_bus.get_task(symbol, "scalein")
        if task and not task.done():
            return {
                "active": True,
                "task": task
            }
        return None
