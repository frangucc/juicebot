# Momo Live Integration Guide
**Date:** 2025-10-27
**Status:** Frontend Complete, Backend Pending

---

## Overview

Momo Live is a real-time ticker bar widget that displays Momo Advanced momentum classification as bars stream in. It mirrors Murphy Live's architecture.

**Frontend Status:** ✅ Complete (ChartAgentContent.tsx)
**Backend Status:** ⏳ Needs Implementation (AI Service)

---

## Frontend Implementation (✅ Complete)

### 1. State Management
Located in `dashboard/components/ChartAgentContent.tsx`:

```typescript
const [momoLive, setMomoLive] = useState<any>(null)
const [momoHistory, setMomoHistory] = useState<Array<{
  signal: string
  action: string
  price: number
  timestamp: number
  correct: boolean | null
}>>([])
const [momoAccuracy, setMomoAccuracy] = useState<{
  lastSignalCorrect: boolean | null
  totalSignals: number
  correctSignals: number
  accuracy: number
}>({ lastSignalCorrect: null, totalSignals: 0, correctSignals: 0, accuracy: 0 })
```

### 2. WebSocket Listener
Listens on `ws://localhost:8002/events/{symbol}` for `momo_live` events:

```typescript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'event' && data.event?.type === 'momo_live') {
    const momoData = data.event
    setMomoLive(momoData)
    // Extracts signal, action, price
    // Stores in history for accuracy tracking
  }
}
```

### 3. Accuracy Evaluator
Runs every 10 seconds to evaluate signal correctness:
- Compares signal direction to actual price movement
- Requires 1%+ move after 30 seconds to mark as correct
- Tracks overall accuracy percentage

### 4. Ticker Bar UI
Displays 3 columns:
- **Left**: Direction (↑/↓/−) + Action (STRONG_BUY/BUY/WAIT/SELL/STRONG_SELL)
- **Middle**: 2 lines of details (line2, line3)
- **Right**: Accuracy stats + MOMO badge

---

## Backend Implementation (⏳ Needed)

### Required: AI Service WebSocket Emitter

The AI service (`ai-service/main.py` or equivalent) needs to emit `momo_live` events via WebSocket.

**Event Format:**

```python
{
  "type": "momo_live",
  "line1": "↑ BULLISH | STRONG_BUY",
  "line2": "Stars: ★★★★★★★ (7/7) | Confidence: 85% | Price: $1.15",
  "line3": "VWAP: VALUE (-3.2%) | Leg: 1 → 2 (65%) | Time: morning_run",
}
```

**Field Breakdown:**

#### `line1` (Direction + Action)
- Format: `{arrow} {DIRECTION} | {ACTION}`
- Direction: `BULLISH`, `BEARISH`, or `NEUTRAL`
- Action: `STRONG_BUY`, `BUY`, `WAIT`, `SELL`, `STRONG_SELL`
- Examples:
  - `"↑ BULLISH | STRONG_BUY"`
  - `"↓ BEARISH | SELL"`
  - `"− NEUTRAL | WAIT"`

#### `line2` (Primary Metrics)
- Format: `Stars: {stars} ({count}/7) | Confidence: {pct}% | Price: ${price}`
- Stars: Unicode star characters (★★★★★★★)
- Count: Number of aligned timeframes (5-7)
- Confidence: Percentage (0-100)
- Price: Current price with $ sign
- Example: `"Stars: ★★★★★★ (6/7) | Confidence: 72% | Price: $1.08"`

#### `line3` (Context Details)
- Format: `VWAP: {zone} ({distance}%) | Leg: {current} → {next} ({prob}%) | Time: {period}`
- VWAP Zone: `DEEP_VALUE`, `VALUE`, `FAIR`, `EXTENDED`, `EXTREME`
- Distance: Percentage from VWAP (can be negative)
- Current Leg: Integer (1, 2, 3, etc.)
- Next Leg: Integer
- Probability: Percentage chance of next leg
- Time Period: `premarket_early`, `morning_run`, `lunch_chop`, etc.
- Example: `"VWAP: VALUE (-3.2%) | Leg: 1 → 2 (65%) | Time: morning_run"`

---

## Implementation Steps for Backend

### Step 1: Import Momo Advanced

```python
# In ai-service/main.py or equivalent
from momo_advanced import MomoAdvanced

momo_classifier = MomoAdvanced()
```

### Step 2: Classify on Each Bar

When processing a new bar for a symbol:

```python
async def process_bar(symbol: str, bar: Bar):
    # Get yesterday's close (you likely already have this)
    yesterday_close = get_yesterday_close(symbol)

    # Get last 50+ bars
    bars = get_recent_bars(symbol, limit=50)
    current_index = len(bars) - 1

    # Run Momo classification
    momo_signal = momo_classifier.classify(
        bars=bars,
        signal_index=current_index,
        yesterday_close=yesterday_close
    )

    # Format for WebSocket emission
    event = format_momo_live_event(momo_signal, bar.close)

    # Emit to WebSocket
    await broadcast_event(symbol, event)
```

