#!/bin/bash

echo "=== COMPREHENSIVE TRADE COMMAND TESTS ==="
echo ""
echo "Starting Position: SHORT 200 @ $0.60"
echo ""

# Test 1: Flatten current position
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 1: Flatten Position"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "flat", "symbol": "BYND"}' | jq -r '.response'
echo ""
sleep 1

# Test 2: Enter long position
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 2: Go Long 500 shares"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "long 500", "symbol": "BYND"}' | jq -r '.response'
echo ""
sleep 1

# Test 3: Check position
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 3: Check Position"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "pos", "symbol": "BYND"}' | jq -r '.response'
echo ""
sleep 1

# Test 4: Accumulate (add to position)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 4: Accumulate - Add 300 more"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "accumulate 300", "symbol": "BYND"}' | jq -r '.response'
echo ""
sleep 1

# Test 5: Check position after accumulate
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 5: Position After Accumulate (should be 800)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "pos", "symbol": "BYND"}' | jq -r '.response'
echo ""
sleep 1

# Test 6: Scale out
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 6: Scale Out 400 shares"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "scaleout 400", "symbol": "BYND"}' | jq -r '.response'
echo ""
sleep 1

# Test 7: Position after scale out
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 7: Position After Scale Out (should be 400)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "pos", "symbol": "BYND"}' | jq -r '.response'
echo ""
sleep 1

# Test 8: Reverse position
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 8: Reverse to Short 600"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "reverse 600", "symbol": "BYND"}' | jq -r '.response'
echo ""
sleep 1

# Test 9: Position after reversal
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 9: Position After Reversal (should be SHORT 600)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "pos", "symbol": "BYND"}' | jq -r '.response'
echo ""
sleep 1

# Test 10: Bracket order
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 10: Bracket Order - Long 1000 with stops"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "bracket long 1000 stop 0.55 target 0.75", "symbol": "BYND"}' | jq -r '.response'
echo ""
sleep 1

# Test 11: Final position check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 11: Final Position Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "pos", "symbol": "BYND"}' | jq -r '.response'
echo ""
sleep 1

# Test 12: Flatten everything
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST 12: Final Flatten"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "flat", "symbol": "BYND"}' | jq -r '.response'
echo ""

echo ""
echo "=== TEST COMPLETE ==="
echo "Checking final database state..."
echo ""
