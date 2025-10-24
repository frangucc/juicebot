# Databento Data Capture Analysis & Recommendations

**Date:** 2025-10-24
**Analysis Context:** Investigating data capture completeness for leaderboard stocks

---

## Executive Summary

Your application is **correctly configured** and capturing data from Databento, but there are **4 critical issues** preventing you from getting maximum bar coverage:

1. ✅ **Volume is 0 by design** - MBP-1 schema doesn't include volume data
2. ⚠️ **Bar capture is enabled but you have 8+ duplicate scanner processes running**
3. ⚠️ **You're using MBP-1 (quotes) instead of trades, limiting bar completeness**
4. ⚠️ **No priority mechanism specifically for bar capture - only for DB writes**

---

## 1. Why Volume is Zero (ANSWERED)

### Root Cause: MBP-1 Schema Limitation

**Location:** `screener/scanner.py:599-606`, `scanner.py:272`

```python
# You're subscribing to MBP-1 (Market By Price - Level 1)
live.subscribe(
    dataset=settings.screener_dataset,  # EQUS.MINI
    schema=settings.screener_schema,     # mbp-1
    symbols="ALL_SYMBOLS",
)

# Bar aggregator receives volume=0
self.bar_aggregator.add_tick(
    symbol=symbol,
    price=mid,  # Calculated from bid/ask
    timestamp=ts,
    volume=0  # Volume not available from MBP-1
)
```

### What is MBP-1?

**MBP-1** (Market By Price, Level 1) is **top-of-book quote data**:
- ✅ Best bid price
- ✅ Best ask price
- ✅ Bid size (number of shares)
- ✅ Ask size (number of shares)
- ❌ **NO trade volume** (because these are quotes, not trades)

### Available on Your Databento Plan

