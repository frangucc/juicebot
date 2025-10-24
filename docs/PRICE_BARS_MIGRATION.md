# Price Bars Migration Strategy
## Goal: Add 1-Minute OHLCV Bars for All Symbols (Zero Downtime)

### Overview
We're migrating from **threshold-based alerts** (only capturing 3%+ moves) to **full 1-minute bar capture** (all symbols, all the time). This enables:
- ✅ Accurate baseline calculations (% YEST, % OPEN, % PRE)
- ✅ Foundation for algorithmic trading systems
- ✅ Ability to reconstruct complete 1-minute charts

### Storage Impact
- **Current**: 3.17 GB/year (threshold alerts only)
- **New**: ~175 GB/year (full 1-min bars)
- **Cost**: ~$45-100/month (depending on provider)

---

## Migration Phases

### ✅ Phase 1: Add New Infrastructure (NO BREAKING CHANGES)

**What we're adding:**
1. New `price_bars` table (runs alongside existing tables)
2. Bar aggregator in scanner (adds bars while keeping alerts)
3. New baseline calculation functions (query price_bars, fallback to old method)

**What stays the same:**
- ✅ `screener_alerts` table still works
- ✅ Existing alerts/notifications still fire
- ✅ Dashboard still works
- ✅ All existing APIs unchanged

**Timeline**: Today (Friday) - Ready to deploy Monday

---

### Phase 2: Start Capturing Bars (Monday Cloud Deploy)

**Scanner changes:**
1. Scanner receives tick via websocket
2. **NEW**: Aggregate tick into 1-minute bar (in-memory)
3. **KEEP**: Check if crossed 3% threshold → fire alert
4. Every 1 minute: Flush completed bar to `price_bars` table
5. Every 2 seconds: Flush alerts to `screener_alerts` table (unchanged)

**Result**:
- Monday onwards: Full 1-minute bars for all 11.9k symbols
- Historical data: Use old Databento lookups or live with gaps

---

### Phase 3: Fix Baseline Calculations (Monday Evening)

**Switch calculations to use `price_bars`:**

1. **Fix % YEST**:
   - Old: Load from Databento EQUS.SUMMARY (often stale)
   - New: Query `price_bars` for yesterday 4:00 PM close
   - Fallback: Use Databento if no bar found

2. **Fix % OPEN**:
   - Old: First price scanner sees (wrong)
   - New: Query `price_bars` for today 8:30 AM bar
   - Fallback: Use `rth_open` if no bar found

3. **Fix % PRE**:
   - Old: Scanner in-memory dict (empty if started late)
   - New: Query `price_bars` for earliest bar today before 8:30 AM
   - Fallback: NULL if no pre-market bar

4. **Fix 5m/15m**:
   - Old: In-memory snapshots (broken)
   - New: Aggregate last 5/15 bars from `price_bars`
   - Fallback: Current broken logic

**Result**: All calculations accurate from Monday onwards

---

### Phase 4: Build Chart Infrastructure (Week 2+)

**Enable algorithmic trading:**
1. API endpoint: `GET /charts/{symbol}?interval=1m&from=...&to=...`
2. Returns: Array of OHLCV bars for charting
3. Trading system can query historical bars to make decisions
4. Build indicators (SMA, RSI, MACD) on top of bars

---

## Technical Details

### 1. Bar Aggregation Logic

```python
class BarAggregator:
    def __init__(self):
        self.current_bars = {}  # symbol -> Bar

    def add_tick(self, symbol, price, timestamp):
        # Round timestamp to minute boundary
        bar_timestamp = timestamp.floor('1min')

        if symbol not in self.current_bars:
            # Start new bar
            self.current_bars[symbol] = Bar(
                symbol=symbol,
                timestamp=bar_timestamp,
                open=price,
                high=price,
                low=price,
                close=price,
                trade_count=1
            )
        else:
            bar = self.current_bars[symbol]

            # Check if we've crossed into a new minute
            if bar_timestamp > bar.timestamp:
                # Flush completed bar to database
                self.flush_bar(symbol, bar)

                # Start new bar
                self.current_bars[symbol] = Bar(...)
            else:
                # Update current bar
                bar.high = max(bar.high, price)
                bar.low = min(bar.low, price)
                bar.close = price
                bar.trade_count += 1
```

