# Trade Commands Reference

## Overview

JuiceBot provides instant position tracking commands that execute in <50ms without LLM calls. All positions are persisted to Supabase with automatic reversal logic and P&L tracking.

---

## Position Entry Commands

### Long Position
```
long [quantity] @ [price]
buy [quantity] @ [price]
```

**Examples:**
```
long 100 @ .57
buy 500 @ 12.45
long 1000 @ 0.71
```

**Behavior:**
- If no position: Opens new LONG position
- If SHORT position exists: Closes SHORT, books P&L, opens new LONG
- If LONG position exists: Adds to position with averaged entry price

**Response Format:**
```
✓ LONG 100 BYND @ $0.57
  Position Value: $57.00
```

**Reversal Example:**
```
✓ CLOSED SHORT 500 BYND @ $0.57
  Entry: $0.68 | P&L: +$55.00

✓ LONG 100 BYND @ $0.57
  Position Value: $57.00
  Master P&L: +$55.00
```

---

### Short Position
```
short [quantity] @ [price]
sell [quantity] @ [price]
```

**Examples:**
```
short 100 @ .68
sell 500 @ 12.45
short 1000 @ 0.71
```

**Behavior:**
- If no position: Opens new SHORT position
- If LONG position exists: Closes LONG, books P&L, opens new SHORT
- If SHORT position exists: Adds to position with averaged entry price

**Response Format:**
```
✓ SHORT 1000 BYND @ $0.71
  Position Value: $710.00
```

---

## Position Query Commands

### Check Position
```
pos
position
positions
```

**Response Format:**
```
LONG 100 BYND @ $0.57
Current: $0.63 | P&L: +$6.00 (+10.53%)
```

**With Master P&L:**
```
SHORT 1000 BYND @ $0.71
Current: $0.63 | P&L: +$80.00 (+11.27%)
Master P&L: +$140.10
```

**No Position:**
```
No open position for BYND
```

---

### Close Position
```
close
close position
close all
exit
exit position
sell all
```

**Response Format:**
```
✓ CLOSED LONG 100 BYND @ $0.63
  Entry: $0.57 | P&L: +$6.00
  Master P&L: +$6.00
```

**No Position:**
```
⚠️ No open position for BYND
```

---

## Market Data Commands

### Current Price
```
last
price
current
now
```

**Response:** `$0.57`

---

### Volume
```
volume
vol
```

**Response:** `Vol: 1,234,567`

---

### Range
```
high
low
range
```

**Response:** `High: $0.70 | Low: $0.55`

---

## Command Types

| Type | Speed | Description |
|------|-------|-------------|
| **F** | <50ms | Fast-path only (no LLM) |
| **F+AI** | <50ms + ~2s | Fast response + AI analysis after |

### Fast Commands (F)
- `last`, `price` - Current price
- `volume`, `vol` - Current volume  
- `high`, `low` - Today's range

### Hybrid Commands (F+AI)
- `long [qty] @ [price]` - Record long position + AI analysis
- `short [qty] @ [price]` - Record short position + AI analysis
- `pos`, `position` - Position status + AI trade analysis
- `close`, `exit` - Close position + AI exit analysis

---

## Position Tracking Features

### Automatic Reversal
When you switch from LONG → SHORT or SHORT → LONG:
1. Automatically closes existing position
2. Calculates and books P&L
3. Opens new opposite position
4. Shows both transactions
5. Carries forward Master P&L

**Example:**
```
User has: SHORT 500 @ $0.68
User types: long 100 @ .57

Result:
✓ CLOSED SHORT 500 BYND @ $0.57
  Entry: $0.68 | P&L: +$55.00

✓ LONG 100 BYND @ $0.57
  Position Value: $57.00
  Master P&L: +$55.00
```

### Position Averaging
When you add to an existing position:
```
Existing: LONG 100 @ $0.50
User: long 50 @ $0.60

Result:
✓ ADDED TO LONG BYND
  +50 @ $0.60
  Total Position: 150 @ $0.53 avg
```

### Master P&L Tracking
- **Realized P&L**: Sum of all closed trades
- **Unrealized P&L**: Current open position P&L
- **Master P&L**: Realized + Unrealized (total performance)

---

## Chart Visualization

### Position Line
Horizontal line shows at entry price with real-time P&L:

**SHORT Position:**
- **Color:** Yellow (#EAB308)
- **Style:** Solid line
- **Label:** `short 1000 up +$159.40`

**LONG Position:**
- **Color:** Purple (#A855F7)
- **Style:** Solid line
- **Label:** `long 2000 down -$79.80`

**Features:**
- Updates P&L every 1 second
- Persists across browser refresh
- Only one position line at a time (can't be both long and short)

---

## Planned Commands

### /trade FLAT
```
/trade flat
```
Close position at current market price (market order simulation).

### /trade RESET
```
/trade reset
```
Clear session P&L and start fresh. Keeps trade history in database but resets realized_pnl counter.

### /trade REVERSE
```
/trade reverse
```
Instantly reverse position (close current and open opposite at market price).

---

## Database Schema

Positions stored in `trades` table:

| Field | Type | Description |
|-------|------|-------------|
| `id` | uuid | Primary key |
| `user_id` | uuid | User identifier (nullable) |
| `symbol` | text | Stock symbol |
| `side` | text | 'long' or 'short' |
| `quantity` | int | Number of shares |
| `entry_price` | decimal | Entry price |
| `entry_value` | decimal | Quantity × Entry Price |
| `entry_time` | timestamp | When position opened |
| `exit_price` | decimal | Exit price (null if open) |
| `exit_time` | timestamp | When position closed |
| `status` | text | 'open' or 'closed' |
| `realized_pnl` | decimal | Cumulative P&L (includes previous trades) |
| `created_at` | timestamp | Record creation time |
| `updated_at` | timestamp | Last update time |

---

## Example Session

```
User: long 100 @ .57
Bot: ✓ LONG 100 BYND @ $0.57
     Position Value: $57.00

[Price moves to $0.63]

User: pos
Bot: LONG 100 BYND @ $0.57
     Current: $0.63 | P&L: +$6.00 (+10.53%)

User: short 50 @ .65
Bot: ✓ CLOSED LONG 100 BYND @ $0.65
     Entry: $0.57 | P&L: +$8.00

     ✓ SHORT 50 BYND @ $0.65
     Position Value: $32.50
     Master P&L: +$8.00

User: close
Bot: ✓ CLOSED SHORT 50 BYND @ $0.63
     Entry: $0.65 | P&L: +$1.00
     Master P&L: +$9.00
```

---

## API Endpoints

### Get Position
```bash
GET http://localhost:8002/position/{symbol}
```

**Response:**
```json
{
  "position": {
    "id": "uuid",
    "symbol": "BYND",
    "side": "short",
    "quantity": 1000,
    "entry_price": 0.71,
    "current_price": 0.63,
    "unrealized_pnl": 80.0,
    "unrealized_pnl_pct": 11.27,
    "realized_pnl": 0.0,
    "total_pnl": 80.0,
    "entry_time": "2025-10-25T18:50:42.277503+00:00",
    "status": "open"
  }
}
```

---

## Notes

- All commands are **case-insensitive**
- Price can be written as `.57` or `0.57` or `$0.57`
- Commands persist to Supabase immediately
- P&L updates in real-time based on live price feed
- Position line updates every 1 second
- Supports multiple concurrent positions across different symbols
- Current implementation: single user (user_id nullable)

