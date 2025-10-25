#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test_full_cycle():
    try:
        async with websockets.connect('ws://localhost:8001') as ws:
            # Receive welcome
            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            print(f'1. Connected: {json.loads(msg)["type"]}')

            # Subscribe
            await ws.send(json.dumps({'command': 'subscribe', 'symbol': 'BYND'}))
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)
            print(f'2. Subscribed: {data["type"]}, bars: {data.get("total_bars", 0)}')

            # Play
            await ws.send(json.dumps({'command': 'play', 'symbol': 'BYND'}))
            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            print(f'3. Play status: {json.loads(msg)["type"]}')

            # Wait for first bar
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)
            print(f'4. First message: {data["type"]}')
            if data['type'] == 'bar':
                print(f'   Bar {data["meta"]["bar_index"]}/{data["meta"]["total_bars"]}')
                print(f'   Price: ${data["data"]["close"]}')

            print('\n✓ Full cycle working!')
    except asyncio.TimeoutError:
        print('Timeout waiting for message')
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_full_cycle())
