#!/usr/bin/env python3
"""Test the WebSocket real-time price feed."""
import asyncio
import websockets
import json

async def test_websocket():
    """Connect to WebSocket and print price updates."""
    uri = "ws://localhost:8000/ws/prices"

    print("Connecting to WebSocket...")
    async with websockets.connect(uri) as websocket:
        print("✅ Connected! Listening for price updates...")
        print()

        # Receive and print the first 20 price updates
        count = 0
        while count < 20:
            message = await websocket.recv()
            data = json.loads(message)

            if data['type'] == 'connected':
                print(f"📡 {data['message']}")
                print()
            elif data['type'] == 'price_update':
                price_data = data['data']
                count += 1
                print(f"{count}. {price_data['symbol']}: ${price_data['price']:.4f} ({price_data['pct_from_yesterday']:+.2f}%)")

if __name__ == "__main__":
    asyncio.run(test_websocket())
