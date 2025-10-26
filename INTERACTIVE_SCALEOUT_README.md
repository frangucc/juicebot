# Interactive Scaleout & Pub-Sub Architecture

## Overview

New interactive command system with real-time progress updates streaming to chat. This architecture enables multi-turn conversations and background workers that publish events back to the chat interface.

---

## Features Implemented

### 1. Interactive Scaleout Command

**User Flow:**
```
User: scaleout
Bot: 📉 INTERACTIVE SCALEOUT
     Position: LONG 3750 @ $0.63

     How fast should I scale out?
       1️⃣  FAST - Next 1-3 minutes (6-10 chunks)
       2️⃣  MEDIUM - Next 10-15 minutes (8-12 chunks)
       3️⃣  SLOW - Next hour (10-15 chunks)

     💡 Reply with 1, 2, or 3

User: 1

Bot: 🔄 SCALEOUT INITIATED
     Mode: FAST (1-3 minutes)
     Total Quantity: 3,750
     Chunks: 8
     Entry: $0.63
     💡 Progress updates will appear automatically

[10 seconds later]
Bot: ✓ Chunk 1/8: Sold 468 @ $1.01
     P&L: $+177.84 | Remaining: 3,282 | Total P&L: $+177.84

[25 seconds later]
Bot: ✓ Chunk 2/8: Sold 468 @ $1.02
     P&L: $+182.52 | Remaining: 2,814 | Total P&L: $+360.36

... continues until complete ...

[Final chunk]
Bot: 🎉 SCALEOUT COMPLETE
     Final Chunk: 468 @ $1.03
     Total P&L: $+1,458.99
     Position: FLAT
```

### 2. New `/trade pl` Command

Shows focused P&L summary:
```
User: pl

Bot: 💰 P&L SUMMARY - BYND
     Open: LONG 3,750 @ $0.63
     Current: $1.01
     Unrealized P&L: $+1,422.38 (+60.14%)
     Realized P&L: $+36.61
     ━━━━━━━━━━━━━━━━━━━━━━
     Master P&L: $+1,458.99
```

**Aliases:**  `pl`, `pnl`, `profit`

---

## Architecture Components

### 1. Event Bus (`event_bus.py`)

Global pub-sub system for real-time chat updates.

**Key Methods:**
```python
# Subscribe to events
event_bus.subscribe(symbol, conversation_id, websocket)

# Publish events from anywhere
await event_bus.publish(symbol, {
    "type": "scaleout_progress",
    "message": "✓ Sold 500 @ $0.65 | P&L: +$125.00",
    "data": {...}
})

# Manage background tasks
event_bus.register_task(symbol, "scaleout", asyncio_task)
event_bus.cancel_task(symbol, "scaleout")
```

**Event Types:**
- `scaleout_start` - Scaleout begins
- `scaleout_progress` - Each chunk sold
- `scaleout_complete` - All chunks sold
- `scaleout_cancelled` - User cancelled
- `scaleout_error` - Error occurred

**Event History:**
- Stores last 50 events per symbol
- Allows new subscribers to catch up

### 2. Scaleout Worker (`scaleout_worker.py`)

Background worker that gradually exits positions over time.

**Speed Modes:**
| Mode | Duration | Chunks | Delay Between Chunks |
|------|----------|--------|---------------------|
| Fast | 1-3 min | 6-10 | 10-30 seconds |
| Medium | 10-15 min | 8-12 | 60-120 seconds |
| Slow | 60 min | 10-15 | 240-480 seconds (4-8 min) |

**Key Methods:**
```python
worker = ScaleoutWorker(user_id=user_id)

# Start scaleout
await worker.start_scaleout(
    symbol="BYND",
    speed="fast",  # fast, medium, or slow
    quantity=None  # None = all
)

# Cancel active scaleout
await worker.cancel_scaleout(symbol="BYND")

# Check status
status = worker.get_scaleout_status(symbol="BYND")
```

**How It Works:**
1. Spawns async background task
2. Calculates chunk sizes (e.g., 3750 shares / 8 chunks = ~468 per chunk)
3. Sells chunks at random intervals within delay range
4. Publishes progress event after each chunk
5. Updates database position after each sale
6. Completes when all chunks sold

### 3. Conversation State (`conversation_state.py`)

Tracks multi-turn conversation state for interactive commands.

