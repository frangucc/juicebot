# JuiceBot /test Command - Test Coverage

## Overview

Comprehensive test suite for all JuiceBot trade commands with **real database operations**. All tests insert actual positions into Supabase and validate P&L tracking.

---

## Quick Start

### From JuiceBot Chat Window:
```
/test trade             → Run core tests (default, confirms "fast")
/test trade fast        → Run core tests explicitly
/test trade all         → Run core + advanced tests (brackets, stops)
/test trade ai          → Run AI/LLM tests
```

### From Command Line:
```bash
source venv/bin/activate
python3 test_trade_commands.py core            # Core tests
python3 test_trade_commands.py all             # Core + Advanced
python3 test_trade_commands.py ai              # AI tests
python3 test_trade_commands.py core --fast     # Skip slow tests
```

---

## Test Suites

### 1. Core Tests (`/test trade fast` or `/test trade`)
**14 tests** - Fast-path commands that execute in <50ms

| Test | Command | Validates |
|------|---------|-----------|
| Market Buy | `buy 100` | Long 100 shares |
| Position Check | `pos` | Position exists |
| P&L Summary (pl) | `pl` | Shows P&L summary |
| P&L Summary (pnl) | `pnl` | Shows P&L summary |
| P&L Summary (profit) | `profit` | Shows P&L summary |
| Accumulate | `add 50` | Long 150 shares |
| Scale Out 50% | `sell half` | Long 75 shares |
| Flatten | `flat` | No position |
| Limit Buy | `long 200 @ 0.55` | Long 200 @ $0.55 |
| Reverse | `reverse` | Short position |
| Get Price | `price` | Returns current price |
| Get Volume | `volume` | Returns volume |
| Final Flatten | `flat` | Clean state |

**Database Operations:**
- ✅ Inserts positions into `trades` table
- ✅ Updates position on accumulate/scale
- ✅ Validates `quantity`, `side`, `entry_price`
- ✅ Checks P&L calculations

---

### 2. Advanced Tests (`/test trade all` only)
**15 tests** - Bracket orders, stop losses, interactive scaleout, complex scenarios

| Test | Command | Validates |
|------|---------|-----------|
| Bracket Long | `bracket long 100 @ 0.55 stop 0.50 target 0.70` | Position + Stop + Target |
| Bracket Short | `bracket short 200 @ 0.60 stop 0.65 target 0.50` | Short position with safety |
| Stop Loss Setup | `long 100 @ 0.55` → `stop 0.50` | Stop added to position |
| Bracket Market | `bracket long 150` | Auto-calculates stop/target |
| Interactive Scaleout - Prompt | `long 1000` → `scaleout` | Shows speed selection menu |
| Interactive Scaleout - FAST | Select option `1` | Scales out over 1-3 min |
| Interactive Scaleout - MEDIUM | Select option `2` | Scales out over 10-15 min |
| Interactive Scaleout - SLOW | Select option `3` | Scales out over 60 min |

**Handler Coverage:**
- ✅ `create_bracket_order()` - Auto-calculates -2% stop, +6% target (3:1 R/R)
- ✅ `set_stop_loss()` - Sets stop at -2% for longs, +2% for shorts
- ✅ `scale_out_position()` - Interactive multi-turn command with speed selection
- ✅ `execute_scaleout_with_speed()` - Background worker with pub-sub progress events
- ❌ `set_trailing_stop()` - **NOT IMPLEMENTED YET**

---

### 3. AI Tests (`/test trade ai`)
**1 test** - Natural language commands requiring LLM

| Test | Command | Validates |
|------|---------|-----------|
| Natural Language Entry | `I want to go long 100 shares at fifty five cents` | LLM parses and executes |

**LLM Integration:**
- ✅ Uses `SMCAgent` for complex parsing
- ✅ Falls back to fast-path when possible
- ✅ Full context with bar history

---

## How Tests Work

### 1. Execution Flow
```
User types: /test trade all
    ↓
ChatInterface.tsx → Sends to AI service
    ↓
ai-service/main.py → handle_slash_command()
    ↓
Spawns subprocess: python3 test_trade_commands.py all
    ↓
Test suite executes commands via API
    ↓
Commands insert positions into Supabase
    ↓
Test suite validates database state
    ↓
Returns formatted results to chat
```

