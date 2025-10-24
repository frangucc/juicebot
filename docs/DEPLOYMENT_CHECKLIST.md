# Session Tracking Deployment Checklist

**Date**: 2025-10-24
**Feature**: PRE-market and POST-market baseline tracking

---

## ✅ What's Been Completed

### 1. Scanner Code ✅
- Added session detection function
- Tracks `pre_market_open`, `rth_open`, `post_market_open` separately
- Calculates `pct_from_pre` and `pct_from_post`
- Writes new fields to database

**File**: `/Users/franckjones/Desktop/trade_app/screener/scanner.py`

### 2. Frontend UI ✅
- Updated TypeScript interface with PRE/POST fields
- Added % PRE and % POST to dropdown filter
- "SHOW ALL" view now displays 6 columns: % YEST, % PRE, % OPEN, % POST, % 15M, % 5M
- NULL values display as "--" gracefully

**File**: `/Users/franckjones/Desktop/trade_app/dashboard/components/AlertsLeaderboard.tsx`

### 3. Documentation ✅
- Pre-market baseline analysis: `/docs/PRE_MARKET_BASELINE_ANALYSIS.md`
- Implementation guide: `/docs/SESSION_TRACKING_IMPLEMENTATION.md`
- This deployment checklist

---

## 🔧 REQUIRED: Manual Steps Before Restart

### Step 1: Run Database Migration

**⚠️ CRITICAL - DO THIS FIRST**

1. Open Supabase Dashboard: https://app.supabase.com
2. Navigate to: **SQL Editor**
3. Copy and paste the following SQL:

```sql
-- Add baseline price columns
ALTER TABLE symbol_state
ADD COLUMN IF NOT EXISTS pre_market_open DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS rth_open DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS post_market_open DECIMAL(10, 4);

-- Add percentage move columns
ALTER TABLE symbol_state
ADD COLUMN IF NOT EXISTS pct_from_pre DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS pct_from_post DECIMAL(10, 4);

-- Add indexes for faster filtering
CREATE INDEX IF NOT EXISTS idx_symbol_state_pct_from_pre ON symbol_state(pct_from_pre);
CREATE INDEX IF NOT EXISTS idx_symbol_state_pct_from_post ON symbol_state(pct_from_post);
```

4. Click **RUN**
5. Verify success: You should see "Success. No rows returned"

**Verification**:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'symbol_state'
AND column_name IN ('pre_market_open', 'rth_open', 'post_market_open', 'pct_from_pre', 'pct_from_post');
```

Should return 5 rows.

---

## 🚀 Deployment Steps

### Step 2: Restart Scanner

```bash
# Stop current scanner
npm stop

# Clear any cached processes
pkill -f "python.*scanner"

# Start fresh
npm start
```

### Step 3: Monitor Scanner Logs

Watch for:
- ✅ "PRE open: $X.XX" messages during pre-market
- ✅ "RTH open: $X.XX" messages at 8:30 AM
- ✅ No database errors about missing columns
- ❌ Any errors mentioning `pre_market_open` or `pct_from_pre`

```bash
tail -f .pids/screener.log | grep -E "PRE|RTH|POST|ERROR"
```

### Step 4: Test API Endpoint

```bash
curl http://localhost:8000/symbols/leaderboard?threshold=1.0 | jq '.col_20_plus[0]'
```

**Expected output** should include:
```json
{
  "symbol": "GNTA",
  "pct_from_yesterday": 263.45,
  "pct_from_pre": 6.5,       // ← NEW
  "pct_from_open": 3.8,
  "pct_from_post": null,     // ← NEW (NULL if not post-market yet)
  "pre_market_open": 11.74,  // ← NEW
  "rth_open": 12.06,         // ← NEW
  "post_market_open": null   // ← NEW
}
```

### Step 5: Test Frontend

1. Open dashboard: http://localhost:3000
2. Check dropdown has new options:
   - % Yest
   - **% PRE** ← NEW
   - % OPEN
   - **% POST** ← NEW
   - % 15M
   - % 5M

3. Select "SHOW ALL" view
   - Should see 6 columns (previously 4)
   - % PRE and % POST columns visible
   - NULL values display as "--"

4. Select "% PRE" from dropdown
   - Table sorts by pre-market performance
   - Symbols without pre-market data show "--"

---

## 🧪 Testing Scenarios

### Test 1: Pre-Market Session (3:00-8:30 AM CST)

**When**: Scanner running before 8:30 AM

**Expected**:
- `pre_market_open` populated with first trade price
- `rth_open` = NULL (not RTH yet)
- `post_market_open` = NULL
- `pct_from_pre` calculated from pre_market_open
- `pct_from_post` = NULL

**Verification**:
```bash
curl http://localhost:8000/symbols/state | jq '.[] | select(.symbol=="GNTA") | {symbol, pre_market_open, rth_open, pct_from_pre}'
```

### Test 2: RTH Session (8:30 AM-3:00 PM CST)

**When**: Scanner running during regular hours

**Expected**:
- `pre_market_open` locked (doesn't change)
- `rth_open` populated at 8:30 AM bell
- `post_market_open` = NULL
- `pct_from_pre` calculated
- `pct_from_open` calculated
- `pct_from_post` = NULL

### Test 3: Post-Market Session (3:00-7:00 PM CST)

**When**: Scanner running after 3:00 PM

**Expected**:
- `pre_market_open` locked
- `rth_open` locked
- `post_market_open` populated at 3:00 PM
- All percentages calculated
- `pct_from_post` now available

### Test 4: Symbol Without Pre-Market Activity

**When**: Symbol only trades during RTH

**Expected**:
- `pre_market_open` = NULL
- `rth_open` populated
- `pct_from_pre` = NULL
- Frontend displays "--" for % PRE column

---

## 🐛 Troubleshooting

### Error: "column 'pre_market_open' does not exist"

**Cause**: Database migration not run

**Fix**:
1. Run Step 1 (Database Migration) above
2. Restart scanner

### Error: Frontend shows "undefined" instead of "--"

**Cause**: TypeScript interface not updated or API not returning new fields

**Fix**:
1. Verify API response includes new fields
2. Clear browser cache / hard refresh (Cmd+Shift+R)
3. Check TypeScript interface matches API response

### Scanner logs show wrong session

**Example**: Says "RTH open" at 7:00 AM

**Cause**: Timezone issue (using ET instead of CT)

**Fix**:
- Check `_get_current_session()` uses `America/Chicago`
- Verify scanner system time is correct

### % PRE shows 0% for all symbols

**Cause**: `pre_market_open` not being set

**Debug**:
```bash
# Check if baselines are being set
grep "PRE open" .pids/screener.log

