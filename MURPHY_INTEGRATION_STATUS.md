# Murphy Integration Status

## ✅ COMPLETED Tonight

### 1. Murphy Chat Command (`murphy`)
**Status**: WORKING PERFECTLY ✓

**What it does**:
- Type `murphy` in JuiceBot chat
- Analyzes last 50-100 bars instantly
- Returns direction (↑/↓/−), stars (****), grade ([1-10]), confidence
- Detects liquidity sweeps, rejections, patterns, FVG momentum

**Example output**:
```
🔍 Murphy Analysis - BYND @ $0.62

Direction: ↑
Rating: ↑ **** [8]
Confidence: 1.60

📊 Extreme bullish | Liquidity sweep detected (stop hunt reversal)

✨ V2 Features:
  • Liquidity Sweep: Yes
  • Rejection: bearish_rejection
```

**Files modified**:
- `ai-service/fast_classifier_v2.py` - Added `_execute_murphy()` with direct Murphy execution
- `murphy_classifier_v2.py` - Core classifier (already existed, working great)

### 2. Murphy Slash Command (`/murphy`)
**Status**: WORKING ✓

Shows help text explaining Murphy features. Type `/murphy` to see usage.

**Files modified**:
- `dashboard/components/ChatInterface.tsx:316-343` - Added to slash command list

---

## 🚧 IN PROGRESS

### 3. Murphy Labels on BoS/CHoCH Chart Lines
**Status**: CODE WRITTEN, NOT COMPILED YET

**Goal**: When BoS/CHoCH lines appear on chart, show Murphy analysis like:
- `↑ **** [8]` instead of just `↑ BoS`
- **Green** line when Murphy agrees (bullish BoS + Murphy ↑)
- **Red** line when Murphy disagrees (bullish BoS + Murphy ↓)

**Files modified**:
- `dashboard/components/StockChartHistorical.tsx:732-756` - Added Murphy calls for all 4 signal types
- `api/main.py:681-751` - Added `/murphy/classify` endpoint

**Problem**: Murphy API endpoint times out (murphy_classifier.classify() hangs)
**Workaround attempted**: Added logging to debug where it hangs

**To fix**:
1. Run `npm stop && npm start` to restart everything
2. Check browser console (F12) for Murphy call errors
3. Check `.pids/api.log` for Murphy API timeout/hang location
4. May need to optimize murphy_classifier_v2.py (FVG/liquidity detection loops)

---

## 📋 TODO: Murphy Live Ticker

### Goal
Background widget above chat input showing live Murphy updates every second:

```
MURPHY LIVE | Direction: ↑ BULLISH | Strength: STRONG **** | Grade: [8] | Confidence: 1.45
Price: $0.62 | Signal: Extreme bullish momentum with volume confirmation
Last Update: 23:45:32
```

### Implementation Plan

**Backend (AI Service)** - ✅ DONE
- Added `murphy live` command detection
- Added `_start_murphy_live()` to spawn background task
- Added `_murphy_live_worker()` that runs every 1 second
- Publishes to event_bus with 3-line updates

**Files modified**:
- `ai-service/fast_classifier_v2.py:155-245`

**Frontend (Dashboard)** - ❌ TODO
Need to add widget to `ChatInterface.tsx`:

1. **Add WebSocket listener** for Murphy Live events:
```typescript
useEffect(() => {
  const ws = new WebSocket(`ws://localhost:8002/events/${symbol}`)
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'murphy_live') {
      setMurphyLive(data)
    }
  }
  return () => ws.close()
}, [symbol])
```

2. **Add state** for Murphy Live data:
```typescript
const [murphyLive, setMurphyLive] = useState<any>(null)
```

3. **Add widget above input** (around line 1500-1600):
```typescript
{murphyLive && (
  <div className="murphy-live-ticker">
    <div className="text-xs font-mono">{murphyLive.line1}</div>
    <div className="text-xs font-mono text-gray-400">{murphyLive.line2}</div>
    <div className="text-xs font-mono text-gray-500">{murphyLive.line3}</div>
  </div>
)}
```

4. **Add CSS** for styling (monospace, 3 rows, above input)

---

## Key Files Reference

### Murphy Classifier
- `/murphy_classifier_v2.py` - Core Murphy logic (FVG, sweeps, patterns, RVOL)
- Lines 82-100: FVG detection
- Lines 201-235: Liquidity sweep detection
- Lines 237-265: Rejection analysis
- Lines 267-322: Pattern detection

### AI Service
- `/ai-service/fast_classifier_v2.py` - Fast command handler
- Lines 127-137: Murphy command routing
- Lines 155-166: Murphy Live starter
- Lines 168-245: Murphy Live worker (background task)
- Lines 247-331: Single Murphy execution

### Dashboard
- `/dashboard/components/ChatInterface.tsx` - Chat UI
- Lines 316-343: Murphy slash command definition
- Need to add: Murphy Live widget + WebSocket listener

### API
- `/api/main.py` - REST API
- Lines 681-751: Murphy classify endpoint (for chart labels)
- Lines 93-105: Murphy response model

---

## Testing Murphy

### Chat Command
```
murphy          → Current price analysis
murphy 0.66     → Specific price level
murphy live     → Start live ticker (TODO: finish frontend)
```

### Expected Behavior
- **Direction**: ↑ BULLISH, ↓ BEARISH, − NEUTRAL
- **Strength**: STRONG/MODERATE/WEAK/MINIMAL/CHOP
- **Stars**: **** (0-4 conviction)
- **Grade**: [1-10] score
- **Confidence**: Synthetic OI delta
- **V2 Features**: Sweeps, rejections, patterns, FVG momentum

---

## Next Steps

1. **Fix chart labels** (Murphy on BoS/CHoCH):
   - Debug why Murphy API times out
   - Or bypass API and use direct Murphy execution (like chat command does)

2. **Complete Murphy Live frontend**:
   - Add WebSocket listener in ChatInterface
   - Add 3-row widget above chat input
   - Style like scaleout progress widget
   - Test with `murphy live` command

3. **Optimization** (if Murphy is slow):
   - Profile murphy_classifier_v2.py
   - Optimize FVG detection loop (currently 50-bar lookback)
   - Cache recent Murphy results for same price level

---

## Performance Notes

Murphy currently analyzes:
- Last 100 bars
- 50-bar FVG lookback
- 10-bar liquidity sweep detection
- 14-bar ATR calculation
- 3-bar pattern recognition

**Total processing**: ~150 bar lookups
**Current speed**: Works instantly in AI service, times out in API
**Likely culprit**: FVG detection nested loops or statistics.mean() calls

---

**End of session summary. Murphy chat command is WORKING GREAT! 🎉**