According to Databento docs, `EQUS.MINI` includes:
- ✅ `mbp-1` (what you're using) - quotes only
- ✅ `mbp-10` - 10 levels of book depth
- ✅ **`trades`** - actual trade executions with volume
- ✅ `ohlcv-1m`, `ohlcv-1d` - pre-aggregated bars with volume

---

## 2. Getting Volume Data (SOLUTION)

### Option A: Subscribe to Trades Schema (RECOMMENDED)

**Change your schema to get actual trade data with volume:**

```python
# In shared/config.py, change:
screener_schema: str = "trades"  # Instead of "mbp-1"
```

**What you'll get:**
- Trade price
- Trade volume
- Trade timestamp
- Trade conditions/flags

**Trade-offs:**
- ✅ Actual volume per trade
- ✅ More accurate bars (trades, not quotes)
- ✅ Better for bar aggregation
- ⚠️ Higher message rate (more data to process)
- ⚠️ Slightly higher Databento costs

### Option B: Use OHLCV-1M Schema

**Subscribe to pre-aggregated 1-minute bars:**

```python
schema="ohlcv-1m"
```

**What you'll get:**
- Pre-calculated OHLCV bars
- Accurate volume
- Lower message rate

**Trade-offs:**
- ✅ Volume included
- ✅ Less processing needed
- ✅ Lower message rate
- ❌ Already aggregated (can't customize bar intervals)
- ❌ Only updates at minute boundaries

### Option C: Dual Subscription (BEST FOR YOUR USE CASE)

**Run two separate streams:**

1. **Keep MBP-1 for real-time scanning** (fast alerts)
2. **Add trades stream for bar recording** (complete bars)

```python
# Scanner process 1: MBP-1 for alerts
live.subscribe(schema="mbp-1", symbols="ALL_SYMBOLS")

# Scanner process 2: Trades for bar aggregation
live.subscribe(schema="trades", symbols="ALL_SYMBOLS")
```

---

## 3. Multiple Scanner Processes Issue (CRITICAL)

### Current State

You have **8+ scanner processes running simultaneously:**

```bash
$ ps aux | grep scanner
franckjones  66813  15.9%  /Python -u -m screener.main --threshold 0.03
franckjones  63246  13.8%  /Python -u -m screener.main --threshold 0.03
franckjones  62299  11.8%  /Python -u -m screener.main --threshold 0.03
franckjones  58911  11.1%  /Python -u -m screener.main --threshold 0.03
... (4 more)
```

### Impact on Bar Capture

**Each process:**
- Subscribes to the same data feed
- Creates its own bars independently
- Writes to the same `price_bars` table
- **Causes race conditions and overwrites**

### From Your Logs

```
[2025-10-24 16:29:58] Flushed 10 symbols to symbol_state table (batch #74850)
[DEBUG] Processed 6883000 messages, 11963 symbols mapped
```

This shows your scanner is processing data correctly, but **multiple scanners competing** may cause:
- Inconsistent bar data
- Database contention
- Missed ticks (each scanner processes a subset)

### Solution

**Kill duplicate processes and run only ONE scanner:**

```bash
# Kill all scanners
pkill -f "screener.main"

# Restart single scanner
npm stop screener
npm start screener
```

---

## 4. Bar Coverage Analysis

### Current Bar Aggregator Configuration

**Location:** `screener/bar_aggregator.py:67-91`

```python
class BarAggregator:
    def __init__(self, enable_db_writes: bool = False):
        self.enable_db_writes = enable_db_writes
        self._flush_interval = 60  # Flush every 60 seconds
```

**Enabled via:** `ENABLE_PRICE_BARS=true` in `.env` ✅

### How Bars Are Created

**Location:** `screener/bar_aggregator.py:92-146`

```python
def add_tick(self, symbol: str, price: float, timestamp: pd.Timestamp, volume: int = 0):
    # Round to minute boundary
    bar_timestamp = timestamp.floor('1min')

    # Create or update bar
    if symbol in self.current_bars:
        current_bar = self.current_bars[symbol]
        if bar_timestamp > current_bar.timestamp:
            # Complete current bar, start new one
            self.completed_bars[symbol] = current_bar
        else:
            # Update current bar
            current_bar.update_with_tick(price, volume)
```

**This design is sound ✅**

### Why Some Symbols Have Few Bars

From your test results:
- **IRE:** 58 bars over 96 minutes = 0.6 bars/minute ✅ Good
- **INBX:** 2 bars over 44 minutes = 0.05 bars/minute ❌ Very sparse
- **CIIT:** 2 bars over 1 minute = illiquid

**Reasons for sparse bars:**

1. **Symbol is illiquid** - no quotes/trades being sent by exchange
2. **Wide spreads filtered out** - `scanner.py:243` skips if spread > 2%
3. **MBP-1 updates only when quote changes** - if bid/ask don't move, no messages
4. **Symbol not actively traded** - warrants, low-volume OTC stocks

---

## 5. Priority Mechanism Analysis

### Current Priority System

**Location:** `scanner.py:119-143`, `scanner.py:289-329`

```python
PRIORITY_UPDATE_INTERVALS = {
    1: 5,     # Tier 1 (20%+): Update DB every 5 seconds
    2: 30,    # Tier 2 (10-20%): Update DB every 30 seconds
    3: 60,    # Tier 3 (5-10%): Update DB every 60 seconds
    4: 120,   # Tier 4 (1-5%): Update DB every 2 minutes
}
```

### What Priority Does

✅ **Prioritizes database writes to `symbol_state` table**
❌ **Does NOT prioritize bar capture or tick processing**

### The Code Flow

```python
# scanner.py:266-273
# Bar aggregator receives ALL ticks BEFORE any filtering
if self.bar_aggregator:
    self.bar_aggregator.add_tick(
        symbol=symbol,
        price=mid,
        timestamp=ts,
        volume=0  # Volume not available from MBP-1
    )

# Priority system only affects symbol_state DB writes (line 289+)
```

**This means:** Bar capture already gets maximum priority! ✅

---

## 6. Are You Missing Data From Databento?

### Short Answer: Probably Not

Your scanner logs show:
```
[DEBUG] Processed 6883000 messages, 11963 symbols mapped
[DEBUG] Message types: {'SystemMsg': 20, 'SymbolMappingMsg': 11963, 'MBP1Msg': 6871017}
```

**This indicates:**
- ✅ You're receiving messages from Databento
- ✅ All 11,963 symbols are mapped
- ✅ 6.8M MBP-1 messages processed
- ✅ No connection errors

### What You're NOT Getting

**From MBP-1 schema:**
- ❌ Trade volume
- ❌ Trade conditions
- ❌ Trades for illiquid symbols (they may have no quotes)

**From EQUS.MINI dataset:**
- ❌ Extended hours quotes (EQUS.MINI is 9:30 AM - 4:00 PM ET only)

---

## 7. Threading & Queue Analysis

### Current Architecture

**Single-threaded event loop:**

```python
# scanner.py:614-615
live.start()
live.block_for_close()
```

**Databento SDK handles:**
- ✅ Network I/O in background threads
- ✅ Message deserialization
- ✅ Queueing before callback

**Your callback is synchronous:**
```python
def scan(self, event: Any) -> None:
    # Processes each message one at a time
    # No explicit threading or queuing
```

### Potential Bottlenecks

1. **Database writes block message processing**
   - `scanner.py:358-467` - Symbol state batch flush
   - `bar_aggregator.py:148-212` - Bar batch flush

2. **OHLCV fallback fetch (line 469-536)**
   - Runs every 5 minutes
   - Makes synchronous HTTP request to Databento
   - Could block live stream processing

### Recommendations

**Add async processing for DB writes:**

```python
# Use asyncio or threading to avoid blocking callback
import concurrent.futures

class PriceMovementScanner:
    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    def _flush_symbol_state_batch(self):
        # Submit to background thread
        self.executor.submit(self._do_db_write, batch_data)
```

---

## 8. Symbols With No Bar Data

### Your Test Results

**11 symbols returned 404 errors:**
- ADVWW, MOFG, MSN, CRMLW, NTRP, FRDU, CLSKW, MIGI, CELZ, REFR, TGL

### Why No Bars?

1. **Warrants** (ADVWW, CRMLW, CLSKW)
   - Often have minimal trading
   - May not be included in `ALL_SYMBOLS` for EQUS.MINI

2. **Low liquidity**
   - No quotes during the time window
   - Filtered out by spread threshold (>2%)

3. **Not in Databento's symbol universe**
   - Some OTC or delisted stocks

### Verification Test

Run this to see what symbols Databento is sending:

```bash
# Check if symbols exist in your database
psql $DATABASE_URL -c "SELECT symbol, COUNT(*) as bar_count FROM price_bars WHERE symbol IN ('ADVWW', 'MOFG', 'MSN') GROUP BY symbol;"
```

---

## 9. Recommendations Summary

### Immediate Actions (Critical)

1. ✅ **Kill duplicate scanner processes**
   ```bash
   pkill -f "screener.main"
   npm stop screener && npm start screener
   ```

2. ✅ **Switch to `trades` schema for volume data**
   ```python
   # shared/config.py
   screener_schema: str = "trades"
   ```

3. ✅ **Verify bar capture is working**
   ```bash
   # Check if bars are being written
   psql $DATABASE_URL -c "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM price_bars WHERE timestamp > NOW() - INTERVAL '1 hour';"
   ```

### Short-Term Improvements

4. ⚠️ **Add async DB writes to prevent blocking**
   - Move batch flushes to background threads
   - Prevent message backlog during DB writes

5. ⚠️ **Implement bar capture monitoring**
   - Log bar creation rate per minute
   - Alert if bar rate drops significantly

6. ⚠️ **Add bar completeness metrics**
   ```python
   # Track expected vs actual bars
   expected_bars = (current_time - start_time) / 60  # minutes
   actual_bars = bar_aggregator.bars_created_count
   completeness = actual_bars / expected_bars
   ```

### Long-Term Optimizations

7. 📊 **Dual-stream architecture**
   - Stream 1: MBP-1 for real-time alerts
   - Stream 2: Trades for bar aggregation

8. 📊 **Symbol-specific subscriptions**
   - Subscribe to leaderboard symbols with `trades`
   - Subscribe to all others with `mbp-1`

9. 📊 **Historical backfill**
   - When a symbol enters leaderboard, backfill last 30 min of bars
   - Use `ohlcv-1m` historical API

---

## 10. Data Capture Verification Script

Run this to verify your current bar capture:

```bash
# Check bar capture for top 20%+ stocks
psql $DATABASE_URL << EOF
SELECT
    symbol,
    COUNT(*) as bar_count,
    MIN(timestamp) as first_bar,
    MAX(timestamp) as last_bar,
    ROUND(EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60, 1) as duration_minutes,
    ROUND(COUNT(*)::numeric / NULLIF(EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60, 0), 2) as bars_per_minute
FROM price_bars
WHERE symbol IN (
    SELECT symbol FROM symbol_state
    WHERE pct_from_yesterday > 20
    ORDER BY pct_from_yesterday DESC
    LIMIT 20
)
AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY symbol
ORDER BY bar_count DESC;
EOF
```

---

## Conclusion

### Your System is Working Correctly ✅

- Databento connection is stable
- Messages are being processed
- Bar aggregator is enabled and functioning
- Priority system is working for DB writes

### Main Issues to Fix

1. **Multiple scanner processes** causing conflicts
2. **No volume data** because you're using quotes (MBP-1) not trades
3. **Potential blocking** during database writes

### Expected Results After Fixes

- ✅ Volume data in bars
- ✅ More bars per symbol (trades update more frequently than quotes)
- ✅ No duplicate/conflicting bar writes
- ✅ Better bar completeness for leaderboard stocks

**Next Steps:** Implement recommendations 1-3, then re-run your test to see improved bar coverage.