### 2. Database Schema

```sql
price_bars:
- id (bigserial): Primary key
- symbol (varchar): Stock ticker
- timestamp (timestamptz): Start of 1-minute window (e.g., 2025-10-24 14:30:00)
- open (decimal): First trade in minute
- high (decimal): Highest trade in minute
- low (decimal): Lowest trade in minute
- close (decimal): Last trade in minute
- volume (bigint): Total volume (if available)
- trade_count (int): Number of ticks aggregated
- created_at (timestamptz): When bar was inserted

Indexes:
- (symbol, timestamp DESC): Fast symbol queries
- (timestamp DESC): Fast time-range queries
- UNIQUE (symbol, timestamp): One bar per symbol per minute
```

### 3. Query Examples

```sql
-- Get yesterday's closing price
SELECT close FROM price_bars
WHERE symbol = 'WGRX'
AND timestamp = (CURRENT_DATE - INTERVAL '1 day') + INTERVAL '16 hours'
LIMIT 1;

-- Get today's opening price (8:30 AM)
SELECT open FROM price_bars
WHERE symbol = 'WGRX'
AND timestamp = CURRENT_DATE + INTERVAL '8 hours 30 minutes'
LIMIT 1;

-- Get last 5 minutes of bars
SELECT * FROM price_bars
WHERE symbol = 'WGRX'
AND timestamp >= NOW() - INTERVAL '5 minutes'
ORDER BY timestamp DESC;

-- Build 5-minute OHLCV from 1-minute bars
SELECT
    symbol,
    DATE_TRUNC('minute', timestamp - INTERVAL '5 minutes') as bar_start,
    FIRST(open ORDER BY timestamp) as open,
    MAX(high) as high,
    MIN(low) as low,
    LAST(close ORDER BY timestamp) as close,
    SUM(volume) as volume
FROM price_bars
WHERE symbol = 'WGRX'
AND timestamp >= NOW() - INTERVAL '5 minutes'
GROUP BY symbol, bar_start;
```

---

## Rollout Checklist

### Friday (Today):
- [x] Create `price_bars` table migration
- [ ] Run migration on Supabase
- [ ] Test table creation
- [ ] Add bar aggregator class to scanner
- [ ] Test aggregator locally (without writing to DB)

### Monday (Cloud Deploy):
- [ ] Enable bar flushing to `price_bars` table
- [ ] Deploy to cloud
- [ ] Monitor storage growth (should be ~700 MB/day)
- [ ] Verify bars are being written correctly

### Monday Evening:
- [ ] Switch baseline calculations to query `price_bars`
- [ ] Test % YEST, % OPEN, % PRE accuracy
- [ ] Deploy dashboard updates
- [ ] Monitor leaderboard accuracy

### Week 2:
- [ ] Build `/charts` API endpoint
- [ ] Add data retention policy (keep 90 days, archive older)
- [ ] Add data export scripts
- [ ] Begin building trading algorithms on top

---

## Rollback Plan

If anything breaks:
1. **Disable bar writing**: Set `ENABLE_PRICE_BARS=false` in env
2. **Fall back to old logic**: Baseline calculations revert to old methods
3. **Keep alerts working**: `screener_alerts` table unchanged

**No downtime, no data loss.**

---

## Future Enhancements

1. **Data compression**: Use TimescaleDB hypertables (10x compression)
2. **Partitioning**: Partition by month for faster queries
3. **Real-time aggregations**: 5m, 15m, 1h, 1d bars pre-computed
4. **Market replay**: Replay historical bars for backtesting
5. **Multi-timeframe indicators**: SMA, RSI, MACD on any timeframe
