# `/test` Command - Integration Testing Guide

## Overview

The `/test` command runs comprehensive integration tests for all chat commands (Fast and AI) with real-time progress tracking and detailed results.

## Usage

### 1. Basic Test (All Fast Commands)
```
/test
```

Runs all Fast (F) commands and then prompts you to test AI commands.

### 2. Quick AI Test (No LLM Calls)
```
/test ai -quick
```

Tests Fast commands + AI command recognition without actually calling Claude (fast).

### 3. Interactive Mode
```
/test
```
Then when prompted:
- Type `yes` - Full AI test with LLM calls
- Type `quick` - Quick AI test (no LLM)
- Type `no` - Skip AI tests

## What Gets Tested

### Fast Commands (F)
Tests instant-response commands:
- ✅ `last` / `price` - Current price
- ✅ `volume` / `vol` - Current volume
- ✅ `high` / `low` - Today's range
- ✅ `long 100 @ 0.50` - Position entry
- ✅ `pos` / `position` - Position status
- ✅ `close position` - Close position

### AI Commands (LLM)
Tests Claude-powered analysis:
- ✅ "What do you see on the chart?"
- ✅ "Where should I enter?"
- ✅ "What are the key levels?"

## Test Output

### Progress Display
Each test shows real-time results:
```
🟢 last - PASS
🟢 volume - PASS
🔴 pos - FAIL
```

- 🟢 = Test passed
- 🔴 = Test failed

### Summary Report
After all tests complete:
```
📊 TEST SUMMARY
═══════════════════════════════════
Total: 10 tests
Passed: 🟢 9
Failed: 🔴 1
Success Rate: 90.0%

Fast Commands (F): 6/7
AI Commands (LLM): 3/3

Failed Tests:
🔴 pos: Expected pattern not found: /(LONG|SHORT|No open position)/

```

## How It Works

### 1. Fast Command Testing
For each fast command:
1. Sends command to AI service (`localhost:8002`)
2. Validates response matches expected pattern
3. Shows result with 🟢/🔴
4. Waits 300ms between tests
5. Tracks pass/fail

### 2. AI Command Testing (Full Mode)
For each AI command:
1. Sends question to Claude via AI service
2. Validates response length (> 10 chars)
3. Shows result
4. Waits 1s between tests (for LLM)
5. Tracks pass/fail

### 3. AI Command Testing (Quick Mode)
For each AI command:
1. Just checks command is recognized
2. Marks as PASS immediately
3. No actual LLM call
4. Waits 100ms between tests
5. Fast validation only

## Expected Patterns

Each test validates responses using regex:

| Command | Pattern | Example Match |
|---------|---------|---------------|
| `last` | `/\$[\d.]+/` | "$0.57" |
| `volume` | `/Vol:/` | "Vol: 1,234" |
| `high` | `/High:.*Low:/` | "High: $0.70 \| Low: $0.55" |
| `long 100 @ 0.50` | `/✓ (LONG\|CLOSED)/` | "✓ LONG 100 BYND @ $0.50" |
| `pos` | `/(LONG\|SHORT\|No open position)/` | "LONG 100 BYND @ $0.50" |
| `close` | `/(✓ CLOSED\|No open position)/` | "✓ CLOSED LONG 100 BYND" |

## Test Modes

### Full Mode (default)
- Tests all Fast commands with validation
- Prompts for AI testing
- If yes: Calls Claude for each AI command
- Takes ~10-15 seconds total

### Quick Mode (`/test ai -quick`)
- Tests all Fast commands with validation
- Tests AI commands without LLM calls
- Just validates commands are recognized
- Takes ~3-5 seconds total

## Use Cases

### 1. Pre-Deployment Testing
```
/test
> yes
```
Full validation before pushing code.

### 2. Quick Health Check
```
/test ai -quick
```
Verify commands work without waiting for LLM.

### 3. Fast Commands Only
```
/test
> no
```
Test just the instant commands.

### 4. Debugging Specific Commands
Run `/test` and check which commands fail in the summary.

## Example Session

```
User: /test

Bot: 🧪 INTEGRATION TEST STARTED
Mode: full

Testing Fast Commands (F)...
🟢 last - PASS
🟢 price - PASS
🟢 volume - PASS
🟢 high - PASS
🟢 long 100 @ 0.50 - PASS
🟢 pos - PASS
🟢 close position - PASS

Fast command tests complete: 7/7 passed

Test AI commands? Type:
  'yes' - Full AI test (with LLM calls)
  'quick' - Quick test (no LLM)
  'no' - Skip AI tests

User: yes

Bot: Testing AI Commands (FULL MODE)...
🟢 "What do you see on the chart?" - PASS
🟢 "Where should I enter?" - PASS
🟢 "What are the key levels?" - PASS

📊 TEST SUMMARY
═══════════════════════════════════
Total: 10 tests
Passed: 🟢 10
Failed: 🔴 0
Success Rate: 100.0%

Fast Commands (F): 7/7
AI Commands (LLM): 3/3

✅ All tests passed!
```

## Integration with AI Service

The test command communicates with your AI service on `localhost:8002`:

```typescript
fetch('http://localhost:8002/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    symbol: 'BYND',  // Current chart symbol
    message: 'last',  // Test command
    conversation_id: 'test_12345'
  })
})
```

## Troubleshooting

### Test Fails: "No live data"
**Problem**: AI service not receiving market data
**Fix**: Ensure WebSocket is connected and streaming bars

### Test Fails: "Error: Failed to fetch"
**Problem**: AI service not running
**Fix**: Start AI service with `npm start`

### Test Fails: Position commands
**Problem**: Supabase connection or position storage issue
**Fix**: Check `position_storage.py` and database connection

### AI Tests Timeout
**Problem**: Claude API taking too long
**Fix**: Use `/test ai -quick` to skip LLM calls

## Adding New Tests

To add a new fast command test, edit `ChatInterface.tsx`:

```typescript
const fastTests = [
  // ... existing tests
  {
    cmd: 'your_command',
    type: 'F' as const,
    expectedPattern: /expected regex/
  },
]
```

To add a new AI test:

```typescript
const aiTests = [
  // ... existing tests
  {
    cmd: 'Your AI question?',
    type: 'LLM' as const
  },
]
```

## Command Reference

| Command | Mode | Duration | LLM Calls |
|---------|------|----------|-----------|
| `/test` | Interactive | ~10-15s | If yes |
| `/test ai -quick` | Quick | ~3-5s | No |
| `/test` + `no` | Fast only | ~2-3s | No |
| `/test` + `yes` | Full | ~15-20s | Yes |
| `/test` + `quick` | Quick AI | ~5-8s | No |

## Success Criteria

A test **passes** if:
- Response received within timeout
- Response matches expected pattern
- No errors thrown

A test **fails** if:
- No response received
- Response doesn't match pattern
- Network error
- Service error

## Performance Notes

- Fast commands: ~300ms each
- AI commands (full): ~1-2s each
- AI commands (quick): ~100ms each
- Total with AI: ~15-20 seconds
- Total without AI: ~3-5 seconds

## Status Codes

The test uses these status indicators:
- 🟢 **PASS** - Test passed successfully
- 🔴 **FAIL** - Test failed validation
- 🧪 **TESTING** - Test in progress
- 📊 **SUMMARY** - Final results

---

**Pro Tip**: Run `/test ai -quick` before committing code for fast validation!