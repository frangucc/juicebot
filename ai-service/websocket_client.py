"""
WebSocket Client for AI Service

Connects to the historical WebSocket server and feeds bar data
into the fast classifier's in-memory buffer.
"""

import asyncio
import json
import websockets
from typing import Dict
from datetime import datetime


class BarDataClient:
    """WebSocket client that subscribes to bar data and populates classifiers."""

    def __init__(self, classifiers: Dict, websocket_url: str = "ws://localhost:8001"):
        self.classifiers = classifiers
        self.websocket_url = websocket_url
        self.ws = None
        self.subscribed_symbols = set()
        self.running = False

    async def connect(self):
        """Connect to WebSocket server."""
        try:
            self.ws = await websockets.connect(self.websocket_url)
            self.running = True
            print(f"[AI Service] ✓ Connected to WebSocket at {self.websocket_url}")
        except Exception as e:
            print(f"[AI Service] ✗ Failed to connect to WebSocket: {e}")
            self.running = False

    async def subscribe(self, symbol: str):
        """Subscribe to bar data for a symbol."""
        if not self.ws or not self.running:
            print(f"[AI Service] ⚠️ WebSocket not connected, cannot subscribe to {symbol}")
            return

        if symbol in self.subscribed_symbols:
            return

        try:
            await self.ws.send(json.dumps({
                "command": "subscribe",
                "symbol": symbol
            }))
            self.subscribed_symbols.add(symbol)
            print(f"[AI Service] 📊 Subscribed to {symbol} bar data")
        except Exception as e:
            print(f"[AI Service] ✗ Failed to subscribe to {symbol}: {e}")

    async def listen(self):
        """Listen for bar updates and populate classifiers."""
        if not self.ws or not self.running:
            return

        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')

                    if msg_type == 'bar':
                        symbol = data.get('symbol')
                        bar_data = data.get('data')

                        if symbol and bar_data:
                            # Ensure classifier exists for this symbol
                            if symbol not in self.classifiers:
                                from fast_classifier import TradingClassifier
                                self.classifiers[symbol] = TradingClassifier()

                            # Update classifier's bar history
                            classifier = self.classifiers[symbol]
                            classifier.update_market_data(symbol, bar_data)

                            # Log every 10th bar
                            meta = data.get('meta', {})
                            if meta.get('bar_index', 0) % 10 == 0:
                                print(f"[AI Service] 📈 {symbol} - Bar {meta.get('bar_index')}/{meta.get('total_bars')} "
                                      f"| ${bar_data['close']} | History: {len(classifier.bar_history)} bars")

                    elif msg_type == 'connected':
                        print(f"[AI Service] ✓ WebSocket connection confirmed")

                    elif msg_type == 'subscribed':
                        symbol = data.get('symbol')
                        total_bars = data.get('total_bars', 0)
                        print(f"[AI Service] ✓ Subscribed to {symbol} ({total_bars} bars available)")

                    elif msg_type == 'replay_complete':
                        symbol = data.get('symbol')
                        print(f"[AI Service] ✓ Replay complete for {symbol}")

                except json.JSONDecodeError:
                    print(f"[AI Service] ⚠️ Invalid JSON received")
                except Exception as e:
                    print(f"[AI Service] ✗ Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            print(f"[AI Service] ⚠️ WebSocket connection closed")
            self.running = False
        except Exception as e:
            print(f"[AI Service] ✗ WebSocket error: {e}")
            self.running = False

    async def start(self):
        """Connect and start listening."""
        await self.connect()
        if self.running:
            await self.listen()

    async def stop(self):
        """Stop the WebSocket client."""
        self.running = False
        if self.ws:
            await self.ws.close()
