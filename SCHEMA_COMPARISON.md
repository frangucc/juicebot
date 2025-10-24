# Databento Schema Comparison: MBP-1 vs Trades

## Quick Answer

**YES**, you can build price bars from **BOTH** schemas:

| Feature | MBP-1 (Current) | Trades (Recommended) |
|---------|----------------|----------------------|
| **Price** | ✅ Yes (bid/ask mid) | ✅ Yes (actual trades) |
| **Timestamp** | ✅ Yes | ✅ Yes |
| **Volume** | ❌ **NO** (always 0) | ✅ **YES** (actual volume) |
| **Bar Building** | ✅ Can build OHLC | ✅ Can build **OHLCV** |

---

## Detailed Comparison

### MBP-1 (Market By Price, Level 1) - What You Have Now

**Data Fields:**
```python
event.instrument_id    # Symbol ID
event.ts_event        # Timestamp (nanoseconds)
event.levels[0].bid_px  # Best bid price
event.levels[0].ask_px  # Best ask price
event.levels[0].bid_sz  # Bid size (NOT trade volume)
event.levels[0].ask_sz  # Ask size (NOT trade volume)
```

**What You Get:**
- Top of book quotes (best bid/ask)
- Updates when market makers change quotes
- Can calculate mid-price: `(bid + ask) / 2`

**What You DON'T Get:**
- ❌ Trade volume (only bid/ask sizes)
- ❌ Actual trade executions
- ❌ Trade side (buy vs sell)

