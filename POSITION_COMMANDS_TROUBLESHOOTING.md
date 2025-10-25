# Position Commands Troubleshooting

## Issue: "Failed to fetch" when typing `long 1000 @ 0.57`

### Root Cause
The AI service on port 8002 is not running or not reachable.

### Solution

1. **Restart AI Service** (to pick up new position_storage.py):
```bash
npm stop
npm start
```

2. **Verify AI Service is Running:**
Check that you see:
```
[AI Service] 🚀 Starting on port 8002...
[AI Service] 🚀 Starting WebSocket client for bar data...
```

3. **Test Position Command:**
In chart-agent chat, type:
```
long 1000 @ 0.57
```

Expected response:
```
✓ LONG 1000 BYND @ $0.57
  Position Value: $570.00
```

Then Claude analysis follows.

## How Position Commands Work

### Command Flow
```
User types: long 1000 @ 0.57
     ↓
Chat sends to: http://localhost:8002/chat
     ↓
AI Service → fast_classifier.py
     ↓
Pattern matches: LONG_PATTERN
     ↓
Calls: position_storage.record_position()
     ↓
Saves to: Supabase trades table
     ↓
Returns fast response immediately
     ↓
Then continues to Claude for AI analysis
     ↓
Both responses show in chat
```

### What Gets Stored in Database

When you type `long 1000 @ 0.57`:

**Supabase `trades` table record:**
```json
{
  "user_id": "default_user",
  "symbol": "BYND",
  "side": "long",
  "quantity": 1000,
  "entry_price": 0.57,
  "entry_value": 570.00,
  "entry_time": "2025-01-25T10:30:00Z",
  "status": "open",
  "realized_pnl": 0.00
}
```

## `/trade` Command Center - Complete Strategy

**`/trade` is your COMMAND CENTER** - Shows available position management commands.

### What `/trade` Does:
Displays all position management commands you can type (without slash):
```
/trade

Returns:
═══════════════════════════════════════════
         TRADE COMMAND CENTER
═══════════════════════════════════════════

POSITION ENTRY:
  long <qty> @ <price>    → enter long position 🟢 F+AI
  short <qty> @ <price>   → enter short position 🟢 F+AI

POSITION MANAGEMENT:
  pos / position          → check current position 🟢 F+AI
  close / exit            → close position at market 🟢 F+AI
  flat                    → flatten all positions 🟢 F+AI

ACCOUNT MANAGEMENT:
  /trade reset            → reset P&L (start fresh) 🔴 LLM
  /trade history          → view trade history 🔴 LLM
  /trade summary          → P&L summary report 🔴 LLM

VISUAL INDICATORS:
  - Long positions: Bright purple line on chart
  - Short positions: Yellow line on chart
  - Real-time P&L updates in line label
  - Only ONE position line at a time

═══════════════════════════════════════════
Type commands WITHOUT the / slash
Example: long 1000 @ 0.57
═══════════════════════════════════════════
```

### How to Actually Trade:
**Type commands DIRECTLY without the `/` slash:**

✅ Correct:
```
long 1000 @ 0.57
short 500 @ 12.45
pos
close
flat
```

❌ Wrong:
```
/long 1000 @ 0.57
/short 500 @ 12.45
/pos
/flat
```

### Position Entry Commands

#### `long <qty> @ <price>`
Opens or adds to long position.
- **Behavior**: If you have an existing SHORT, it will CLOSE the short (calculate P&L), then open the long
- **If already LONG**: Adds to position with averaged entry price
- **Database**: Creates new record in `trades` table with status='open'
- **Chart**: Displays bright purple horizontal line at entry price with real-time P&L label
- **Example**: `long 1000 @ 0.57` → Purple line at $0.57, label shows "long 1000 up $50"

#### `short <qty> @ <price>`
Opens or adds to short position.
- **Behavior**: If you have an existing LONG, it will CLOSE the long (calculate P&L), then open the short
- **If already SHORT**: Adds to position with averaged entry price
- **Database**: Creates new record in `trades` table with status='open'
- **Chart**: Displays yellow horizontal line at entry price with real-time P&L label
- **Example**: `short 1000 @ 0.71` → Yellow line at $0.71, label shows "short 1000 up $100"

### Position Management Commands

#### `pos` or `position`
Shows current position with live P&L.
- **Fast Response**: Instant position summary with unrealized P&L
- **AI Analysis**: Claude provides context on the position
- **Database**: Queries `trades` table for open position
- **Example Output**:
  ```
  SHORT 1000 BYND @ $0.71
  Current: $0.61 | P&L: +$100.00 (+14.08%)
  Master P&L: +$250.00
  ```