### Step 3: Format Event

```python
def format_momo_live_event(signal: MomoAdvancedSignal, price: float) -> dict:
    """Format Momo signal for WebSocket broadcast"""

    # Line 1: Direction + Action
    arrow = "↑" if signal.direction == "↑" else "↓" if signal.direction == "↓" else "−"
    direction_text = "BULLISH" if signal.direction == "↑" else "BEARISH" if signal.direction == "↓" else "NEUTRAL"
    line1 = f"{arrow} {direction_text} | {signal.action}"

    # Line 2: Stars + Confidence + Price
    stars_str = "★" * signal.stars
    conf_pct = int(signal.confidence * 100)
    line2 = f"Stars: {stars_str} ({signal.stars}/7) | Confidence: {conf_pct}% | Price: ${price:.2f}"

    # Line 3: VWAP + Leg + Time
    vwap_zone = signal.vwap_context.zone
    vwap_dist = signal.vwap_context.distance_pct
    current_leg = signal.leg_context.current_leg
    next_leg = current_leg + 1
    next_leg_prob = int(signal.leg_context.next_leg_probability * 100)
    time_period = signal.time_period.period

    line3 = f"VWAP: {vwap_zone} ({vwap_dist:+.1f}%) | Leg: {current_leg} → {next_leg} ({next_leg_prob}%) | Time: {time_period}"

    return {
        "type": "momo_live",
        "line1": line1,
        "line2": line2,
        "line3": line3
    }
```

### Step 4: Broadcast to WebSocket

```python
async def broadcast_event(symbol: str, event: dict):
    """Broadcast event to all WebSocket clients watching this symbol"""

    # Your existing WebSocket manager
    await websocket_manager.broadcast_to_symbol(symbol, {
        "type": "event",
        "event": event
    })
```

---

## Testing the Integration

### 1. Backend Emits Events
Start the AI service and verify it's emitting `momo_live` events:

```bash
# Check WebSocket messages
wscat -c ws://localhost:8002/events/BYND
```

You should see:
```json
{
  "type": "event",
  "event": {
    "type": "momo_live",
    "line1": "↑ BULLISH | STRONG_BUY",
    "line2": "Stars: ★★★★★★★ (7/7) | Confidence: 85% | Price: $1.15",
    "line3": "VWAP: VALUE (-3.2%) | Leg: 1 → 2 (65%) | Time: morning_run"
  }
}
```

### 2. Frontend Receives and Displays
Open the chart in browser:
```
http://localhost:3000/chart-agent?symbol=BYND&mode=historical
```

The Momo Live ticker bar should appear below Murphy's (if Murphy Live is also active).

### 3. Verify Accuracy Tracking
After 30 seconds, check browser console:
```
[Momo Eval] Signal @ $1.15 (BULLISH/STRONG_BUY) | Now $1.17 (+1.74%) → CORRECT ✓
[Momo Eval] Updated accuracy: {accuracy: 71.4, correctSignals: 5, totalSignals: 7}
```

---

## Trigger via Commands

### Slash Command (ChatInterface)
Type in chat:
```
/momo live
```

This shows help text explaining Momo Live.

### Alias (without slash)
Type in chat:
```
momo live
```

This should also trigger Momo Live (needs alias mapping).

---

## Differences from Murphy Live

| Feature | Murphy Live | Momo Live |
|---------|-------------|-----------|
| **Stars** | 0-4 (OI delta magnitude) | 5-7 (timeframe alignment) |
| **Signal Source** | Structure breaks (BoS/CHoCH) | Continuous momentum |
| **Action Types** | BULLISH/BEARISH/NEUTRAL | STRONG_BUY/BUY/WAIT/SELL/STRONG_SELL |
| **Context** | Volume, FVG, rejection | VWAP zone, legs, time period |
| **Badge** | Flask icon (Test Lab) | MOMO badge (purple) |

---

## Next Steps

1. ✅ Frontend complete (WebSocket listener, UI, accuracy tracker)
2. ⏳ **Backend needed**: Implement `momo_live` event emitter in AI service
3. ⏳ **Optional**: Create MomoTestModal for detailed testing (like MurphyTestModal)
4. ⏳ **Optional**: Create momo_test_recorder.py for session/signal tracking

---

## Summary

The frontend is ready to receive and display Momo Live events. The backend needs to:

1. Import `MomoAdvanced` classifier
2. Run classification on each new bar
3. Format the signal into `line1`/`line2`/`line3` format
4. Emit via WebSocket to `ws://localhost:8002/events/{symbol}`

Once the backend emits events, the Momo Live ticker bar will automatically appear and function!

---

**END OF INTEGRATION GUIDE**
