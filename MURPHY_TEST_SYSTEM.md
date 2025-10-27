# Murphy Test System Documentation

## Overview

The Murphy Test System is a comprehensive recording and evaluation framework for optimizing Murphy's signal classifier. It records **ALL** signals (both displayed and filtered), evaluates them at multiple timeframes, and provides detailed analytics to help fine-tune filter thresholds and improve accuracy.

## Problem It Solves

**Before:** Murphy was producing too many signals, but we had no data to determine:
- Are the filters too loose or too strict?
- What's the accuracy of signals we're showing vs. signals we're filtering out?
- Are we filtering out good signals or correctly removing noise?
- What filter thresholds produce optimal results?

**After:** Complete visibility into every signal with multi-timeframe evaluation to make data-driven decisions about filter optimization.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Murphy Live Worker                          │
│  - Generates signals every 1 second                             │
│  - Applies filters (stars >= 3, grade >= 7, etc.)              │
│  - Records ALL signals to database (passed + filtered)          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ Records to
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                     Database Tables                              │
│  - murphy_test_sessions: Test session metadata + metrics        │
│  - murphy_signal_records: Every signal with evaluations         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ Evaluated by
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                  Murphy Test Evaluator                           │
│  - Background worker (runs every 10 seconds)                    │
│  - Evaluates signals at: 2min, 5min, 10min, 30min              │
│  - Marks signals as correct/wrong based on price movement       │
│  - Updates session accuracy metrics                             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      │ Displayed by
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                  Frontend Test Modal                             │
│  - Real-time dashboard of test session                          │
│  - Table showing all signals + evaluations                      │
│  - Comparison: Displayed vs Filtered accuracy                   │
│  - Controls to start/stop test sessions                         │
└─────────────────────────────────────────────────────────────────┘
```

## Database Schema

### `murphy_test_sessions`
Tracks test sessions with configuration and aggregated metrics.

**Key Fields:**
- `id`: Session UUID
- `symbol`: Stock symbol being tested
- `status`: 'active', 'completed', 'cancelled'
- `config`: Filter configuration (thresholds, sticky direction, etc.)
- `metrics`: Aggregated stats (total signals, accuracy, avg grade, etc.)

### `murphy_signal_records`
Records every signal Murphy generates.

**Key Fields:**
- `session_id`: Links to test session
- `direction`, `stars`, `grade`, `confidence`: Signal properties
- `passed_filter`: TRUE if shown in UI, FALSE if filtered out
- `filter_reason`: Why it was filtered (e.g., "below threshold: ** [6]")
- `eval_2min`, `eval_5min`, `eval_10min`, `eval_30min`: Price evaluations
- `final_result`: 'correct' | 'wrong' | 'pending'

## How Signal Evaluation Works

1. **Signal Generation:** Murphy analyzes current market conditions every second
2. **Filter Application:** Checks if signal meets thresholds (stars >= 3, grade >= 7, etc.)
3. **Recording:** Both passed and filtered signals are saved to database
4. **Evaluation Timeline:**
   - **2 minutes:** First check - did price move correctly?
   - **5 minutes:** Medium-term validation
   - **10 minutes:** Extended validation
   - **30 minutes:** FINAL evaluation - marks signal as correct/wrong

5. **Correctness Criteria:**
   - BULLISH signal: Price must increase by >= 0.3%
   - BEARISH signal: Price must decrease by >= 0.3%
   - < 0.3% move: Considered neutral/no result

## Usage Guide

### 1. Apply Database Schema

```bash
# Option A: Via Supabase SQL Editor (Recommended)
# 1. Go to Supabase Dashboard → SQL Editor
# 2. Copy contents of database/murphy_test_schema.sql
# 3. Paste and execute

# Option B: Via Python script (limited - may need manual execution)
python database/apply_murphy_schema.py
```

### 2. Start the Services

```bash
# Start all services (includes evaluator)
npm start

