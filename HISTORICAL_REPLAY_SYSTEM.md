# Historical Data Replay System - Complete Guide

**Date:** 2025-10-25
**Feature:** WebSocket-based historical data replay for backtesting

---

## 🎯 What It Does

Replays historical 1-minute bars **one at a time** through WebSocket to simulate real-time market conditions. Perfect for:
- Backtesting trading strategies
- Testing alert logic with historical data
- Training on past market behavior
- Regression testing your scanner

---

## 🏗️ Architecture

```
┌──────────────────────┐
│  Chart Agent UI      │
│  (Browser)           │
│  - Live/Historical   │
│    dropdown          │
└──────────┬───────────┘
           │
           │ WebSocket Connection
           │ ws://localhost:8001
           ▼
┌──────────────────────┐
│  Historical WS       │
│  Server (Python)     │
│  Port: 8001          │
│  - Loads bars from   │
│    Supabase          │
│  - Streams 1/min     │
└──────────┬───────────┘
           │
           │ Query
           ▼
┌──────────────────────┐
│  Supabase            │
│  historical_bars     │
│  - BYND: 1,258 bars  │
│  - Oct 17-24, 2024   │
└──────────────────────┘
```

---

## 📁 Files Created

### 1. `historical_websocket_server.py` - WebSocket Server
**Purpose:** Standalone server that streams historical bars

**Features:**
- ✅ Loads bars from `historical_bars` table
- ✅ Streams one bar at a time (simulating real-time)
- ✅ Configurable playback speed (1x, 2x, 10x, etc.)
- ✅ Play/Pause/Reset controls
- ✅ Progress tracking
- ✅ Multi-client support

**Commands:**
- `subscribe` - Load bars for a symbol
- `play` - Start streaming
- `pause` - Pause streaming
- `reset` - Reset to beginning
- `set_speed` - Change playback speed

### 2. `dashboard/components/StockChartHistorical.tsx` - Updated Chart
**Purpose:** React component with WebSocket support

**Features:**
- ✅ Connects to historical WebSocket when in historical mode
- ✅ Displays bars as they arrive (real-time feel)
- ✅ Shows progress indicator
- ✅ Falls back to REST API for live mode
- ✅ Automatic reconnection logic

### 3. Updated Chart Agent UI
**Files Modified:**
- `dashboard/components/ChartAgentContent.tsx` - Added dropdown
- Uses `StockChartHistorical.tsx` component

---

## 🚀 How to Use

### Step 1: Start the Historical WebSocket Server

**In a new terminal:**
```bash
# Activate virtual environment
source venv/bin/activate

# Start server on port 8001
python historical_websocket_server.py --port 8001
```

**Expected Output:**
```
================================================================================
📡 Historical Data WebSocket Server
================================================================================
Port: 8001
Endpoint: ws://localhost:8001

Commands:
  - subscribe: Load historical bars for a symbol
  - play: Start replaying bars
  - pause: Pause replay
  - reset: Reset to beginning
  - set_speed: Change playback speed

Press Ctrl+C to stop
================================================================================
```

### Step 2: Start Your Main Services

**In another terminal:**
```bash
npm start
```

This starts:
- API on port 8000
- Dashboard on port 3000
- Screener

### Step 3: Open Chart Agent

**In your browser:**
```
http://localhost:3000/chart-agent?symbol=BYND
```

### Step 4: Switch to Historical Mode

1. Look for dropdown in top-right corner (next to "Chart Agent")
2. Select "Historical Data"
3. Watch as bars replay one by one! 🎬

---

## ⚡ Playback Speed Control

Default speed is **1x** (60 seconds per bar = real-time).

To change speed, send WebSocket command:
```javascript
// In browser console
ws.send(JSON.stringify({
  command: 'set_speed',
  symbol: 'BYND',
  speed: 10.0  // 10x speed = 6 seconds per bar
}))
```

**Common Speeds:**
- `0.1` = 10 minutes per bar (slow motion for analysis)
- `1.0` = 60 seconds per bar (real-time)
- `2.0` = 30 seconds per bar (2x speed)
- `10.0` = 6 seconds per bar (10x speed)
- `60.0` = 1 second per bar (60x speed, fast replay)

---

## 🎮 Control Commands

### Via WebSocket (in browser console):

```javascript
// Connect
const ws = new WebSocket('ws://localhost:8001')

// Subscribe to BYND
ws.send(JSON.stringify({
  command: 'subscribe',
  symbol: 'BYND'
}))

// Start playing
ws.send(JSON.stringify({
  command: 'play',
  symbol: 'BYND'
}))

// Pause
ws.send(JSON.stringify({
  command: 'pause',
  symbol: 'BYND'
}))

// Reset to beginning
ws.send(JSON.stringify({
  command: 'reset',
  symbol: 'BYND'
}))

// Change speed to 10x
ws.send(JSON.stringify({
  command: 'set_speed',
  symbol: 'BYND',
  speed: 10.0
}))
```

---

## 📊 Progress Display

When in historical mode, you'll see a status indicator in the top-left of the chart:

```
▶️ Bar 523 / 1258 (41.6%)
```

- **Green ▶️** = Playing
- **Gray ⏸️** = Paused
- **Bar count** = Current position
- **Percentage** = Progress through replay

---

## 🧪 Testing

### Test 1: Verify Server is Running
```bash
# In another terminal
curl http://localhost:8001
# Should get "WebSocket endpoint" response
```

