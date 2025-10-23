"""
Quick test to see if EQUS.MINI provides after-hours data.
"""
import databento as db
from datetime import datetime
import pytz

print(f"[{datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z')}] Testing EQUS.MINI for after-hours data...")
print("Subscribing to AAPL, TSLA, NVDA...")
print("If we see price updates, after-hours data is available!")
print("-" * 60)

client = db.Live(key="db-Uy7j8hhNfyxPadQFiHcpbKYUMCQDt")

# Counter to track messages
message_count = 0
max_messages = 20  # Stop after 20 messages to avoid running forever

def callback(msg):
    global message_count
    message_count += 1

    ts = datetime.now(pytz.timezone('US/Eastern')).strftime('%H:%M:%S')

    if isinstance(msg, db.SymbolMappingMsg):
        print(f"[{ts}] Symbol mapping: {msg.stype_out_symbol}")
    elif isinstance(msg, db.MBP1Msg):
        print(f"[{ts}] MBP1: instrument_id={msg.instrument_id}, bid={msg.levels[0].bid_px}, ask={msg.levels[0].ask_px}")
    elif isinstance(msg, db.TradeMsg):
        print(f"[{ts}] TRADE: price={msg.price}, size={msg.size}")
    elif isinstance(msg, db.BboMsg):
        print(f"[{ts}] BBO: bid={msg.bid_px}, ask={msg.ask_px}")
    else:
        print(f"[{ts}] {type(msg).__name__}")

    if message_count >= max_messages:
        print("-" * 60)
        print(f"Received {message_count} messages. Stopping test.")
        client.stop()

client.subscribe(
    dataset="EQUS.MINI",
    schema="mbp-1",
    symbols=["AAPL", "TSLA", "NVDA"],
)

client.add_callback(callback)

print("Listening for 30 seconds...")
try:
    client.start()
    import time
    time.sleep(30)  # Listen for 30 seconds
    client.stop()
except KeyboardInterrupt:
    print("\nTest interrupted by user")
    client.stop()

print("-" * 60)
print(f"Test complete. Total messages received: {message_count}")

if message_count == 0:
    print("❌ No data received - EQUS.MINI might not stream after-hours")
elif message_count <= 3:
    print("⚠️  Only symbol mappings received - likely no after-hours data")
else:
    print("✅ Received price data! EQUS.MINI appears to stream after-hours")