**Usage:**
```python
from conversation_state import conversation_state

# Set state when prompting user
conversation_state.set_state(
    conversation_id=conversation_id,
    symbol=symbol,
    command='scaleout_speed_selection',
    context={'quantity': 3750}
)

# Check state on next message
state = conversation_state.get_state(conversation_id)
if state and state['command'] == 'scaleout_speed_selection':
    # User is responding to prompt
    speed = parse_speed_choice(message)
    execute_scaleout(symbol, speed)

# Clear state when done
conversation_state.clear_state(conversation_id)
```

**Features:**
- 5-minute timeout for stale states
- Per-conversation tracking
- Context storage for passing data between turns

### 4. Updated Trade Command Executor

**New Parameters:**
```python
TradeCommandExecutor(
    user_id=user_id,
    conversation_id=conversation_id  # NEW!
)
```

**New Methods:**
```python
# Interactive scaleout prompt
async def scale_out_position(symbol, params):
    # Sets conversation state
    # Returns prompt for speed selection
    ...

# Execute scaleout with chosen speed
async def execute_scaleout_with_speed(symbol, speed):
    # Starts background worker
    # Clears conversation state
    ...

# New P&L command
async def get_pnl_summary(symbol, params):
    # Returns formatted P&L display
    ...
```

### 5. Updated Fast Classifier

**Conversation-Aware Classification:**
```python
classifier = TradingClassifierV2(
    user_id=user_id,
    conversation_id=conversation_id  # NEW!
)

# Checks conversation state FIRST
state = conversation_state.get_state(conversation_id)
if state and state['command'] == 'scaleout_speed_selection':
    # User is responding to prompt
    if message in ['1', '2', '3', 'fast', 'medium', 'slow']:
        return execute_scaleout_with_speed(...)
```

**Priority Order:**
1. Check conversation state (interactive responses)
2. Try indicators (vp, rvol, vwap)
3. Try trade commands (database-driven)
4. Fall back to LLM

---

## Database Changes

### New Command

Added `/trade pl` command:
```sql
INSERT INTO trade_commands (command, handler_function, description, category, is_implemented)
VALUES ('/trade pl', 'get_pnl_summary', 'Show P&L summary', 'position', TRUE);
```

### New Aliases
- `pl` → `/trade pl`
- `pnl` → `/trade pl`
- `profit` → `/trade pl`

---

## Integration Points

### 1. Main.py Changes

**Conversation-Aware Classifiers:**
```python
# Old: Single classifier per symbol
classifiers[symbol] = TradingClassifier()

# New: Classifier per symbol + conversation
conversation_id = msg.conversation_id or f"conv_{symbol}_{timestamp}"
classifier_key = f"{symbol}:{conversation_id}"
classifiers[classifier_key] = TradingClassifier(conversation_id=conversation_id)
```

**Why:** Enables per-conversation state tracking for interactive commands.

### 2. WebSocket Integration (TODO)

To receive real-time progress updates in the frontend:

```typescript
// Subscribe to events
websocket.on('event', (data) => {
  if (data.event.type === 'scaleout_progress') {
    // Append progress message to chat
    addChatMessage(data.event.message);
  }
});
```

**Backend WebSocket Handler (TODO):**
```python
@app.websocket("/events/{symbol}")
async def event_stream(websocket: WebSocket, symbol: str):
    await websocket.accept()

    # Subscribe to events
    conversation_id = websocket.headers.get('conversation-id')
    event_bus.subscribe(symbol, conversation_id, websocket)

    # Keep connection open
    try:
        while True:
            await websocket.receive_text()  # Keep alive
    finally:
        event_bus.unsubscribe(symbol, conversation_id)
```

---

## Use Cases Beyond Scaleout

This architecture enables many interactive flows:

### 1. Interactive Close Command
```
User: close
Bot: Close at market or limit price?
     1️⃣  Market - Close immediately
     2️⃣  Limit - Enter your limit price
User: 2
Bot: What limit price?
User: 1.05
Bot: ✓ LIMIT SELL ORDER @ $1.05 (working)
```

### 2. Bracket Order Builder
```
User: bracket
Bot: Setting up bracket order...
     Current position: LONG 1000 @ $0.50

     1️⃣  Quick Setup (auto stop/target)
     2️⃣  Custom Setup (choose your levels)
User: 2
Bot: Enter stop loss price:
User: 0.45
Bot: Enter take profit price:
User: 0.70
Bot: 🎯 BRACKET ORDER SET
     Stop: $0.45 (-10%)
     Target: $0.70 (+40%)
```

