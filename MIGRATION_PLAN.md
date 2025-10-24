# Migration Plan: MBP-1 → TRADES Schema

**Date:** October 24, 2025
**Goal:** Switch from MBP-1 (quotes) to TRADES (executions) to get real volume data
**Timeline:** Tonight → Monday/Tuesday cleanup

---

## 🎯 Executive Summary

**What we're doing:**
1. Mark all existing bar data as `legacy` (keep for now)
2. Switch scanner to TRADES schema
3. Start collecting new bars with REAL volume
4. Run both in parallel through weekend
5. Delete legacy data Monday/Tuesday once we verify new data is good

**Why we're doing it:**
- Current: Volume = 0 (MBP-1 doesn't have volume)
- After: Volume = actual shares traded (TRADES has volume)
- Better bars, better analysis, better trading decisions

---

## 📋 Migration Steps

### Phase 1: Prepare Database (Tonight - 15 minutes)

#### Step 1.1: Add Legacy Flag to Existing Data

```sql
-- Connect to database
psql $DATABASE_URL

-- Add is_legacy column to price_bars table
ALTER TABLE price_bars ADD COLUMN IF NOT EXISTS is_legacy BOOLEAN DEFAULT false;
ALTER TABLE price_bars ADD COLUMN IF NOT EXISTS data_source VARCHAR(20) DEFAULT 'mbp-1';

-- Mark all existing data as legacy
UPDATE price_bars SET is_legacy = true, data_source = 'mbp-1' WHERE is_legacy IS NULL OR is_legacy = false;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_price_bars_legacy ON price_bars(is_legacy);
CREATE INDEX IF NOT EXISTS idx_price_bars_source ON price_bars(data_source);

-- Verify
SELECT
    COUNT(*) as total_bars,
    COUNT(*) FILTER (WHERE is_legacy = true) as legacy_bars,
    COUNT(*) FILTER (WHERE is_legacy = false) as new_bars,
    data_source
FROM price_bars
GROUP BY data_source;
```

#### Step 1.2: Update Schema Migration

Create: `/Users/franckjones/Desktop/trade_app/migrations/001_add_legacy_flag.sql`

```sql
-- Migration: Add legacy flag for MBP-1 to TRADES transition
-- Date: 2025-10-24
-- Description: Mark existing bars as legacy before switching to TRADES schema

BEGIN;

-- Add columns if they don't exist
ALTER TABLE price_bars
    ADD COLUMN IF NOT EXISTS is_legacy BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS data_source VARCHAR(20) DEFAULT 'mbp-1',
    ADD COLUMN IF NOT EXISTS migrated_at TIMESTAMP DEFAULT NOW();

-- Mark all existing data as legacy from MBP-1
UPDATE price_bars
SET
    is_legacy = true,
    data_source = 'mbp-1',
    migrated_at = NOW()
WHERE is_legacy IS NULL OR is_legacy = false;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_price_bars_legacy ON price_bars(is_legacy);
CREATE INDEX IF NOT EXISTS idx_price_bars_source ON price_bars(data_source);
CREATE INDEX IF NOT EXISTS idx_price_bars_timestamp_legacy ON price_bars(timestamp, is_legacy);

-- Add comment
COMMENT ON COLUMN price_bars.is_legacy IS 'true = old MBP-1 data (volume=0), false = new TRADES data (real volume)';
COMMENT ON COLUMN price_bars.data_source IS 'mbp-1 = quotes, trades = executions';

COMMIT;
```

---

### Phase 2: Update Application Code (Tonight - 30 minutes)

#### Step 2.1: Update Configuration

**File:** `shared/config.py`

```python
# Change line 41:
# OLD:
screener_schema: str = "mbp-1"

# NEW:
screener_schema: str = "trades"  # ✅ Switch to trades for volume data
```

#### Step 2.2: Update Scanner to Process Trades

**File:** `screener/scanner.py`

**Changes needed:**

```python
# Line 208-210: Change message type check
# OLD:
if not isinstance(event, db.MBP1Msg):
    return

# NEW:
if not isinstance(event, db.TradeMsg):
    return

# Line 217-239: Extract trade data instead of bid/ask
# OLD:
bid = event.levels[0].bid_px
ask = event.levels[0].ask_px

if bid == self.PX_NULL or ask == self.PX_NULL:
    return

bid_price = bid * self.PX_SCALE
ask_price = ask * self.PX_SCALE
mid = (bid_price + ask_price) * 0.5
spread_pct = (ask_price - bid_price) / mid if mid > 0 else 0

if spread_pct > 0.02:
    return

# NEW:
# Extract trade price and volume
trade_price = event.price
if trade_price == self.PX_NULL:
    return

price = trade_price * self.PX_SCALE
volume = event.size  # ✅ This is the actual trade volume!

# No spread check needed for trades (they're executions, not quotes)

# Line 266-273: Update bar aggregator call
# OLD:
if self.bar_aggregator:
    self.bar_aggregator.add_tick(
        symbol=symbol,
        price=mid,
        timestamp=ts,
        volume=0  # ❌ Volume not available from MBP-1
    )

# NEW:
if self.bar_aggregator:
    self.bar_aggregator.add_tick(
        symbol=symbol,
        price=price,
        timestamp=ts,
        volume=volume  # ✅ Real trade volume!
    )

# Line 275-283: Update broadcaster (no bid/ask in trades)
# OLD:
self.price_broadcaster.broadcast_price(
    symbol=symbol,
    price=mid,
    bid=bid_price,
    ask=ask_price,
    pct_from_yesterday=pct_from_yesterday,
    timestamp=ts.isoformat()
)

# NEW:
self.price_broadcaster.broadcast_price(
    symbol=symbol,
    price=price,
    bid=price,  # No bid in trades, use trade price
    ask=price,  # No ask in trades, use trade price
    pct_from_yesterday=pct_from_yesterday,
    timestamp=ts.isoformat()
)

# Update rest of function to use 'price' instead of 'mid'
# Line 285-onwards: Replace 'mid' with 'price'
```

#### Step 2.3: Update Bar Aggregator to Mark Source

**File:** `screener/bar_aggregator.py`

```python
# Line 50-61: Update to_dict method
def to_dict(self) -> dict:
    """Convert bar to dictionary for database insertion."""
    return {
        "symbol": self.symbol,
        "timestamp": self.timestamp.isoformat(),
        "open": self.open,
        "high": self.high,
        "low": self.low,
        "close": self.close,
        "volume": self.volume,
        "trade_count": self.trade_count,
        "is_legacy": False,  # ✅ New bars are not legacy
        "data_source": "trades"  # ✅ Mark as trades schema
    }

# Line 187-197: Update insert query
insert_query = """
    INSERT INTO price_bars (symbol, timestamp, open, high, low, close, volume, trade_count, is_legacy, data_source)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (symbol, timestamp) DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        trade_count = EXCLUDED.trade_count,
        is_legacy = EXCLUDED.is_legacy,
        data_source = EXCLUDED.data_source
"""

# Line 173-184: Update batch_data
batch_data = []
for bar in self.completed_bars.values():
    batch_data.append((
        bar.symbol,
        bar.timestamp,
        bar.open,
        bar.high,
        bar.low,
        bar.close,
        bar.volume,
        bar.trade_count,
        False,  # is_legacy
        "trades"  # data_source
    ))
```

---

### Phase 3: Update API to Filter Legacy Data (Tonight - 15 minutes)

#### Step 3.1: Update Bars API Endpoint

**File:** `api/main.py`

Find the `/bars/{symbol}` endpoint and update to exclude legacy by default:

```python
@app.get("/bars/{symbol}")
async def get_bars(
    symbol: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    include_legacy: bool = False  # ✅ Add parameter
):
    """Get 1-minute OHLCV bars for a symbol."""
    try:
        # Build query
        query = "SELECT * FROM price_bars WHERE symbol = %s"
        params = [symbol]

        # ✅ Filter out legacy data unless explicitly requested
        if not include_legacy:
            query += " AND (is_legacy = false OR is_legacy IS NULL)"

        if start:
            query += " AND timestamp >= %s"
            params.append(start)
        if end:
            query += " AND timestamp <= %s"
            params.append(end)

        query += " ORDER BY timestamp ASC"

        # Execute query...
        # (rest of existing code)
```

---

### Phase 4: Kill Duplicate Scanners & Deploy (Tonight - 5 minutes)

```bash
# Step 1: Kill ALL running scanners
pkill -f "screener.main"

# Verify all are dead
ps aux | grep screener

# Step 2: Run database migration
source venv/bin/activate
psql $DATABASE_URL < migrations/001_add_legacy_flag.sql

# Step 3: Restart services with new code
npm stop
npm start

# Step 4: Verify scanner is running with TRADES
tail -f .pids/screener.log
# Look for: "schema: trades" in startup logs
```

---

### Phase 5: Validation (Tonight - 10 minutes)

```bash
# Test 1: Verify new bars have volume
source venv/bin/activate
psql $DATABASE_URL -c "
    SELECT
        symbol,
        timestamp,
        volume,
        data_source,
        is_legacy
    FROM price_bars
    WHERE timestamp > NOW() - INTERVAL '10 minutes'
    AND is_legacy = false
    ORDER BY timestamp DESC
    LIMIT 10;
"

# Test 2: Count legacy vs new
psql $DATABASE_URL -c "
    SELECT
        data_source,
        is_legacy,
        COUNT(*) as bar_count,
        SUM(volume) as total_volume,
        MIN(timestamp) as first_bar,
        MAX(timestamp) as last_bar
    FROM price_bars
    GROUP BY data_source, is_legacy
    ORDER BY is_legacy DESC;
"

# Test 3: Run bar analysis test
python -m tests.test_leaderboard_analysis up

# Expected: Bars should now have volume > 0!
```

---

### Phase 6: Monitor Through Weekend (Fri-Sun)

**Create monitoring script:** `tests/monitor_migration.py`

```python
"""Monitor TRADES migration progress."""
import psycopg2
from shared.config import settings
import time
from datetime import datetime

while True:
    conn = psycopg2.connect(settings.database_url)
    cur = conn.cursor()

    # Check latest bars
    cur.execute("""
        SELECT
            COUNT(*) as new_bars,
            SUM(volume) as total_volume,
            MAX(timestamp) as latest_bar
        FROM price_bars
        WHERE is_legacy = false
        AND timestamp > NOW() - INTERVAL '1 hour'
    """)

    result = cur.fetchone()
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Migration Status:")
    print(f"  New bars (last hour): {result[0]}")
    print(f"  Total volume:         {result[1]:,} shares")
    print(f"  Latest bar:           {result[2]}")

    cur.close()
    conn.close()

    time.sleep(300)  # Check every 5 minutes
```

Run in background:
```bash
nohup python -m tests.monitor_migration > migration_monitor.log 2>&1 &
```

---

### Phase 7: Legacy Data Cleanup (Monday/Tuesday)

**After verifying new data is good for 3+ days:**

#### Option A: Soft Delete (Recommended)

```sql
-- Keep legacy data but mark for deletion
ALTER TABLE price_bars ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- Mark legacy for deletion
UPDATE price_bars
SET deleted_at = NOW()
WHERE is_legacy = true;

-- Query to exclude deleted
-- WHERE deleted_at IS NULL

-- Actually delete after another week if all is good
DELETE FROM price_bars WHERE deleted_at < NOW() - INTERVAL '7 days';
```

#### Option B: Archive to Separate Table

```sql
-- Create archive table
CREATE TABLE price_bars_legacy AS
SELECT * FROM price_bars WHERE is_legacy = true;

-- Add indexes
CREATE INDEX idx_price_bars_legacy_symbol_timestamp ON price_bars_legacy(symbol, timestamp);

-- Delete from main table
DELETE FROM price_bars WHERE is_legacy = true;

-- Verify
SELECT COUNT(*) FROM price_bars_legacy;  -- Should match old count
SELECT COUNT(*) FROM price_bars WHERE is_legacy = false;  -- Should match new count
```

#### Option C: Hard Delete (Most Aggressive)

```sql
-- ⚠️ ONLY DO THIS AFTER CONFIRMING NEW DATA IS GOOD

-- Backup first
pg_dump $DATABASE_URL -t price_bars > price_bars_backup_$(date +%Y%m%d).sql

-- Delete legacy data
DELETE FROM price_bars WHERE is_legacy = true;

-- Vacuum to reclaim space
VACUUM FULL price_bars;

-- Verify
SELECT
    data_source,
    COUNT(*) as bars,
    MIN(timestamp) as first,
    MAX(timestamp) as last
FROM price_bars
GROUP BY data_source;
```

---

## 📊 Rollback Plan (If Something Goes Wrong)

### If New Data is Bad:

```bash
# 1. Stop scanner
pkill -f "screener.main"

# 2. Revert config
# In shared/config.py, change back to:
screener_schema: str = "mbp-1"

# 3. Revert scanner.py changes
git checkout screener/scanner.py  # If you committed old version
# Or manually change back to MBP1Msg processing

# 4. Delete new bad data
psql $DATABASE_URL -c "DELETE FROM price_bars WHERE is_legacy = false AND data_source = 'trades';"

# 5. Restart scanner
npm start screener
```

### If You Need Legacy Data Back:

```sql
-- If you used Option B (archive)
INSERT INTO price_bars SELECT * FROM price_bars_legacy;

-- If you used Option A (soft delete)
UPDATE price_bars SET deleted_at = NULL WHERE is_legacy = true;
```

---

## ✅ Success Criteria

**Before Monday cleanup, verify:**

1. ✅ New bars have `volume > 0`
2. ✅ At least 1,000 new bars collected
3. ✅ Bar coverage matches or exceeds old MBP-1 coverage
4. ✅ API endpoints return correct data
5. ✅ Leaderboard shows volume data
6. ✅ No scanner errors in logs
7. ✅ Only ONE scanner process running

**Verification queries:**

```sql
-- Check volume distribution
SELECT
    symbol,
    COUNT(*) as bars,
    AVG(volume) as avg_volume,
    MAX(volume) as max_volume
FROM price_bars
WHERE is_legacy = false
AND volume > 0
GROUP BY symbol
ORDER BY bars DESC
LIMIT 20;

-- Compare old vs new bar counts
SELECT
    DATE_TRUNC('hour', timestamp) as hour,
    SUM(CASE WHEN is_legacy = true THEN 1 ELSE 0 END) as legacy_bars,
    SUM(CASE WHEN is_legacy = false THEN 1 ELSE 0 END) as new_bars
FROM price_bars
WHERE timestamp > NOW() - INTERVAL '1 day'
GROUP BY hour
ORDER BY hour;
```

---

## 📝 Timeline

| Phase | Task | Duration | When |
|-------|------|----------|------|
| 1 | Database migration | 15 min | Tonight |
| 2 | Code updates | 30 min | Tonight |
| 3 | API updates | 15 min | Tonight |
| 4 | Deploy | 5 min | Tonight |
| 5 | Validation | 10 min | Tonight |
| 6 | Monitor | 3 days | Fri-Mon |
| 7 | Cleanup | 10 min | Mon/Tue |

**Total active time:** ~90 minutes tonight
**Total timeline:** 3-4 days including monitoring

---

## 🚨 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Lose existing data | HIGH | Mark as legacy, don't delete yet |
| TRADES has less coverage | MEDIUM | Monitor through weekend, can rollback |
| Scanner crashes | MEDIUM | Keep legacy data, easy rollback |
| Duplicate scanners still running | HIGH | Kill all before deploy |
| Volume still 0 | HIGH | Validation step will catch this |

---

## 📞 Decision Points

**Tonight:**
- ✅ Deploy changes
- ✅ Verify volume > 0
- ✅ Keep legacy data

**Monday:**
- Review weekend data
- Decide: Keep collecting or rollback?

**Tuesday:**
- If good: Schedule legacy cleanup
- If bad: Rollback to MBP-1

---

## 🎯 Expected Outcome

**Before migration:**
```
WGRX bars: O:1.20 H:1.25 L:1.15 C:1.18 V:0 ❌
```

**After migration:**
```
WGRX bars: O:1.20 H:1.25 L:1.15 C:1.18 V:1,847 ✅
```

**Real volume data = Better analysis = Better trading!**
