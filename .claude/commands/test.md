---
description: Run comprehensive test suites for JuiceBot
---

# Test Suite Runner

Available test suites:

## /test trade
Test all trading commands and position tracking

**Usage:**
```
/test trade core      # Test fast-path commands (entry, exit, position)
/test trade core --fast    # Skip slow tests (bracket orders, trail stops)
/test trade ai        # Test AI-assisted commands
/test trade all       # Run all trade tests
```

## /test trade core

Tests the following commands:
- Entry: long, short, buy, sell (market & limit)
- Exit: flat, close, sell all/half/percentage
- Position: pos, position, accumulate, scaleout
- Market data: price, volume, range
- Reversals: reverse, flip

**Flags:**
- `--fast`: Skip complex tests (bracket, trail, smart commands)
- `--symbol BYND`: Test with specific symbol (default: BYND)
- `--cleanup`: Flatten and clear P&L after tests

## /test trade ai

Tests AI-assisted commands:
- Smart flatten (gradual exits)
- Smart reverse (safe reversals)
- Bracket orders with stops/targets
- Trailing stops
- Natural language commands

---

**Auto-cleanup:** All tests automatically:
1. Flatten all positions
2. Clear open P&L
3. Reset daily P&L for test user
4. Verify database state

---

To run tests, use:
```
/test trade core
/test trade core --fast
/test trade ai
```