### 3. Position Reconciliation
```
User: long 5000 @ 0.60
Bot: You already have LONG 2000 @ $0.55

     What should I do?
     1️⃣  Add 5000 more (total: 7000)
     2️⃣  Update to 5000 (close 2000, open 5000)
     3️⃣  Replace position (close old, open new)
User: 1
Bot: ✓ ADDED 5000 @ $0.60
     New Average: $0.58 (7000 shares)
```

### 4. Smart Exit Advisor
```
User: should I exit?
Bot: 🤖 EXIT ANALYSIS
     Position: LONG 3000 @ $0.50
     Current: $0.75 (+50%)

     My recommendation: Scale out gradually
     1️⃣  Take profit now (exit all)
     2️⃣  Scale out 50%, hold rest
     3️⃣  Hold and set trailing stop
User: 2
Bot: Starting gradual exit for 1500 shares...
     [Progress updates stream in]
```

---

## Testing

### Manual Test Flow

1. **Start services:**
```bash
npm start ai
```

2. **Open position:**
```
User: long 3750 @ .63
Bot: ✓ LONG 3750 @ $0.63
```

3. **Trigger interactive scaleout:**
```
User: scaleout
Bot: [Shows speed selection prompt]
```

4. **Choose speed:**
```
User: 1
Bot: [Starts fast scaleout]
Bot: [Progress messages appear every 10-30 seconds]
```

5. **Check P&L:**
```
User: pl
Bot: [Shows P&L summary]
```

### Test Edge Cases

1. **Cancel scaleout mid-execution:**
```
User: cancel scaleout
Bot: ✓ Scaleout cancelled
```

2. **Try scaleout when already running:**
```
User: scaleout
Bot: ⚠️ Scaleout already in progress for BYND
     Type 'cancel scaleout' to stop it
```

3. **Timeout conversation state:**
- Wait 6 minutes after scaleout prompt
- Type "1" - should NOT trigger scaleout
- Should fall through to normal command handling

---

## Files Created/Modified

### New Files:
1. `ai-service/event_bus.py` - Pub-sub event system
2. `ai-service/scaleout_worker.py` - Background scaleout worker
3. `ai-service/conversation_state.py` - Multi-turn conversation state
4. `INTERACTIVE_SCALEOUT_README.md` - This file

### Modified Files:
1. `ai-service/trade_command_executor.py`
   - Added `conversation_id` parameter
   - Updated `scale_out_position()` to be interactive
   - Added `execute_scaleout_with_speed()`
   - Added `get_pnl_summary()`

2. `ai-service/fast_classifier_v2.py`
   - Added `conversation_id` parameter
   - Check conversation state FIRST in classify()
   - Handle speed selection responses (1, 2, 3)

3. `ai-service/main.py`
   - Create classifiers per conversation (not just per symbol)
   - Pass `conversation_id` to classifier

### Database:
- Added `/trade pl` command
- Added 3 aliases: `pl`, `pnl`, `profit`

---

## Future Enhancements

1. **WebSocket Event Streaming** - Connect frontend to event bus for real-time updates
2. **Persistent Task Storage** - Store active tasks in Redis for crash recovery
3. **Scheduled Commands** - "sell 1000 @ 0.70 if price hits by 3pm"
4. **Multi-Symbol Scaleout** - Scale out of multiple positions simultaneously
5. **Smart Scaleout** - AI-powered dynamic chunk sizing based on volume/volatility
6. **Progress UI** - Visual progress bar in chat for long-running operations
7. **Task History** - View history of background tasks and their outcomes
8. **Notifications** - Notify user when background task completes (even if chat closed)

---

## Summary

✅ Interactive scaleout with speed selection (fast/medium/slow)
✅ Background worker executes chunked exits over time
✅ Real-time progress updates via pub-sub event bus
✅ Conversation state management for multi-turn flows
✅ New `/trade pl` command for P&L display
✅ Architecture ready for many more interactive commands

**Next Steps:**
1. Test end-to-end in chat interface
2. Connect frontend WebSocket to event bus
3. Add position command enhancements
4. Implement other interactive commands (close, bracket, etc.)
