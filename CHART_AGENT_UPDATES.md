# Chart Agent Updates - Live/Historical Data Toggle

**Date:** 2025-10-25
**Feature:** Added dropdown to switch between live and historical data views

---

## ✅ What Was Implemented

### 1. New API Endpoint (`api/main.py:275-309`)
Added `/bars/{symbol}/historical` endpoint to fetch historical bar data:

```python
@app.get("/bars/{symbol}/historical")
async def get_historical_bars(symbol: str, limit: int = 500):
    """Get historical 1-minute OHLCV bars from historical_bars table."""
    # Queries historical_bars table instead of price_bars
    # Returns up to 2000 bars for backtesting
```

**Features:**
- Fetches from `historical_bars` table (our regression testing data)
- Supports up to 2000 bars (vs 1000 for live)
- Same data format as live endpoint for compatibility

### 2. Updated Chart Agent UI (`dashboard/components/ChartAgentContent.tsx`)
Added dropdown selector in the header:

```tsx
<select
  value={dataMode}
  onChange={(e) => setDataMode(e.target.value as 'live' | 'historical')}
  className="bg-gray-800 text-gray-300..."
>
  <option value="live">Live Data</option>
  <option value="historical">Historical Data</option>
</select>
```

**Location:** Far right of header, next to "Chart Agent" label

### 3. Updated Stock Chart Component (`dashboard/components/StockChart.tsx`)
Modified to handle both data modes:

```tsx
// Added dataMode prop
interface StockChartProps {
  symbol: string
  dataMode?: 'live' | 'historical'
}

// Dynamic endpoint selection
const endpoint = dataMode === 'historical'
  ? `${API_URL}/bars/{symbol}/historical?limit=1000`
  : `${API_URL}/bars/{symbol}?limit=500`

// Only poll for live data
if (dataMode === 'live') {
  intervalId = setInterval(fetchData, 5000)
}
```

**Behavior:**
- **Live Mode:** Fetches from `price_bars`, updates every 5 seconds
- **Historical Mode:** Fetches from `historical_bars`, loads once (no polling)

---

## 🎯 How It Works

### User Workflow:
1. Navigate to http://localhost:3000/chart-agent?symbol=BYND
2. See dropdown in top-right corner (default: "Live Data")
3. Switch to "Historical Data" to view BYND Oct 17-24, 2024 data
4. Chart instantly updates with historical bars

### Data Flow:
```
┌─────────────────┐
│  User selects   │
│  "Historical"   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ChartAgentContent│
│  dataMode state │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  StockChart     │
│  fetches from   │
│  /historical    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API queries    │
│ historical_bars │
│  table          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Chart displays │
│  1258 bars for  │
│  BYND Oct 17-24 │
└─────────────────┘
```

---

## 📊 Current Data Availability

### Live Data (`price_bars` table):
- **BYND:** 201 bars (recent trading)
- **Source:** Live scanner with TRADES schema
- **Updates:** Real-time, every minute
- **Volume:** Real trade volume

### Historical Data (`historical_bars` table):
- **BYND:** 1,258 bars (Oct 17-24, 2024)
- **Source:** Databento historical fetch
- **Updates:** Static (no updates)
- **Volume:** Real trade volume (465,894 total)

---

## 🐛 Known Issues & Debugging

### Issue 1: API Requests Timing Out
**Symptom:**
- HTTP requests to API hang/timeout after 5-10 seconds
- Affects both `/bars/{symbol}` and `/bars/{symbol}/historical`
- Direct Supabase queries work fine (0.16s)

**Possible Causes:**
1. **Async/Sync mismatch** - FastAPI endpoint might be blocking
2. **Connection pool exhaustion** - Supabase client might be depleted
3. **Event loop blocking** - Some synchronous code in async context

**Debugging Steps:**
```bash
# Test direct Supabase query (works fine)
python -c "from shared.database import supabase; print(supabase.table('historical_bars').select('*').eq('symbol', 'BYND').limit(2).execute().data)"

# Test API endpoint (times out)
curl -m 10 'http://localhost:8000/bars/BYND/historical?limit=2'

# Check API logs
tail -f .pids/api.log
```