#### `close` or `exit`
Closes current position at market price.
- **Behavior**:
  - Closes position at current market price
  - Calculates final P&L
  - Updates Master P&L (cumulative)
  - Removes position line from chart
- **Database**: Updates record status='closed', sets exit_price and exit_time
- **Example Output**:
  ```
  ✓ CLOSED SHORT 1000 BYND @ $0.61
    Entry: $0.71 | P&L: +$100.00
    Master P&L: +$250.00
  ```

#### `flat`
Flattens ALL positions immediately.
- **Behavior**:
  - Closes all open positions at current market price
  - Records P&L for each position
  - Updates Master P&L
  - Removes all position lines from chart
- **Database**: Updates all open positions to status='closed'
- **Use Case**: Emergency exit, end of day flatten
- **Example**: `flat` → Closes everything, shows total P&L

### Account Management Commands

#### `/trade reset`
Resets P&L tracking (starts fresh).
- **Behavior**:
  - Does NOT delete historical trades
  - Resets Master P&L counter to $0.00
  - Maintains full trade history in database
  - Use when starting new trading session/strategy
- **Database**: Adds flag or timestamp to mark new P&L session
- **Example**: After testing, reset to start real trading with clean P&L

#### `/trade history`
Shows your trade history.
- **Behavior**:
  - Queries all trades (open and closed)
  - Shows entry/exit prices, P&L per trade
  - Sortable by date, P&L, symbol
- **Database**: Selects from `trades` table with filters
- **Example Output**:
  ```
  TRADE HISTORY
  ═══════════════════════════════════════
  1. BYND SHORT 1000 @ $0.71 → $0.61 | +$100.00
  2. BYND LONG 500 @ $0.53 → $0.58 | +$25.00
  3. BYND SHORT 1000 @ $0.65 → $0.70 | -$50.00
  ═══════════════════════════════════════
  Total P&L: +$75.00 | Win Rate: 66.7%
  ```

#### `/trade summary`
P&L summary and statistics.
- **Behavior**:
  - Total P&L (realized + unrealized)
  - Win rate percentage
  - Average win/loss
  - Largest win/loss
  - Number of trades
- **Database**: Aggregates data from `trades` table
- **Example Output**:
  ```
  P&L SUMMARY
  ═══════════════════════════════════════
  Total P&L: +$250.00
  Realized P&L: +$150.00
  Unrealized P&L: +$100.00 (current position)

  Trades: 12
  Winners: 8 (66.7%)
  Losers: 4 (33.3%)

  Avg Win: +$35.00
  Avg Loss: -$15.00
  Largest Win: +$100.00
  Largest Loss: -$25.00
  ═══════════════════════════════════════
  ```

### Visual Chart Indicators - Position Lines

When you enter a position, a horizontal line appears on the TradingView chart showing your entry price with a real-time P&L label.

#### Line Colors:
- **Long Position**: Bright purple (`#b580ff`) solid line
- **Short Position**: Yellow (`#ffff00`) solid line

#### Label Format:
The line label shows position details and updates continuously as price moves:

**Short Position (profitable, price dropped):**
```
short 1000 up $100
```

**Short Position (losing, price rose):**
```
short 1000 down $50
```

**Long Position (profitable, price rose):**
```
long 500 up $75
```

**Long Position (losing, price dropped):**
```
long 500 down $25
```

#### Rules:
1. **Only ONE line at a time** - Can't be both long and short simultaneously
2. **Real-time updates** - P&L updates continuously as each bar arrives
3. **Reversal behavior** - When you reverse (SHORT → LONG or vice versa):
   - Old line is removed
   - New line appears at new entry price
   - Both transactions shown in chat
4. **Persistence** - Position line survives browser refresh (loads from Supabase)
5. **Removal** - Line disappears when you `close` or `flat` your position

#### Example Scenarios:

**Scenario 1: Open Short**
```
You type: short 1000 @ 0.71
Chart shows: Yellow line at $0.71, label "short 1000 up $0"
Price drops to $0.61
Chart updates: Yellow line at $0.71, label "short 1000 up $100"
```

**Scenario 2: Reversal (Short → Long)**
```
Current: Yellow line at $0.71 (short 1000)
You type: long 500 @ 0.57
Chat shows:
  ✓ CLOSED SHORT 1000 BYND @ $0.57
    Entry: $0.71 | P&L: +$140.00

  ✓ LONG 500 BYND @ $0.57
    Position Value: $285.00
    Master P&L: +$140.00

Chart updates:
  - Yellow line removed
  - Purple line appears at $0.57, label "long 500 up $0"
```

