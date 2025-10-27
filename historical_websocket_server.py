#!/usr/bin/env python3
"""
Historical Data WebSocket Server - Replay historical bars as if they're live.

This server runs independently and streams historical bars one at a time
through WebSocket to simulate real-time market conditions for backtesting.

Usage:
    python historical_websocket_server.py --symbol BYND --speed 1.0 --port 8001
"""

import asyncio
import json
import argparse
from datetime import datetime
from typing import Set, Dict, Optional
import websockets
from shared.database import supabase

# Track connected clients per symbol
clients: Dict[str, Set] = {}

# Replay state per symbol
replay_state: Dict[str, Dict] = {}


def normalize_bars(bars: list) -> list:
    """
    Normalize bars to create continuous price flow.
    Makes the open of each bar equal to the close of the previous bar,
    simulating continuous market data as if we had full ITCH depth.
    Also deduplicates bars with the same timestamp.
    """
    if not bars or len(bars) < 2:
        return bars

    # First, deduplicate by timestamp - keep the last occurrence
    seen_timestamps = {}
    for bar in bars:
        seen_timestamps[bar['timestamp']] = bar

    # Sort by timestamp to ensure proper order
    from datetime import datetime
    deduplicated = sorted(seen_timestamps.values(), key=lambda x: datetime.fromisoformat(x['timestamp'].replace('+00:00', '')))

    # Now normalize for continuous flow
    normalized = []
    prev_close = None

    for i, bar in enumerate(deduplicated):
        normalized_bar = bar.copy()

        if prev_close is not None:
            # Set this bar's open to previous bar's close for continuity
            normalized_bar['open'] = prev_close

            # Ensure OHLC relationship is valid: low <= open <= high, low <= close <= high
            normalized_bar['low'] = min(prev_close, float(bar['low']))
            normalized_bar['high'] = max(prev_close, float(bar['high']))

            # Make sure close is within the high/low range
            normalized_bar['close'] = max(normalized_bar['low'], min(normalized_bar['high'], float(bar['close'])))

        normalized.append(normalized_bar)
        prev_close = float(normalized_bar['close'])

    return normalized