**Recommended Fixes:**
1. **Add async/await to Supabase calls:**
   ```python
   # Current (blocking)
   response = supabase.table("historical_bars").select("*")...

   # Fix (non-blocking)
   response = await supabase.table("historical_bars").select("*")...
   ```

2. **Add timeout to Supabase client:**
   ```python
   from shared.database import supabase
   supabase.postgrest.session.timeout = (5, 30)  # connect, read
   ```

3. **Use FastAPI dependency injection:**
   ```python
   async def get_db():
       # Create fresh client per request
       pass
   ```

### Issue 2: Chart Shows "Failed to Fetch"
**Symptom:**
- Chart page loads but shows error
- Console shows network timeout

**Workaround:**
- Browser directly accessing http://localhost:3000/chart-agent?symbol=BYND
- Should work if API timeout is fixed

---

## 🧪 Testing

### Test Historical Endpoint Directly:
```bash
# Activate venv first
source venv/bin/activate

# Test with Python
python -c "
import requests
response = requests.get('http://localhost:8000/bars/BYND/historical', params={'limit': 5})
print(f'Status: {response.status_code}')
print(f'Bars: {len(response.json())}')
"
```

### Test in Browser:
1. Open http://localhost:3000/chart-agent?symbol=BYND
2. Check browser console for errors
3. Try switching dropdown between "Live Data" and "Historical Data"

### Verify Data:
```bash
# Check what data exists
python -c "
from shared.database import supabase

# Live data
live = supabase.table('price_bars').select('*', count='exact').eq('symbol', 'BYND').execute()
print(f'Live bars: {live.count}')

# Historical data
hist = supabase.table('historical_bars').select('*', count='exact').eq('symbol', 'BYND').execute()
print(f'Historical bars: {hist.count}')
"
```

---

## 📝 Files Modified

1. **`api/main.py`** - Added `/bars/{symbol}/historical` endpoint
2. **`dashboard/components/ChartAgentContent.tsx`** - Added dropdown UI
3. **`dashboard/components/StockChart.tsx`** - Added dataMode prop and logic

---

## 🚀 Next Steps

### Immediate (Fix API Timeout):
1. Debug why API requests hang
2. Add proper async/await to Supabase calls
3. Test endpoint returns data successfully

### Short-Term (Enhance UI):
1. Add loading indicator when switching modes
2. Show data source info ("Showing 1,258 historical bars from Oct 17-24")
3. Add date range picker for historical data
4. Disable dropdown if no historical data exists

### Long-Term (Add Features):
1. **Compare Mode:** Overlay live and historical charts
2. **Date Picker:** Select custom historical date ranges
3. **Export:** Download historical data as CSV
4. **Analytics:** Show volume analysis, price patterns
5. **Multi-Symbol:** Compare multiple symbols side-by-side

---

## 💡 Usage Examples

### For Backtesting:
```
1. Switch to "Historical Data"
2. View BYND price action from Oct 17-24
3. Analyze volume patterns
4. Test trading strategies
```

### For Regression Testing:
```
1. Run scanner with historical data
2. Switch chart to "Historical Data"
3. Verify alert logic triggers correctly
4. Compare with expected results
```

### For Strategy Development:
```
1. Identify interesting price patterns in historical view
2. Switch to live view to see current behavior
3. Develop rules based on patterns
4. Backtest with historical data
```

---

## ✅ Summary

**What Works:**
- ✅ Dropdown added to Chart Agent UI
- ✅ Historical bars API endpoint created
- ✅ StockChart component updated for both modes
- ✅ Database has 1,258 historical bars for BYND
- ✅ Direct Supabase queries work perfectly

**What Needs Fixing:**
- ❌ API requests timeout (need to fix async/await)
- ❌ Chart can't load data until API timeout is resolved

**Expected Result After Fix:**
- User can switch between live and historical data seamlessly
- Historical mode shows Oct 17-24, 2024 data for BYND
- Live mode shows current trading data
- No performance issues or timeouts

---

## 🔧 Quick Fix Commands

```bash
# Restart services
npm stop && npm start

# Test historical endpoint
curl -m 5 'http://localhost:8000/bars/BYND/historical?limit=5'

# Check logs
tail -f .pids/api.log

# Test in browser
open http://localhost:3000/chart-agent?symbol=BYND
```

---

The infrastructure is 95% complete - just needs the API timeout issue resolved!