### Test 2: Check Historical Data
```bash
source venv/bin/activate
python -c "
from shared.database import supabase
result = supabase.table('historical_bars').select('*', count='exact').eq('symbol', 'BYND').execute()
print(f'BYND has {result.count} historical bars')
"
```

### Test 3: Test WebSocket Connection
```bash
# Install wscat if needed: npm install -g wscat
wscat -c ws://localhost:8001

# Then send:
{"command":"subscribe","symbol":"BYND"}
{"command":"play","symbol":"BYND"}
```

---

## 🔧 Configuration

### Change Port
```bash
python historical_websocket_server.py --port 8002
```

Then update `dashboard/components/StockChartHistorical.tsx`:
```typescript
const HISTORICAL_WS_URL = 'ws://localhost:8002'
```

### Change Speed Programmatically
Edit `historical_websocket_server.py`:
```python
# Line ~125: Default speed
sleep_time = 60.0 / speed  # Adjust formula for different timing
```

---

## 📝 Server Output Example

When running, you'll see:
```
[08:45:23] 🔌 Client connected: 127.0.0.1:54321
[08:45:23] Fetching historical bars for BYND...
[08:45:23] ✓ Loaded 1258 bars for BYND
[08:45:23] 📊 127.0.0.1:54321 subscribed to BYND
[08:45:24] ▶️  Play BYND
[08:45:24] Starting replay for BYND at 1.0x speed (60.0s per bar)
[08:45:24] BYND - Bar 1/1258 (0.08%) | $6.62 | Vol: 301
[08:46:24] BYND - Bar 11/1258 (0.87%) | $6.61 | Vol: 696
[08:47:24] BYND - Bar 21/1258 (1.67%) | $6.57 | Vol: 372
...
```

---

## 🎯 Use Cases

### 1. Backtest Trading Strategy
```
1. Start historical replay at 10x speed
2. Watch your scanner trigger alerts
3. Verify alert logic works correctly
4. Compare with expected results
```

### 2. Train on Market Behavior
```
1. Replay at real-time speed (1x)
2. Try to predict next bar
3. Learn price patterns
4. Improve intuition
```

### 3. Regression Testing
```
1. Run scanner with historical feed
2. Capture all alerts
3. Compare with baseline
4. Ensure no regressions
```

### 4. Fast-Forward Through Boring Periods
```
1. Start at 60x speed
2. When interesting action appears, pause
3. Switch to 1x to study closely
4. Resume fast-forward after
```

---

## 🐛 Troubleshooting

### Issue: "Failed to connect to historical server on port 8001"
**Solution:**
```bash
# Check if server is running
ps aux | grep historical_websocket_server

# If not, start it:
source venv/bin/activate
python historical_websocket_server.py
```

### Issue: "No historical bar data found for symbol"
**Solution:**
```bash
# Check if data exists
python -c "from shared.database import supabase; print(supabase.table('historical_bars').select('*', count='exact').eq('symbol', 'BYND').execute().count)"

# If 0, run the fetch script:
python test_historical_bynd.py
```

### Issue: Replay is too slow/fast
**Solution:**
Send speed command via WebSocket or restart server with different logic.

### Issue: Chart doesn't update
**Solution:**
- Check browser console for WebSocket errors
- Verify WebSocket connection is established
- Check server logs for client connection
- Try refreshing the page

---

## 🔄 Workflow Example

**Typical Backtesting Session:**

```bash
# Terminal 1: Start historical server
source venv/bin/activate
python historical_websocket_server.py

# Terminal 2: Start main services
npm start

# Browser:
# 1. Go to http://localhost:3000/chart-agent?symbol=BYND
# 2. Switch dropdown to "Historical Data"
# 3. Watch replay!

# To speed up:
# In browser console:
ws.send(JSON.stringify({command:'set_speed',symbol:'BYND',speed:10}))
```

---

## 📈 Future Enhancements

### Short-Term:
- [ ] Add playback controls to UI (play/pause/speed buttons)
- [ ] Date range selector (replay specific dates)
- [ ] Skip to specific bar (scrubbing)
- [ ] Loop mode (replay continuously)

### Long-Term:
- [ ] Multi-symbol replay (sync multiple charts)
- [ ] Event markers (earnings, splits, etc.)
- [ ] Speed presets in UI (1x, 2x, 5x, 10x, 60x)
- [ ] Export replay to video
- [ ] Record and playback user interactions

---

## ✅ Summary

**What You Have Now:**
- ✅ Dedicated WebSocket server for historical replay
- ✅ Streams bars one at a time (60s per bar by default)
- ✅ Live/Historical dropdown in Chart Agent UI
- ✅ Progress indicator showing replay status
- ✅ 1,258 bars for BYND (Oct 17-24, 2024)
- ✅ Configurable playback speed

**How to Use:**
1. Start historical server: `python historical_websocket_server.py`
2. Start main services: `npm start`
3. Open http://localhost:3000/chart-agent?symbol=BYND
4. Switch to "Historical Data"
5. Watch the replay! 🎬

**Perfect for:**
- Backtesting strategies
- Testing alert logic
- Training and learning
- Regression testing

---

## 🎬 Ready to Test!

**Start the server when ready:**
```bash
source venv/bin/activate
python historical_websocket_server.py
```

Then open your chart and switch to historical mode! 🚀
