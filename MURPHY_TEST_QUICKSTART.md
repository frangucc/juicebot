# Murphy Test System - Quick Start Guide

## 🎯 What You'll Get

A complete testing and optimization system for Murphy that:
- ✅ Records EVERY signal (filtered + displayed)
- ✅ Evaluates signals at 2min, 5min, 10min, 30min
- ✅ Shows accuracy comparison: displayed vs filtered
- ✅ Helps you fine-tune filter thresholds
- ✅ Real-time dashboard with all test data

## 🚀 Setup (5 minutes)

### Step 1: Apply Database Schema

**Option A: Supabase SQL Editor (Recommended)**
1. Open Supabase Dashboard → SQL Editor
2. Open file: `database/murphy_test_schema.sql`
3. Copy the entire contents
4. Paste into SQL Editor
5. Click "Run"

**Option B: Using psql (if you have direct access)**
```bash
psql <your-connection-string> -f database/murphy_test_schema.sql
```

### Step 2: Verify Tables Created

Run this query in Supabase SQL Editor:
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'murphy%';
```

You should see:
- `murphy_test_sessions`
- `murphy_signal_records`

### Step 3: Restart Services

```bash
npm stop
npm start
```

Look for these startup messages:
```
[AI Service] 🚀 Starting WebSocket client for bar data...
[AI Service] 🧪 Starting Murphy test evaluator...
[Murphy Evaluator] Starting background evaluator...
```

## 📊 Using the Test Lab

### 1. Open Chart Agent
Navigate to: `http://localhost:3000/chart-agent?symbol=AAPL`

### 2. Wait for Murphy Live
You should see the Murphy widget appear above the chart showing real-time signals.

### 3. Open Test Lab
Click the **flask icon (🧪)** in the Murphy widget (far right of accuracy column).

A full-screen modal will open with the test dashboard.

### 4. Start Recording
Click the green **"START TEST SESSION"** button.

You'll see:
- Session start time
- Real-time metrics updating
- Signals appearing in the table as Murphy generates them

### 5. Monitor Results

**Metrics Panel:**
- **Total Signals:** Everything Murphy generated
- **Displayed / Filtered:** How many passed/failed filters
- **Accuracy (Displayed):** % correct of signals shown to users
- **Accuracy (Filtered):** % correct of signals we hid

**Signals Table:**
- Each row = one signal
- **Status:** ✓ SHOWN (passed filters) or ✗ HIDDEN (filtered out)
- **2min, 5min, 10min, 30min:** Price movement evaluation
  - Green ✓ = Correct prediction
  - Red ✗ = Wrong prediction
  - Gray ... = Pending evaluation
- **Result:** Final verdict (after 30min)
- **Reason:** Why signal was filtered (if hidden)

### 6. Let It Run

**Recommended:** Let test session run for 1-2 hours to collect meaningful data.

- Auto-refresh is enabled by default (updates every 5 seconds)
- You can switch between tabs: All / Displayed / Filtered
- Metrics update in real-time as signals are evaluated

### 7. Analyze Results

**Good Filters (What You Want):**
```
Displayed Accuracy: 65%+
Filtered Accuracy:  < 50%
```
→ Filters are working! Showing good signals, hiding bad ones.

**Filters Too Strict:**
```
Displayed Accuracy: 70%
Filtered Accuracy:  70%
```
→ We're filtering out good signals! Loosen thresholds.

**Filters Too Loose:**
```
Displayed Accuracy: 45%
Filtered Accuracy:  40%
```
→ Too much noise! Tighten thresholds.

### 8. End Session

Click red **"END SESSION"** button when done.

Session will be marked as completed and saved for historical comparison.

## 🔧 Optimizing Filters

### Current Filter Logic

Located in: `ai-service/fast_classifier_v2.py` (lines 243-247)

```python
is_significant = (
    signal.stars >= 3 or           # ← Adjust this
    signal.grade >= 7 or           # ← Adjust this
    abs(signal.confidence) >= 1.0  # ← Adjust this
)
```

### Example Adjustments

**If too many signals:**
```python
# More strict - only high-quality signals
is_significant = (
    signal.stars >= 4 or           # Changed: 3 → 4
    signal.grade >= 8 or           # Changed: 7 → 8
    abs(signal.confidence) >= 1.5  # Changed: 1.0 → 1.5
)
```

**If filtering out too many good signals:**
```python
# More lenient - allow more signals through
is_significant = (
    signal.stars >= 2 or           # Changed: 3 → 2
    signal.grade >= 6 or           # Changed: 7 → 6
    abs(signal.confidence) >= 0.8  # Changed: 1.0 → 0.8
)
```