# Check database
curl http://localhost:8000/symbols/state | jq '.[] | select(.pre_market_open != null) | {symbol, pre_market_open}'
```

---

## 📊 Success Metrics

### Immediate (Within 1 Hour)

- [ ] Database migration successful
- [ ] Scanner restart without errors
- [ ] API returns new fields
- [ ] Frontend displays % PRE and % POST columns
- [ ] NULL values handled gracefully

### Short-Term (Within 24 Hours)

- [ ] `pre_market_open` being set for active pre-market symbols
- [ ] `rth_open` being set at 8:30 AM bell
- [ ] Percentages calculating correctly
- [ ] No database errors in logs

### Long-Term (After 24/7 Deployment)

- [ ] Monday: PRE baselines captured at 7:00 AM (not 7:24 AM)
- [ ] Baseline accuracy improved from 70% to 90%
- [ ] Can identify pre-market movers vs RTH breakouts
- [ ] ML classifier has clean session-based features

---

## 🎯 What This Enables

### For Trading
- **Pre-market movers**: See which stocks moved in pre-market
- **RTH breakouts**: Identify stocks breaking out at open
- **Post-market catalysts**: Track after-hours momentum

### For ML Classifier (Next Phase)
- **Pattern recognition**: Pre-market pump vs RTH breakout
- **Entry timing**: Know when move happened
- **Winner isolation**: % PRE + % OPEN = classification feature

**Example**:
```
GNTA: +263% YEST, +6% PRE, +3% OPEN
→ "Gap-up holder" (high confidence)

FAKE: +200% YEST, -15% PRE, -8% OPEN
→ "Gap fade" (avoid)
```

---

## 📝 Next Steps (After This Deployment)

### Today
1. ✅ Run migration
2. ✅ Restart scanner
3. ✅ Test API
4. ✅ Test frontend
5. ⏳ Deploy to cloud for 24/7 operation

### Monday (After 24/7 Running)
1. Verify 7:00 AM pre-market baselines
2. Compare accuracy vs TradingView
3. Build baseline validation dashboard
4. Start collecting session-based patterns

### Next Week
1. Implement backfill logic for mid-session starts
2. Add data quality indicators
3. Build session transition alerts
4. Start ML classifier development

---

## 🚨 Rollback Plan

If something goes wrong:

### Quick Rollback (Frontend Only)
```bash
git checkout HEAD~1 dashboard/components/AlertsLeaderboard.tsx
npm restart
```

### Full Rollback (Scanner + Frontend)
```bash
git checkout HEAD~2 .
npm restart
```

Scanner will ignore new database columns (backward compatible).

### Database Rollback (If Needed)
```sql
ALTER TABLE symbol_state
DROP COLUMN IF EXISTS pre_market_open,
DROP COLUMN IF EXISTS rth_open,
DROP COLUMN IF EXISTS post_market_open,
DROP COLUMN IF EXISTS pct_from_pre,
DROP COLUMN IF EXISTS pct_from_post;
```

---

## ✅ Final Checklist

Before considering this deployed:

- [ ] Database migration run successfully
- [ ] Scanner restarted without errors
- [ ] API endpoint returns new fields
- [ ] Frontend shows % PRE and % POST columns
- [ ] "SHOW ALL" view displays 6 columns
- [ ] NULL values display as "--"
- [ ] Dropdown has % PRE and % POST options
- [ ] Scanner logs show session detection working
- [ ] No errors in browser console
- [ ] Mobile view still works

---

**Last Updated**: 2025-10-24 09:00 AM CST
**Status**: ✅ READY FOR DEPLOYMENT
**Next Review**: After 24 hours of 24/7 operation