async def fetch_historical_bars(symbol: str, limit: int = 10000) -> list:
    """Fetch historical bars for a symbol."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching historical bars for {symbol}...")

    try:
        # Supabase Python client has a max limit of 1000 per request
        # Need to paginate to get all bars
        all_bars = []
        page_size = 1000
        offset = 0

        while len(all_bars) < limit:
            response = (supabase.table("historical_bars")
                       .select("*")
                       .eq("symbol", symbol.upper())
                       .order("timestamp", desc=False)  # Ascending order for replay
                       .range(offset, offset + page_size - 1)
                       .execute())

            if not response.data:
                break  # No more data

            all_bars.extend(response.data)
            offset += page_size

            print(f"[{datetime.now().strftime('%H:%M:%S')}]   Fetched {len(response.data)} bars (total: {len(all_bars)})")

            if len(response.data) < page_size:
                break  # Last page

        bars = all_bars[:limit]  # Cap at requested limit
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Loaded {len(bars)} bars for {symbol}")

        # Normalize bars for continuous flow
        normalized_bars = normalize_bars(bars)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Normalized {len(normalized_bars)} bars for continuous flow")

        return normalized_bars
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Error fetching bars: {e}")
        return []


async def replay_bars(symbol: str, speed: float = 1.0):
    """
    Replay historical bars one at a time to connected clients.

    Args:
        symbol: Stock symbol to replay
        speed: Playback speed multiplier (1.0 = real-time, 2.0 = 2x speed, 0.5 = half speed)
    """
    if symbol not in replay_state or not replay_state[symbol].get('bars'):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] No bars loaded for {symbol}")
        return

    state = replay_state[symbol]
    bars = state['bars']
    current_index = state.get('current_index', 0)
    is_playing = state.get('is_playing', False)

    if not is_playing:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Replay for {symbol} is paused")
        return

    # Calculate sleep time (1 minute bar = 60 seconds / speed)
    sleep_time = 60.0 / speed

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting replay for {symbol} at {speed}x speed ({sleep_time:.1f}s per bar)")

    while current_index < len(bars) and state.get('is_playing', False):
        bar = bars[current_index]

        # Format bar data for WebSocket
        message = {
            "type": "bar",
            "symbol": symbol,
            "data": {
                "timestamp": bar['timestamp'],
                "open": float(bar['open']),
                "high": float(bar['high']),
                "low": float(bar['low']),
                "close": float(bar['close']),
                "volume": int(bar['volume']),
            },
            "meta": {
                "bar_index": current_index + 1,
                "total_bars": len(bars),
                "progress": round((current_index + 1) / len(bars) * 100, 2),
                "is_last": current_index == len(bars) - 1
            }
        }

        # Broadcast to all connected clients for this symbol
        if symbol in clients and clients[symbol]:
            disconnected = set()
            for client in clients[symbol]:
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)

            # Remove disconnected clients
            clients[symbol] -= disconnected

            if current_index % 10 == 0 or current_index == len(bars) - 1:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {symbol} - Bar {current_index + 1}/{len(bars)} "
                      f"({message['meta']['progress']}%) | "
                      f"${bar['close']} | Vol: {bar['volume']:,}")

        # Update state
        current_index += 1
        state['current_index'] = current_index

        # If reached the end, loop or stop
        if current_index >= len(bars):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Replay complete for {symbol}")
            state['is_playing'] = False
            state['current_index'] = 0  # Reset for replay

            # Send completion message
            completion_msg = {
                "type": "replay_complete",
                "symbol": symbol,
                "message": f"Replay complete - {len(bars)} bars streamed"
            }
            if symbol in clients:
                for client in clients[symbol]:
                    try:
                        await client.send(json.dumps(completion_msg))
                    except:
                        pass
            break

        # Wait before next bar
        await asyncio.sleep(sleep_time)


async def handle_client(websocket):
    """Handle WebSocket client connection."""
    client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    current_symbol = None

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔌 Client connected: {client_id}")

    try:
        # Send welcome message
        await websocket.send(json.dumps({
            "type": "connected",
            "message": "Historical data WebSocket server",
            "server_time": datetime.now().isoformat()
        }))

        async for message in websocket:
            try:
                data = json.loads(message)
                command = data.get('command')
                symbol = data.get('symbol', '').upper()

                if command == 'subscribe' and symbol:
                    # Unsubscribe from previous symbol
                    if current_symbol and current_symbol in clients:
                        clients[current_symbol].discard(websocket)

                    # Subscribe to new symbol
                    if symbol not in clients:
                        clients[symbol] = set()
                    clients[symbol].add(websocket)
                    current_symbol = symbol

                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 {client_id} subscribed to {symbol}")

                    # Always reload and reset for fresh subscription
                    bars = await fetch_historical_bars(symbol)
                    replay_state[symbol] = {
                        'bars': bars,
                        'current_index': 0,
                        'is_playing': False,
                        'speed': 1.0
                    }

                    # Send current state
                    state = replay_state[symbol]
                    await websocket.send(json.dumps({
                        "type": "subscribed",
                        "symbol": symbol,
                        "total_bars": len(state['bars']),
                        "current_index": state['current_index'],
                        "is_playing": state['is_playing'],
                        "speed": state['speed']
                    }))

                elif command == 'play' and symbol:
                    if symbol in replay_state:
                        replay_state[symbol]['is_playing'] = True
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ▶️  Play {symbol}")

                        # Start replay task if not already running
                        asyncio.create_task(replay_bars(symbol, replay_state[symbol].get('speed', 1.0)))

                        await websocket.send(json.dumps({
                            "type": "status",
                            "message": f"Playing {symbol}",
                            "is_playing": True
                        }))

                elif command == 'pause' and symbol:
                    if symbol in replay_state:
                        replay_state[symbol]['is_playing'] = False
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏸️  Pause {symbol}")

                        await websocket.send(json.dumps({
                            "type": "status",
                            "message": f"Paused {symbol}",
                            "is_playing": False
                        }))

                elif command == 'reset' and symbol:
                    if symbol in replay_state:
                        replay_state[symbol]['current_index'] = 0
                        replay_state[symbol]['is_playing'] = False
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏮️  Reset {symbol}")

                        await websocket.send(json.dumps({
                            "type": "status",
                            "message": f"Reset {symbol}",
                            "current_index": 0
                        }))

                elif command == 'set_speed' and symbol:
                    speed = float(data.get('speed', 1.0))
                    if symbol in replay_state:
                        replay_state[symbol]['speed'] = speed
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚡ Set speed for {symbol}: {speed}x")

                        await websocket.send(json.dumps({
                            "type": "status",
                            "message": f"Speed set to {speed}x",
                            "speed": speed
                        }))

            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Error handling message: {e}")
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Cleanup on disconnect
        if current_symbol and current_symbol in clients:
            clients[current_symbol].discard(websocket)
            if not clients[current_symbol]:
                del clients[current_symbol]

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔌 Client disconnected: {client_id}")


async def main(port: int = 8001):
    """Start the WebSocket server."""
    print("=" * 80)
    print("📡 Historical Data WebSocket Server")
    print("=" * 80)
    print(f"Port: {port}")
    print(f"Endpoint: ws://localhost:{port}")
    print()
    print("Commands:")
    print("  - subscribe: Load historical bars for a symbol")
    print("  - play: Start replaying bars")
    print("  - pause: Pause replay")
    print("  - reset: Reset to beginning")
    print("  - set_speed: Change playback speed")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()

    async with websockets.serve(handle_client, "localhost", port):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Historical Data WebSocket Server")
    parser.add_argument("--port", type=int, default=8001, help="WebSocket port (default: 8001)")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.port))
    except KeyboardInterrupt:
        print("\n\n⚠️  Server stopped by user\n")