### Testing Process

1. Make filter adjustment in `fast_classifier_v2.py`
2. Restart services: `npm stop && npm start`
3. Start new test session
4. Run for 1-2 hours
5. Compare metrics with previous session
6. Iterate until accuracy is optimized

## 🐛 Troubleshooting

### "No signals recording"

**Check:**
1. Test session started? (Green button says "END SESSION")
2. Murphy Live running? (Widget visible above chart)
3. Console logs show: `[Murphy Test] Recorded signal...`

**Fix:**
```bash
# Restart services
npm stop
npm start
```

### "Evaluations stuck at pending"

**Check:**
1. Evaluator running? Look for: `[Murphy Evaluator] Starting...`
2. Signals at least 2 minutes old?
3. Price data available? Check `symbol_state` table has recent data

**Fix:**
```bash
# Check if evaluator is running
# Should see logs like: "[Murphy Evaluator] Found X active sessions"
# If not, restart services
```

### "Modal won't open"

**Check:**
1. Flask icon visible in Murphy widget?
2. Browser console for errors (F12 → Console)

**Fix:**
```bash
# Rebuild frontend
cd dashboard
npm install
npm run dev
```

### "Database schema errors"

**Error:** `relation "murphy_test_sessions" does not exist`

**Fix:**
1. Schema wasn't applied correctly
2. Go to Supabase Dashboard → SQL Editor
3. Copy contents of `database/murphy_test_schema.sql`
4. Paste and run

## 📈 What to Watch For

### First 30 minutes
- Signals should start appearing immediately
- First evaluations (2min) should start ~2 minutes after first signal
- Metrics will be sparse initially

### After 1 hour
- Should have 20-50 signals (depending on volatility)
- Multiple evaluations per signal (2min, 5min, 10min)
- Some signals reaching final (30min) evaluation
- Accuracy trends becoming visible

### After 2+ hours
- 50-100+ signals
- Most signals have full evaluation chain
- Clear accuracy patterns emerge
- Enough data to make optimization decisions

## 🎓 Understanding the Sticky Filter

Murphy uses "sticky directional logic" to reduce noise:

**Rules:**
1. **First signal:** Always show (establish baseline)
2. **Same direction:** Only show if STRONGER (higher grade/stars)
3. **Direction flip:** Only show if HIGH CONVICTION (grade >= 7 or stars >= 3)

**Why?**
Prevents rapid flip-flopping while ensuring important changes are visible.

**Example:**
```
Signal 1: ↑ *** [7] → SHOWN (first signal)
Signal 2: ↑ ** [6]  → HIDDEN (same direction, weaker)
Signal 3: ↑ **** [8] → SHOWN (same direction, stronger!)
Signal 4: ↓ ** [5]  → HIDDEN (flip but weak conviction)
Signal 5: ↓ *** [8] → SHOWN (flip with high conviction)
```

## 📊 Sample Test Session

```
Duration: 2 hours
Symbol: AAPL

Results:
├─ Total Signals: 87
├─ Displayed: 23 (26%)
├─ Filtered: 64 (74%)
│
├─ Displayed Accuracy: 69.6% (16/23)
├─ Filtered Accuracy: 51.6% (33/64)
│
└─ Conclusion: Filters working well!
   Showing mostly good signals, hiding mostly noise.
```

## 🎯 Success Criteria

You've successfully optimized Murphy when:

✅ **Displayed Accuracy >= 65%** (most shown signals are correct)
✅ **Filtered Accuracy < Displayed Accuracy** (filters removing bad signals)
✅ **Signal Volume Manageable** (not overwhelming users)
✅ **High-conviction Signals Captured** (not missing major moves)

## 📝 Next Steps After Setup

1. ✅ Run baseline test (current filters, 2 hours)
2. ⏳ Document baseline metrics
3. ⏳ Make ONE filter adjustment
4. ⏳ Run new test (2 hours)
5. ⏳ Compare results
6. ⏳ Iterate until optimal
7. ⏳ Test on multiple symbols
8. ⏳ Deploy optimized configuration

## 💡 Pro Tips

- **Run during market hours** for meaningful data
- **Test volatile stocks first** (more signals = faster data collection)
- **Change one parameter at a time** (scientific method!)
- **Keep notes** on each test session configuration
- **Compare sessions** to see improvement trends
- **Run overnight tests** for long-term accuracy validation

---

**Need Help?**
- Full documentation: `MURPHY_TEST_SYSTEM.md`
- Architecture details: See "Architecture" section in main docs
- API reference: See "API Endpoints" section

**Ready to optimize Murphy!** 🚀