**Scenario 3: Flatten Everything**
```
Current: Purple line at $0.57 (long 500)
Current price: $0.63
You type: flat
Chat shows:
  ✓ CLOSED LONG 500 BYND @ $0.63
    Entry: $0.57 | P&L: +$30.00
    Master P&L: +$170.00

Chart updates: Purple line removed
```

### Reversal & Flatten Logic

#### Reversal (Opposite Side Entry)
When you enter a position opposite to your current position, the system automatically:
1. **Closes existing position** at current market price
2. **Calculates P&L** from the closed position
3. **Updates Master P&L** (adds to cumulative total)
4. **Opens new position** at your specified price
5. **Updates chart line** (removes old color, adds new color)
6. **Shows both transactions** in chat (close + open)

**Example Flow:**
```
Current Position: SHORT 1000 @ $0.71
Current Price: $0.61
Master P&L: $0.00

You type: long 500 @ 0.57

Result:
1. Close SHORT 1000 @ $0.61 → P&L = +$100.00
2. Update Master P&L: $0.00 + $100.00 = $100.00
3. Open LONG 500 @ $0.57
4. Chart: Remove yellow line, add purple line at $0.57
5. New Master P&L: $100.00
```

#### Adding to Position (Same Side)
When you enter more on the same side, the system:
1. **Calculates average entry price** = (old_qty × old_price + new_qty × new_price) / total_qty
2. **Updates quantity** to total shares
3. **Keeps same line color** (doesn't change)
4. **Updates line position** to new average entry price
5. **Shows addition message** in chat

**Example Flow:**
```
Current Position: LONG 100 @ $0.50
You type: long 50 @ 0.60

Result:
1. Calculate avg: (100 × 0.50 + 50 × 0.60) / 150 = $0.5333
2. Update position: LONG 150 @ $0.5333
3. Chart: Move purple line to $0.5333
4. Label: "long 150 up/down $X"
```

#### Flatten All
The `flat` command closes ALL open positions immediately:
1. **Queries all open positions** from database
2. **Closes each at current market price**
3. **Calculates P&L for each**
4. **Updates Master P&L** with all realized gains/losses
5. **Removes all chart lines**
6. **Shows summary** of all closed positions

**Example Flow:**
```
Current Positions:
- BYND LONG 500 @ $0.57
- (In future: multiple symbols supported)

Current Price: $0.63
You type: flat

Result:
1. Close LONG 500 BYND @ $0.63 → P&L = +$30.00
2. Update Master P&L: $170.00 + $30.00 = $200.00
3. Remove all chart lines
4. Chat: "✓ FLATTENED | Total P&L: +$30.00 | Master P&L: $200.00"
```

### Master P&L Tracking

The **Master P&L** is your cumulative profit/loss across ALL trades (open and closed):
- **Realized P&L**: Sum of all closed trades
- **Unrealized P&L**: Current open position P&L
- **Master P&L**: Realized + Unrealized = Total performance

**Persistence:**
- Master P&L is stored in database
- Survives browser refresh
- Survives position closes
- Only resets with `/trade reset` command

**Example Flow:**
```
Starting Master P&L: $0.00

Trade 1: LONG 100 @ $0.50 → Close @ $0.55
  P&L: +$5.00
  Master P&L: $5.00

Trade 2: SHORT 500 @ $0.70 → Close @ $0.65
  P&L: +$25.00
  Master P&L: $30.00

Trade 3: LONG 1000 @ $0.57 → Currently open @ $0.62
  Unrealized P&L: +$50.00
  Realized P&L: $30.00
  Master P&L: $80.00 (shown in pos command)

After closing Trade 3:
  Realized P&L: $80.00
  Master P&L: $80.00
```

### Database Schema - `trades` Table

All trades are stored with full history:

```sql
CREATE TABLE trades (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('long', 'short')),
  quantity INTEGER NOT NULL,
  entry_price DECIMAL(10, 2) NOT NULL,
  entry_value DECIMAL(12, 2) NOT NULL,
  entry_time TIMESTAMP NOT NULL DEFAULT NOW(),
  exit_price DECIMAL(10, 2),
  exit_time TIMESTAMP,
  status TEXT NOT NULL CHECK (status IN ('open', 'closed')),
  realized_pnl DECIMAL(12, 2) DEFAULT 0.00,
  pnl_session_id UUID,  -- For /trade reset functionality
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast queries
CREATE INDEX idx_trades_user_symbol_status ON trades(user_id, symbol, status);
CREATE INDEX idx_trades_session ON trades(pnl_session_id);
```

**Key Fields:**
- `status='open'`: Active position (has chart line)
- `status='closed'`: Historical trade (no chart line)
- `realized_pnl`: Cumulative P&L at time of close (includes previous trades)
- `pnl_session_id`: Links trades to P&L session (for reset tracking)

## Clerk Feature (Coming Soon)

The clerk feature will:
1. Monitor your open position continuously
2. Send proactive updates to chat every few seconds or on material P&L changes (e.g., $10 move)
3. Post messages like:
   ```
   📊 Position Update
   LONG 1000 BYND @ $0.57
   Current: $0.62 | P&L: +$50.00 (+8.77%)
   ```
4. Alert on key levels (entry price crossings, breakeven, etc.)

### To Enable Clerk:
Will be a command like:
```
clerk on
clerk off
```

This isn't implemented yet but the position storage and chart lines are ready for it!

## Testing Position Commands

### 1. Test Basic Long
```
long 100 @ 0.50
```

Expected:
```
✓ LONG 100 BYND @ $0.50
  Position Value: $50.00
```

### 2. Test Position Check
```
pos
```

Expected:
```
LONG 100 BYND @ $0.50
Current: $0.52 | P&L: +$2.00 (+4.00%)
```

### 3. Test Adding to Position
```
long 50 @ 0.55
```

Expected:
```
✓ ADDED TO LONG BYND
  +50 @ $0.55
  Total Position: 150 @ $0.52 avg
```

### 4. Test Reversal (Short → Long)
```
# First be short
short 100 @ 0.60

# Then go long
long 50 @ 0.57
```

Expected:
```
✓ CLOSED SHORT 100 BYND @ $0.57
  Entry: $0.60 | P&L: +$3.00

✓ LONG 50 BYND @ $0.57
  Position Value: $28.50
  Master P&L: +$3.00
```

### 5. Test Close
```
close
```

Expected:
```
✓ CLOSED LONG 50 BYND @ $0.58
  Entry: $0.57 | P&L: +$0.50
  Master P&L: +$3.50
```

## Verify in Supabase

After running commands, check your Supabase dashboard:

1. Go to Supabase project
2. Navigate to `trades` table
3. You should see records like:

| id | symbol | side | quantity | entry_price | status |
|----|--------|------|----------|-------------|--------|
| 1 | BYND | long | 1000 | 0.57 | open |

## Common Issues

### Issue: "No open position" when you just opened one
**Problem**: Position might not have been saved
**Fix**: Check Supabase connection, restart AI service

### Issue: P&L shows $0.00
**Problem**: No live market data coming in
**Fix**: Ensure WebSocket is connected and streaming bars

### Issue: Commands not recognized
**Problem**: AI service not running
**Fix**: `npm start` and check port 8002

### Issue: Claude response but no fast response
**Problem**: Fast classifier not matching pattern
**Fix**: Check command syntax exactly: `long 100 @ 0.50` (with spaces)

## Quick Diagnostic

Run this in your terminal to check if AI service is up:
```bash
curl http://localhost:8002/health
```

Should return:
```json
{"status": "healthy"}
```

If not, restart with:
```bash
npm stop
npm start
```

## Pattern Matching

The fast classifier uses these patterns:

```python
LONG_PATTERN = r'\b(long|buy)\s+(\d+)\s*@\s*[\$]?(\d+\.?\d*)'
SHORT_PATTERN = r'\b(short|sell)\s+(\d+)\s*@\s*[\$]?(\d+\.?\d*)'
```

Valid formats:
- `long 100 @ 0.50` ✅
- `long 100 @ .50` ✅
- `long 100 @ $0.50` ✅
- `buy 100 @ 0.50` ✅

Invalid formats:
- `long100@0.50` ❌ (no spaces)
- `long 100 0.50` ❌ (missing @)
- `go long 100 @ 0.50` ❌ (extra words before)

## Summary

| What You Type | What Happens | Database |
|---------------|--------------|----------|
| `long 1000 @ 0.57` | Fast + AI response | ✅ Stored |
| `pos` | Shows position + P&L | ✅ Reads from DB |
| `close` | Closes position | ✅ Updates DB |
| `/trade` | Shows command help | ❌ No DB action |
| `/strategy` | Shows strategies | ❌ No DB action |

**Remember**: Trade commands are typed WITHOUT the `/` slash!
