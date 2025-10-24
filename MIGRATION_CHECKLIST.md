# TRADES Migration Checklist

**Quick reference for tonight's migration**

---

## ✅ Pre-Flight Checklist

- [ ] Read `MIGRATION_PLAN.md` thoroughly
- [ ] Backup database: `pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql`
- [ ] Verify only ONE scanner process running: `ps aux | grep screener`
- [ ] Current time is good for deployment (low traffic)

---

## 🚀 Deployment Steps (90 minutes)

### 1. Database Migration (15 min)

```bash
cd /Users/franckjones/Desktop/trade_app

# Run migration
source venv/bin/activate
psql $DATABASE_URL < migrations/001_add_legacy_flag.sql

# Verify
psql $DATABASE_URL -c "SELECT COUNT(*), is_legacy, data_source FROM price_bars GROUP BY is_legacy, data_source;"
```

**Expected output:**
```
 count  | is_legacy | data_source
--------+-----------+-------------
 12453  | true      | mbp-1
(1 row)
```

---

### 2. Code Updates (30 min)

#### A. Update Config
```bash
# Edit shared/config.py line 41
# Change: screener_schema: str = "mbp-1"
# To:     screener_schema: str = "trades"
```

#### B. Update Scanner
See `MIGRATION_PLAN.md` Phase 2.2 for detailed code changes in:
- `screener/scanner.py` (lines 208, 217-283)

Key changes:
- `MBP1Msg` → `TradeMsg`
- `bid/ask` → `trade price`
- `volume=0` → `volume=event.size`

#### C. Update Bar Aggregator
See `MIGRATION_PLAN.md` Phase 2.3 for:
- `screener/bar_aggregator.py` (lines 50-61, 173-197)

Add `is_legacy=False` and `data_source='trades'` to bars

---

### 3. API Updates (15 min)

```python
# api/main.py - Update /bars/{symbol} endpoint
# Add: include_legacy: bool = False parameter
# Add: if not include_legacy: query += " AND (is_legacy = false OR is_legacy IS NULL)"
```

---

### 4. Deploy (5 min)

```bash
# Kill all scanners
pkill -f "screener.main"

# Verify all dead
ps aux | grep screener.main

# Restart
npm stop
npm start

# Check logs
tail -f .pids/screener.log
```

**Look for:**
- `schema: trades` in startup
- `Bar aggregator ENABLED`
- No errors

---

### 5. Validation (10 min)

```bash
# Wait 5 minutes for data to flow

# Check new bars have volume
psql $DATABASE_URL -c "
SELECT symbol, timestamp, volume, data_source, is_legacy
FROM price_bars
WHERE timestamp > NOW() - INTERVAL '10 minutes'
AND is_legacy = false
ORDER BY timestamp DESC
LIMIT 10;"

# Run test
python -m tests.test_leaderboard_analysis up
```

**Expected:**
- ✅ `volume` column has numbers > 0
- ✅ `data_source` = 'trades'
- ✅ `is_legacy` = false

---

## 📊 Weekend Monitoring

```bash
# Start monitor in background
nohup python -m tests.monitor_migration > migration_monitor.log 2>&1 &

# Check monitor output
tail -f migration_monitor.log

# Or check manually
psql $DATABASE_URL -c "
SELECT
    COUNT(*) as new_bars,
    SUM(volume) as total_volume,
    MAX(timestamp) as latest_bar
FROM price_bars
WHERE is_legacy = false
AND timestamp > NOW() - INTERVAL '1 hour';"
```

---

## 🔄 Rollback (If Needed)

```bash
# 1. Stop scanner
pkill -f "screener.main"

# 2. Revert config
# Change shared/config.py back to: screener_schema: str = "mbp-1"

# 3. Revert code changes
git checkout screener/scanner.py screener/bar_aggregator.py

# 4. Delete bad data
psql $DATABASE_URL -c "DELETE FROM price_bars WHERE is_legacy = false AND data_source = 'trades';"

# 5. Restart
npm start
```

---

## 🗑️ Monday/Tuesday Cleanup

**Only after verifying new data is good!**

### Option 1: Archive (Recommended)

```sql
-- Archive legacy data
CREATE TABLE price_bars_legacy AS
SELECT * FROM price_bars WHERE is_legacy = true;

-- Delete from main table
DELETE FROM price_bars WHERE is_legacy = true;

-- Vacuum
VACUUM FULL price_bars;
```

### Option 2: Hard Delete

```sql
-- Backup first!
pg_dump $DATABASE_URL -t price_bars > price_bars_backup_$(date +%Y%m%d).sql

-- Delete
DELETE FROM price_bars WHERE is_legacy = true;

-- Vacuum
VACUUM FULL price_bars;
```

---

## ✅ Success Criteria

Before cleaning up legacy data, verify:

- [ ] New bars have `volume > 0`
- [ ] At least 1,000 new bars collected
- [ ] Bar coverage >= old coverage
- [ ] API returns correct data
- [ ] Leaderboard shows volume
- [ ] No scanner errors
- [ ] Only 1 scanner running
- [ ] Monitor shows healthy status for 3+ days

---

## 📞 Quick Commands

```bash
# Check scanner status
ps aux | grep screener

# Check latest bars
psql $DATABASE_URL -c "SELECT * FROM price_bars ORDER BY timestamp DESC LIMIT 5;"

# Check volume
psql $DATABASE_URL -c "SELECT COUNT(*), AVG(volume) FROM price_bars WHERE is_legacy = false;"

# Restart scanner
npm stop screener && npm start screener

# View logs
tail -f .pids/screener.log
```

---

## 🆘 Emergency Contacts

- Databento Docs: https://databento.com/docs
- Migration Plan: `/Users/franckjones/Desktop/trade_app/MIGRATION_PLAN.md`
- Analysis Docs: `/Users/franckjones/Desktop/trade_app/DATABENTO_ANALYSIS.md`

---

**Good luck! 🚀**
