#!/bin/bash

echo "=== Testing Position Tracking ==="
echo ""

echo "1. Current Price:"
curl -s -X POST http://localhost:8002/chat -H "Content-Type: application/json" -d '{"message": "price", "symbol": "BYND"}'
echo ""
echo ""

echo "2. Check Position:"
curl -s -X POST http://localhost:8002/chat -H "Content-Type: application/json" -d '{"message": "position", "symbol": "BYND"}'
echo ""
echo ""

echo "3. Flatten Position:"
curl -s -X POST http://localhost:8002/chat -H "Content-Type: application/json" -d '{"message": "flat", "symbol": "BYND"}'
echo ""
echo ""

echo "4. Verify Closed:"
curl -s -X POST http://localhost:8002/chat -H "Content-Type: application/json" -d '{"message": "position", "symbol": "BYND"}'
echo ""