# The evaluator runs automatically as part of the AI service
```

### 3. Using the Test Lab

1. **Open Chart Agent:** Navigate to `/chart-agent?symbol=AAPL`

2. **Wait for Murphy Live:** Murphy widget should appear showing live signals

3. **Open Test Lab:** Click the flask icon (🧪) in the Murphy accuracy column

4. **Start Test Session:** Click "START TEST SESSION" button

5. **Monitor Results:**
   - Table shows all signals (displayed + filtered)
   - Real-time evaluation at 2min, 5min, 10min, 30min
   - Green ✓ = correct prediction
   - Red ✗ = wrong prediction
   - Gray ... = pending evaluation

6. **Analyze Metrics:**
   - **Displayed Accuracy:** How accurate are the signals we show users?
   - **Filtered Accuracy:** How accurate are the signals we're hiding?
   - **If filtered accuracy > displayed accuracy:** Filters are TOO STRICT (we're filtering good signals)
   - **If displayed accuracy < 60%:** Filters are TOO LOOSE (showing bad signals)

7. **End Session:** Click "END SESSION" when done

### 4. Optimizing Filters

Based on test results, adjust filters in `fast_classifier_v2.py`:

```python
# Current filters (lines 243-247)
is_significant = (
    signal.stars >= 3 or      # ← Try adjusting this
    signal.grade >= 7 or      # ← Try adjusting this
    abs(signal.confidence) >= 1.0  # ← Try adjusting this
)
```

**Optimization Strategy:**
1. Run test session for 1-2 hours
2. Check metrics in Test Lab modal
3. If filtered accuracy is high (> displayed): **Loosen** filters (lower thresholds)
4. If displayed accuracy is low (< 60%): **Tighten** filters (higher thresholds)
5. Restart services and run new test session
6. Compare results between sessions

## API Endpoints

### Session Management

```bash
# Create new test session
POST /murphy-test/sessions
Body: {
  "symbol": "AAPL",
  "config": {
    "min_stars": 3,
    "min_grade": 7,
    "min_confidence": 1.0
  },
  "notes": "Testing new filter thresholds"
}

# Get active session for symbol
GET /murphy-test/sessions/{symbol}/active

# Get session by ID
GET /murphy-test/sessions/{session_id}

# End session
POST /murphy-test/sessions/{session_id}/end
Body: { "status": "completed" }

# Get signals for session
GET /murphy-test/sessions/{session_id}/signals?limit=100&passed_filter=true

# Get recent sessions
GET /murphy-test/sessions?symbol=AAPL&limit=10
```

## Key Files

### Backend
- `ai-service/murphy_test_recorder.py` - Session and signal recording
- `ai-service/murphy_test_evaluator.py` - Background evaluation worker
- `ai-service/fast_classifier_v2.py` - Murphy live worker (integrated recording)
- `api/main.py` - REST API endpoints (lines 799-949)
- `database/murphy_test_schema.sql` - Database schema

### Frontend
- `dashboard/components/MurphyTestModal.tsx` - Test Lab UI
- `dashboard/components/ChartAgentContent.tsx` - Flask icon integration

## Troubleshooting

### No Signals Recording

**Check:**
1. Is there an active test session? (Click flask icon → "START TEST SESSION")
2. Is Murphy Live running? (Widget should show in chart area)
3. Check console logs: `[Murphy Test] Recorded signal...`

### Evaluations Not Updating

**Check:**
1. Is the evaluator running? Should see: `[Murphy Evaluator] Starting...` in logs
2. Are signals old enough? (Needs at least 2 minutes for first evaluation)
3. Is current price available? (Evaluator fetches from `symbol_state`)

### Modal Not Opening

**Check:**
1. Flask icon visible in Murphy widget accuracy column?
2. Browser console for React errors
3. Ensure `MurphyTestModal.tsx` is imported in `ChartAgentContent.tsx`

## Current Filter Logic

Murphy Live uses "sticky directional logic" with these rules:

1. **Base Threshold:** Signal must have:
   - stars >= 3 OR
   - grade >= 7 OR
   - confidence >= 1.0

2. **First Signal:** Always publish (establish baseline)

3. **Same Direction:** Only publish if STRONGER
   - Higher grade OR more stars than last signal

4. **Direction Flip:** Only publish if HIGH CONVICTION
   - grade >= 7 OR stars >= 3

This prevents signal spam while ensuring important changes are shown.

## Metrics Explained

### Session Metrics

- **Total Signals Generated:** Every signal Murphy produced (filtered + displayed)
- **Signals Displayed:** Signals that passed filters and shown in UI
- **Signals Filtered:** Signals blocked by filters
- **Accuracy (Displayed):** % of displayed signals that were correct
- **Accuracy (Filtered):** % of filtered signals that would have been correct
- **Avg Grade:** Average grade of signals in each category

### Ideal Metrics

**Good Filter Performance:**
- Displayed Accuracy: >= 65%
- Filtered Accuracy: <= 50%
- This means filters are successfully removing bad signals

**Poor Filter Performance (Too Strict):**
- Displayed Accuracy: 70%
- Filtered Accuracy: 70%
- We're filtering out good signals!

**Poor Filter Performance (Too Loose):**
- Displayed Accuracy: 45%
- Filtered Accuracy: 40%
- Too much noise getting through!

## Next Steps

1. ✅ Apply database schema
2. ✅ Restart services
3. ✅ Start test session on active symbol
4. ✅ Monitor for 1-2 hours
5. ⏳ Analyze results in Test Lab
6. ⏳ Adjust filter thresholds
7. ⏳ Run A/B tests with different configurations
8. ⏳ Document optimal settings

## Future Enhancements

- [ ] A/B testing framework (run multiple configs simultaneously)
- [ ] Historical session comparison charts
- [ ] Export test results to CSV
- [ ] Automated threshold optimization (ML-based)
- [ ] Per-symbol filter tuning
- [ ] Integration with position entry/exit logic
