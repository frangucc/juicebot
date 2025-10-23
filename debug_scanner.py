"""Debug scanner to see what data we're actually receiving."""
import databento as db
from datetime import datetime
import pytz

print(f"[{datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z')}] Debug test - checking what data is coming in...")
print("-" * 60)

client = db.Live(key="db-Uy7j8hhNfyxPadQFiHcpbKYUMCQDt")

message_count = 0
symbol_mappings = {}
price_updates = []

def callback(msg):
    global message_count, symbol_mappings, price_updates
    message_count += 1

    ts = datetime.now(pytz.timezone('US/Eastern')).strftime('%H:%M:%S')

    if isinstance(msg, db.SymbolMappingMsg):
        symbol_mappings[msg.hd.instrument_id] = msg.stype_out_symbol
        print(f"[{ts}] Symbol mapping: {msg.stype_out_symbol} (ID: {msg.hd.instrument_id})")
    elif isinstance(msg, db.MBP1Msg):
        symbol = symbol_mappings.get(msg.instrument_id, f"ID_{msg.instrument_id}")
        bid = msg.levels[0].bid_px * 1e-9
        ask = msg.levels[0].ask_px * 1e-9
        mid = (bid + ask) / 2
        price_updates.append((symbol, mid))
        print(f"[{ts}] {symbol}: bid=${bid:.4f}, ask=${ask:.4f}, mid=${mid:.4f}")
    else:
        print(f"[{ts}] Other message type: {type(msg).__name__}")

    if message_count >= 50:
        print("-" * 60)
        print(f"Stopping after {message_count} messages")
        print(f"Symbol mappings received: {len(symbol_mappings)}")
        print(f"Price updates received: {len(price_updates)}")
        client.stop()

# Test with just a few liquid symbols
client.subscribe(
    dataset="EQUS.MINI",
    schema="mbp-1",
    symbols=["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"],
)

client.add_callback(callback)

print("Listening for 30 seconds or 50 messages...")
try:
    client.start()
    import time
    time.sleep(30)
    client.stop()
except KeyboardInterrupt:
    print("\nTest interrupted")
    client.stop()

print("-" * 60)
print(f"Total messages: {message_count}")
print(f"Symbol mappings: {len(symbol_mappings)}")
print(f"Price updates: {len(price_updates)}")

if len(price_updates) == 0:
    print("❌ NO PRICE DATA - After-hours might be over or very low volume")
else:
    print(f"✅ Received {len(price_updates)} price updates")