**Use Case:**
- Real-time price alerts (what you're doing now)
- Spread tracking
- Quote-based bars (OHLC without volume)

---

### Trades Schema - The Alternative

**Data Fields:**
```python
event.instrument_id    # Symbol ID
event.ts_event        # Trade timestamp (nanoseconds)
event.price           # Actual trade price
event.size            # ✅ TRADE VOLUME (shares traded)
event.side            # Buy or sell side
event.action          # Trade action type
```

**What You Get:**
- Actual trade executions
- Real trade volume
- Trade price (not calculated mid)
- Trade side information

**Use Case:**
- Building standard OHLCV bars with volume
- Volume analysis
- Trade-based indicators

---

## Building Bars: Side-by-Side

### Current Setup (MBP-1)

```python
# scanner.py:266-273
if self.bar_aggregator:
    self.bar_aggregator.add_tick(
        symbol=symbol,
        price=mid,  # Calculated: (bid + ask) / 2
        timestamp=ts,
        volume=0  # ❌ Always 0 - not available
    )
```

**Result:** Bars with OHLC but **volume = 0**

---

### With Trades Schema

```python
# Modified scanner.py
if not isinstance(event, db.TradeMsg):
    return

# Extract trade data
trade_price = event.price * self.PX_SCALE
trade_volume = event.size  # ✅ Actual shares traded

if self.bar_aggregator:
    self.bar_aggregator.add_tick(
        symbol=symbol,
        price=trade_price,
        timestamp=ts,
        volume=trade_volume  # ✅ Real volume
    )
```

**Result:** Bars with **OHLCV including real volume**

---

## Message Frequency Comparison

### MBP-1 (Quotes)
- Updates when quotes change
- Lower frequency for slow-moving stocks
- More frequent for volatile stocks
- **Example:** Stock with stable bid/ask = few messages

### Trades
- Updates on every trade execution
- Higher frequency overall
- More data to process
- **Example:** Active stock = many trade messages

---

## Code Changes Required

### Option 1: Simple Switch (Replace MBP-1 with Trades)

**1. Update config:**
```python
# shared/config.py
screener_schema: str = "trades"  # Change from "mbp-1"
```

**2. Update scanner callback:**
```python
# scanner.py:145 (scan function)
def scan(self, event: Any) -> None:
    # Handle symbol mapping
    if isinstance(event, db.SymbolMappingMsg):
        # ... existing code ...
        return

    # Change: Process TradeMsg instead of MBP1Msg
    if not isinstance(event, db.TradeMsg):
        return

    # Get trade data
    symbol = self.symbol_directory.get(event.instrument_id)
    if not symbol or symbol not in self.last_day_lookup:
        return

    # Extract trade price and volume
    trade_price = event.price * self.PX_SCALE
    trade_volume = event.size  # ✅ Now we have volume!

    # Rest of logic remains similar
    last_close = self.last_day_lookup[symbol]
    pct_from_yesterday = ((trade_price - last_close) / last_close) * 100

    # Add to bar aggregator WITH volume
    if self.bar_aggregator:
        self.bar_aggregator.add_tick(
            symbol=symbol,
            price=trade_price,
            timestamp=ts,
            volume=trade_volume  # ✅ Real volume
        )

    # Broadcast price update
    self.price_broadcaster.broadcast_price(
        symbol=symbol,
        price=trade_price,
        bid=trade_price,  # No bid/ask in trades
        ask=trade_price,  # Use trade price for both
        pct_from_yesterday=pct_from_yesterday,
        timestamp=ts.isoformat()
    )
```

---

### Option 2: Dual Stream (Advanced)

Run **two separate scanners**:

**Scanner 1: MBP-1 for alerts**
- Fast real-time price updates
- Low latency alerts
- No volume needed

**Scanner 2: Trades for bars**
- Complete OHLCV bar recording
- Volume data
- Separate process

---

## Impact Analysis

### Switching to Trades Schema

**Benefits:**
- ✅ Get real volume data
- ✅ More accurate bars (trades, not mid-prices)
- ✅ Better bar completeness (more updates)
- ✅ Standard OHLCV bars

**Potential Issues:**
- ⚠️ Higher message rate (more data)
- ⚠️ No bid/ask spread data
- ⚠️ Slightly higher Databento costs
- ⚠️ Need to update scanner logic

**Data Loss?**
- No - you still get all price data
- Just different source (trades vs quotes)

---

## Recommendation

### For Your Use Case (Leaderboard + Bar Capture):

**Best Approach: Dual Stream**

1. **Keep MBP-1 for real-time scanning**
   - Fast alerts
   - Spread monitoring
   - Current leaderboard logic works

2. **Add Trades for bar recording**
   - Run separate scanner process
   - Only writes to `price_bars` table
   - Gets you volume data

**Implementation:**
```bash
# Process 1: Alert scanner (MBP-1)
python -m screener.main --threshold 0.03

# Process 2: Bar recorder (Trades)
ENABLE_PRICE_BARS=true SCREENER_SCHEMA=trades python -m screener.bar_recorder
```

### If You Want Simplicity:

**Just switch to Trades:**
- Single schema
- Get volume data
- Lose bid/ask spread info (but you're not using it much)

---

## Testing the Switch

**Before switching, test with historical data:**

```python
import databento as db
from datetime import datetime

client = db.Historical(key="YOUR_KEY")

# Test trades schema
data = client.timeseries.get_range(
    dataset="EQUS.MINI",
    schema="trades",
    symbols=["AAPL", "WGRX"],  # Test with a leaderboard stock
    start="2025-10-24T14:30",
    end="2025-10-24T15:30",
)

# Check what you get
for msg in data:
    print(f"Trade: {msg.price * 1e-9}, Volume: {msg.size}")
```

---

## Summary

| Question | Answer |
|----------|--------|
| Can I build bars from trades schema? | ✅ **YES** |
| Will I get volume? | ✅ **YES** - real trade volume |
| Will I lose price data? | ❌ **NO** - you get trade prices |
| Will bars be complete? | ✅ **Better** - trades update more frequently |
| Should I switch? | ✅ **YES** - if you want volume data |
| Will it break anything? | ⚠️ **Minor code changes needed** |

**Bottom Line:** Switch to `trades` schema to get volume data. Your bar building will work the same (or better), and you'll finally have real volume in your OHLCV bars!
