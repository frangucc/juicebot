# Trade Command Center - Complete Reference

## Overview

The Trade Command Center provides comprehensive position management with visual chart indicators and real-time P&L tracking. All positions persist to Supabase and survive browser refreshes.

## Quick Reference

### Position Entry (Type WITHOUT `/`)
```
long <qty> @ <price>    → Enter/add to long position
short <qty> @ <price>   → Enter/add to short position
```

### Position Management
```
pos / position          → Check current position + P&L
close / exit            → Close position at market
flat                    → Flatten ALL positions
```

### Account Management (WITH `/`)
```
/trade reset            → Reset P&L counter (start fresh)
/trade history          → View all trades
/trade summary          → P&L statistics report
```

## Visual Chart Indicators

### Position Lines
When you enter a position, a horizontal line appears on the chart:

| Position Type | Line Color | Example Label |
|--------------|------------|---------------|
| LONG | Bright purple (`#b580ff`) | `long 500 up $75` |
| SHORT | Yellow (`#ffff00`) | `short 1000 up $100` |

### Line Behavior
- **Only ONE line at a time** (can't be long and short simultaneously)
- **Real-time P&L updates** as prices move
- **Solid lines** (not dashed)
- **Persistent** across browser refresh
- **Removed** when position closed or flattened

## Command Details

### `long <qty> @ <price>`
Opens or adds to long position.

**Reversal Logic:**
- If SHORT position exists → Close short (calc P&L) → Open long
- Chart: Yellow line removed → Purple line added

**Adding Logic:**
- If LONG position exists → Average entry price
- Chart: Purple line moves to new average entry

**Example:**
```
long 1000 @ 0.57

Response:
✓ LONG 1000 BYND @ $0.57
  Position Value: $570.00

Chart:
Purple line appears at $0.57
Label: "long 1000 up $0"
```

### `short <qty> @ <price>`
Opens or adds to short position.

**Reversal Logic:**
- If LONG position exists → Close long (calc P&L) → Open short
- Chart: Purple line removed → Yellow line added

**Adding Logic:**
- If SHORT position exists → Average entry price
- Chart: Yellow line moves to new average entry

**Example:**
```
short 1000 @ 0.71

Response:
✓ SHORT 1000 BYND @ $0.71
  Position Value: $710.00

Chart:
Yellow line appears at $0.71
Label: "short 1000 up $0"
```

### `pos` / `position`
Shows current position with live P&L.

**Response Format:**
```
SHORT 1000 BYND @ $0.71
Current: $0.61 | P&L: +$100.00 (+14.08%)
Master P&L: +$250.00
```

**Includes:**
- Side (LONG/SHORT)
- Quantity
- Entry price
- Current price
- Unrealized P&L (dollars and percent)
- Master P&L (cumulative total)

### `close` / `exit`
Closes current position at market price.

**Behavior:**
1. Closes position at current market price
2. Calculates final P&L
3. Updates Master P&L
4. Removes chart line
5. Updates database (status='closed')

**Response Format:**
```
✓ CLOSED SHORT 1000 BYND @ $0.61
  Entry: $0.71 | P&L: +$100.00
  Master P&L: +$250.00
```

### `flat`
Flattens ALL open positions immediately.

**Behavior:**
1. Closes all open positions at market
2. Calculates P&L for each
3. Updates Master P&L
4. Removes all chart lines
5. Shows summary

**Response Format:**
```
✓ FLATTENED
  BYND LONG 500 @ $0.63 (Entry: $0.57) | P&L: +$30.00
  Master P&L: +$280.00
```

**Use Cases:**
- Emergency exit
- End of day flatten
- Risk management

### `/trade reset`
Resets P&L tracking (starts fresh session).

**Behavior:**
- Does NOT delete historical trades
- Resets Master P&L counter to $0.00
- Maintains full trade history
- Creates new P&L session ID

**Use Case:**
After testing, reset to start real trading with clean P&L

### `/trade history`
Shows complete trade history.

**Response Format:**
```
TRADE HISTORY
═══════════════════════════════════════
1. BYND SHORT 1000 @ $0.71 → $0.61 | +$100.00
   Entry: 2025-01-25 10:30:00
   Exit: 2025-01-25 10:45:00

2. BYND LONG 500 @ $0.53 → $0.58 | +$25.00
   Entry: 2025-01-25 09:15:00
   Exit: 2025-01-25 09:30:00

3. BYND SHORT 1000 @ $0.65 → $0.70 | -$50.00
   Entry: 2025-01-25 08:00:00
   Exit: 2025-01-25 08:20:00
═══════════════════════════════════════
Total P&L: +$75.00 | Win Rate: 66.7%
```

### `/trade summary`
P&L statistics and performance metrics.

**Response Format:**
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

Profit Factor: 2.33
Expectancy: +$16.67 per trade
═══════════════════════════════════════
```

## Master P&L Tracking

### What is Master P&L?
Cumulative profit/loss across ALL trades:
- **Realized P&L**: Sum of all closed trades
- **Unrealized P&L**: Current open position P&L
- **Master P&L**: Realized + Unrealized = Total performance

### Persistence
- Stored in database
- Survives browser refresh
- Survives position closes
- Only resets with `/trade reset`

### Example Flow
```
Starting: Master P&L = $0.00

Trade 1: LONG 100 @ $0.50 → Close @ $0.55
  P&L: +$5.00
  Master P&L: $5.00 ✓

Trade 2: SHORT 500 @ $0.70 → Close @ $0.65
  P&L: +$25.00
  Master P&L: $30.00 ✓

Trade 3: LONG 1000 @ $0.57 (currently open @ $0.62)
  Unrealized P&L: +$50.00
  Master P&L: $80.00 (includes unrealized)

After closing Trade 3:
  Realized P&L: $80.00
  Master P&L: $80.00
```

## Reversal & Flatten Logic

### Reversal (Opposite Side)
When you reverse position (SHORT → LONG or LONG → SHORT):

**Process:**
1. Close existing position at current market price
2. Calculate P&L from close
3. Add to Master P&L
4. Open new position at your entry price
5. Update chart line (remove old color, add new color)
6. Show both transactions in chat

**Example:**
```
Current: SHORT 1000 @ $0.71
Current Price: $0.61
You type: long 500 @ 0.57

Result:
1. Close SHORT 1000 @ $0.61 → P&L = +$100.00
2. Master P&L: $0.00 + $100.00 = $100.00
3. Open LONG 500 @ $0.57
4. Chart: Yellow line removed, purple line at $0.57
```

### Adding to Position (Same Side)
When you add to existing position:

**Process:**
1. Calculate average entry price:
   `(old_qty × old_price + new_qty × new_price) / total_qty`
2. Update total quantity
3. Keep same line color
4. Move line to new average entry price
5. Update label

**Example:**
```
Current: LONG 100 @ $0.50
You type: long 50 @ 0.60

Result:
Avg = (100 × 0.50 + 50 × 0.60) / 150 = $0.5333
New position: LONG 150 @ $0.5333
Chart: Purple line moves to $0.5333
```

### Flatten All
`flat` command closes everything:

**Process:**
1. Query all open positions
2. Close each at current market price
3. Calculate P&L for each
4. Update Master P&L
5. Remove all chart lines
6. Show summary

## Real-Time P&L Updates

### Update Frequency
P&L label updates **continuously** as bars arrive:
- Historical replay: Every second (1min bars)
- Live market: Every bar received
- WebSocket driven

### Label Format

**Profitable (P&L positive):**
```
long 500 up $75
short 1000 up $100
```

**Losing (P&L negative):**
```
long 500 down $25
short 1000 down $50
```

### Calculation

**Long Position:**
```
P&L = (current_price - entry_price) × quantity
```

**Short Position:**
```
P&L = (entry_price - current_price) × quantity
```

## Database Schema

### `trades` Table
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
  pnl_session_id UUID,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trades_user_symbol_status
  ON trades(user_id, symbol, status);
CREATE INDEX idx_trades_session
  ON trades(pnl_session_id);
```

**Field Descriptions:**
- `status='open'`: Active position (has chart line)
- `status='closed'`: Historical trade (no chart line)
- `realized_pnl`: Cumulative P&L at close (includes previous trades)
- `pnl_session_id`: Links trades to session (for `/trade reset`)

## Integration with AI Service

### Hybrid F+AI Pattern
Position commands use hybrid approach:
1. **Fast Response** (< 100ms): Position recorded, instant confirmation
2. **AI Analysis** (~2s): Claude provides trade context

**Example Flow:**
```
You type: long 1000 @ 0.57

Fast Response (instant):
✓ LONG 1000 BYND @ $0.57
  Position Value: $570.00

AI Response (~2s later):
Position recorded. Current price action shows
consolidation near $0.57 support level. Entry
looks reasonable given the recent bounce...
```

## Testing

### Initial Test Position
For testing, create this position:
```
short 1000 @ 0.71
```

This will:
1. Create record in Supabase `trades` table
2. Display yellow line on chart at $0.71
3. Show label "short 1000 up/down $X" based on current price

### Cleanup After Testing
When done testing:
```
close    # Closes the position
# OR
flat     # Flattens everything
# THEN
/trade reset    # Resets P&L to start fresh
```

This keeps trade history but starts new P&L session.

## Future Enhancements

### Clerk Feature (Coming Soon)
Proactive position monitoring:
- Auto-updates every few seconds
- Alerts on material P&L changes
- Posts to chat automatically
- Enable with: `clerk on`

### Multi-Symbol Support
Currently supports one symbol at a time. Future:
- Track positions across multiple symbols
- Multiple chart lines (different colors per symbol)
- Aggregate P&L view

### Risk Management
Planned features:
- Stop loss alerts
- Take profit targets
- Position size calculator
- Risk/reward ratios

## Troubleshooting

### Position Not Saving
**Problem**: Commands recognized but not in database
**Check**:
1. Supabase connection in `position_storage.py`
2. AI service running on port 8002
3. Check browser console for errors

### Chart Line Not Appearing
**Problem**: Position saved but no line
**Check**:
1. Chart component mounted properly
2. Position line code in StockChartHistorical.tsx
3. Browser console for rendering errors

### P&L Not Updating
**Problem**: Line shows but P&L stuck at $0
**Check**:
1. WebSocket connected and streaming bars
2. Current price updating in market data
3. P&L calculation in position line logic

## Summary

The Trade Command Center provides:
- ✅ Visual position tracking with chart lines
- ✅ Real-time P&L updates
- ✅ Reversal and position averaging logic
- ✅ Master P&L tracking across all trades
- ✅ Complete trade history
- ✅ Performance statistics
- ✅ Database persistence
- ✅ Hybrid F+AI responses

All positions persist to Supabase and survive browser refreshes. Type commands directly (no `/`) to trade, use `/trade` to see command reference.