### 2. Test Architecture
```python
class TradeTestSuite:
    async def execute_command(self, command: str):
        """Send command to AI service API"""
        response = await session.post("http://localhost:8002/chat", json={
            "message": command,
            "symbol": self.symbol
        })
        return response

    def assert_position(self, side: str, qty: int):
        """Query Supabase and validate position"""
        pos = supabase.table('trades')\
            .select('*')\
            .eq('symbol', self.symbol)\
            .eq('status', 'open')\
            .execute()

        assert pos['side'] == side
        assert pos['quantity'] == qty
```

### 3. Auto-Cleanup
After all tests complete:
1. ✅ Flattens any open positions
2. ✅ Deletes test data from `trades` table
3. ✅ Resets P&L for test user
4. ✅ Verifies clean state

---

## Test Results Format

```
============================================================
  JUICEBOT TRADE COMMANDS TEST SUITE
============================================================
  Suite: all
  Symbol: BYND
  Fast Mode: False
============================================================

🚀 === CORE TESTS: Fast-Path Commands ===

🧹 Clearing all test positions...
✓ All positions cleared

▶️ Test 1: Market Buy - Long 100
📝 Command: 'buy 100'
✅ PASSED: Market Buy - Long 100

▶️ Test 2: Position Check
📝 Command: 'pos'
✅ PASSED: Position Check

...

🛡️ === ADVANCED TESTS: Bracket & Stop Orders ===

▶️ Test 11: Bracket Order - Long with Stop & Target
📝 Command: 'bracket long 100 @ 0.55 stop 0.50 target 0.70'
✅ PASSED: Bracket Order - Long with Stop & Target

...

🤖 === AI TESTS: Natural Language Commands ===

▶️ Test 18: Natural Language - Entry
📝 Command: 'I want to go long 100 shares at fifty five cents'
✅ PASSED: Natural Language - Entry

============================================================
📊 TEST SUMMARY
============================================================
📝 Total Tests: 18
✅ Passed: 18
❌ Failed: 0
🎉 ALL TESTS PASSED!
============================================================
```

---

## Requirements

- ✅ AI service running on port 8002
- ✅ Supabase connection configured
- ✅ venv activated with dependencies:
  - `aiohttp`
  - `supabase-py`
  - `python-dotenv`

---

## Files

| File | Purpose |
|------|---------|
| `test_trade_commands.py` | Main test suite (Python) |
| `ai-service/main.py` | Slash command handler |
| `dashboard/components/ChatInterface.tsx` | Frontend autocomplete |
| `.claude/commands/test-trade.sh` | Wrapper script |
| `TEST_SUITE_README.txt` | Quick reference |
| `TEST_COVERAGE.md` | This file (comprehensive docs) |

---

## Known Issues

### ❌ Trailing Stops Not Implemented
- No handler exists for `set_trailing_stop()`
- `/test trade all` skips trailing stop tests
- Needs implementation in `trade_command_executor.py`

### ⚠️ Close Command Enhancement Needed
User requested: "close should ask me, close at market, or at a price... let me type market or yes or a price"

**Current behavior:** `close` or `flat` immediately closes at market

**Desired behavior:**
```
> close
JuiceBot: Close at market or limit price? Type 'market' or enter price
> 0.60
JuiceBot: ✓ LIMIT SELL @ $0.60 (working order)
```

### ⚠️ Position Reconciliation
When user says "long 5000" but already holding 2000:
- Should ask: "Add 5000 or update to 5000?"
- Currently: Adds 5000 (accumulates)

---

## Integration with Claude Code

The `/test` command is integrated with Claude Code but executes in JuiceBot's chat window:

1. User types `/test` in JuiceBot chat
2. React autocomplete shows subcommands
3. Backend spawns Python test runner
4. Results stream back to chat in real-time

**NOT** a Claude Code slash command (no `.claude/commands/test.md`)

---

## Command Coverage Summary

| Category | Total Commands | Fast-Path | LLM-Assisted | Tested |
|----------|----------------|-----------|--------------|--------|
| Entry | 4 | 4 | 0 | ✅ |
| Exit | 3 | 3 | 0 | ✅ |
| Position Mgmt | 4 | 4 | 0 | ✅ |
| Advanced Orders | 3 | 2 | 1 | ⚠️ (missing trailing) |
| Market Data | 5 | 5 | 0 | ✅ |
| **TOTAL** | **19** | **18** | **1** | **95%** |

---

## Next Steps

1. **Implement trailing stops** in `trade_command_executor.py`
2. **Add interactive close** flow (market vs limit)
3. **Position reconciliation** logic (add vs update)
4. **Test indicators** suite (`/test indicators`)
5. **Test strategy** suite (`/test strategy`)
