# JuiceBot /test Command - Test Suite

## Overview

Comprehensive test suite for all JuiceBot trade commands with real database operations.

## Usage

### Run Core Tests (Fast Commands)
```
/test trade core
```

Tests:
- Market orders: buy 100, short 200
- Limit orders: long 200 @ 0.55
- Position tracking: pos, position
- P&L display: pl, pnl, profit
- Accumulate: add 50
- Scale out: sell half, sell 25%
- Flatten: flat, close
- Reversals: reverse, flip
- Market data: price, volume, range

### Run Core Tests (Fast Mode - Skip Slow Tests)
```
/test trade core --fast
```

Skips:
- Bracket orders
- Trailing stops
- Smart commands

### Run AI Tests
```
/test trade ai
```

Tests:
- Smart flatten (gradual exits)
- Smart reverse (safe reversals)
- Bracket orders with stops/targets
- Trailing stops
- Natural language commands

### Run Advanced Tests (Includes Core)
```
/test trade all
```

Tests:
- All core commands (see above)
- Bracket orders with stop & target
- Stop loss commands
- Complex order scenarios

### Run All Tests (Core + Advanced + AI)
```
/test trade all
```

Runs core, advanced, and AI tests together.

## What It Does

### 1. Test Execution
- Sends commands to AI service (http://localhost:8002/chat)
- Uses real market data for BYND
- Inserts positions into Supabase database
- Validates database state after each command

### 2. Position Assertions
- Checks if position exists/doesn't exist
- Verifies side (long/short)
- Verifies quantity (exact or minimum)
- Validates entry price

### 3. Auto-Cleanup
After all tests complete:
- Flattens any open positions
- Clears all test data from database
- Resets P&L for test user
- Verifies clean state

## Test Results

Example output:
```
============================================================
  JUICEBOT TRADE COMMANDS TEST SUITE
============================================================
  Suite: core
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

============================================================
📊 TEST SUMMARY
============================================================
📝 Total Tests: 10
✅ Passed: 10
❌ Failed: 0
🎉 ALL TESTS PASSED!
============================================================
```

## Flags

- `--fast`: Skip slow/complex tests
- `--symbol BYND`: Test with specific symbol (default: BYND)

## Requirements

- AI service running on port 8002
- Supabase connection configured
- venv activated
- aiohttp installed

## Files

- `.claude/commands/test.md` - Slash command documentation
- `test_trade_commands.py` - Main test suite
- `.claude/commands/test-trade.sh` - Wrapper script

## Integration with Claude Code

Type `/test` in Claude Code to see available test suites.

Run tests with:
```
/test trade core
/test trade core --fast
/test trade ai
/test trade all
```

