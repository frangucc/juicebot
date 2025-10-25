#!/usr/bin/env python3
"""
Diagnostic test for AI service - tests each component independently
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import anthropic
from fast_classifier import TradingClassifier
from tools.market_data import (
    get_current_price,
    detect_fvg,
    detect_bos,
    detect_choch
)


async def test_bar_data():
    """Test 1: Check if classifier has bar data"""
    print("\n" + "="*80)
    print("TEST 1: Bar Data Availability")
    print("="*80)

    classifier = TradingClassifier()

    # Simulate some bar data
    test_bars = [
        {
            'timestamp': '2025-01-01T09:30:00',
            'open': 0.55,
            'high': 0.57,
            'low': 0.54,
            'close': 0.56,
            'volume': 10000
        },
        {
            'timestamp': '2025-01-01T09:31:00',
            'open': 0.56,
            'high': 0.58,
            'low': 0.55,
            'close': 0.57,
            'volume': 12000
        },
        {
            'timestamp': '2025-01-01T09:32:00',
            'open': 0.57,
            'high': 0.59,
            'low': 0.56,
            'close': 0.58,
            'volume': 15000
        }
    ]

    print(f"📊 Adding {len(test_bars)} test bars to classifier...")
    for bar in test_bars:
        classifier.update_market_data("BYND", bar)

    print(f"✓ Classifier now has {len(classifier.bar_history)} bars in history")
    print(f"✓ Latest bar: ${classifier.bar_history[-1]['close']} @ {classifier.bar_history[-1]['timestamp']}")

    return classifier


async def test_tools_with_data(classifier):
    """Test 2: Check if tools work with bar data"""
    print("\n" + "="*80)
    print("TEST 2: Tool Execution with Bar Data")
    print("="*80)

    bar_history = classifier.bar_history

    # Test get_current_price
    print("\n📍 Testing get_current_price...")
    try:
        result = await get_current_price("BYND", bar_history)
        print(f"   ✓ Result: {result}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test detect_fvg
    print("\n📍 Testing detect_fvg...")
    try:
        result = await detect_fvg("BYND", bar_history, lookback=10)
        print(f"   ✓ Result: Found {len(result)} FVGs")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test detect_bos
    print("\n📍 Testing detect_bos...")
    try:
        result = await detect_bos("BYND", bar_history, lookback=10)
        print(f"   ✓ Result: Found {len(result)} BoS patterns")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    # Test detect_choch
    print("\n📍 Testing detect_choch...")
    try:
        result = await detect_choch("BYND", bar_history, lookback=10)
        print(f"   ✓ Result: Found {len(result)} CHoCH patterns")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_claude_api():
    """Test 3: Check if Claude API is responsive"""
    print("\n" + "="*80)
    print("TEST 3: Claude API Connection")
    print("="*80)

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("✗ ANTHROPIC_API_KEY not found in environment")
        return False

    print(f"✓ API key found: {api_key[:20]}...")

    try:
        client = anthropic.Anthropic(api_key=api_key)

        print("\n📍 Testing simple Claude API call...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Say 'hello' if you can hear me"}
            ]
        )

        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        print(f"✓ Claude responded: {text}")
        return True

    except Exception as e:
        print(f"✗ Claude API error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_claude_with_tools(classifier):
    """Test 4: Full integration test with Claude + tools"""
    print("\n" + "="*80)
    print("TEST 4: Full Integration Test (Claude + Tools)")
    print("="*80)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    bar_history = classifier.bar_history

    # Define tool for Claude
    tools = [
        {
            "name": "get_current_price",
            "description": "Get the current price for BYND",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"}
                },
                "required": ["symbol"]
            }
        }
    ]

    print("\n📍 Asking Claude to call get_current_price tool...")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            messages=[
                {
                    "role": "user",
                    "content": "What is the current price of BYND? Use the get_current_price tool."
                }
            ]
        )

        print(f"✓ Claude responded with stop_reason: {response.stop_reason}")

        # Check if Claude called the tool
        if response.stop_reason == "tool_use":
            for block in response.content:
                if block.type == "tool_use":
                    print(f"✓ Claude called tool: {block.name}")
                    print(f"  Input: {block.input}")

                    # Execute the tool
                    result = await get_current_price(block.input["symbol"], bar_history)
                    print(f"  Tool result: {result}")

                    # Send result back to Claude
                    response2 = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1024,
                        tools=tools,
                        messages=[
                            {
                                "role": "user",
                                "content": "What is the current price of BYND? Use the get_current_price tool."
                            },
                            {
                                "role": "assistant",
                                "content": response.content
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": str(result)
                                    }
                                ]
                            }
                        ]
                    )

                    final_text = ""
                    for block2 in response2.content:
                        if hasattr(block2, "text"):
                            final_text += block2.text

                    print(f"✓ Claude's final response: {final_text}")
        else:
            print(f"⚠️ Claude did not call tool, response: {response.content}")

        return True

    except Exception as e:
        print(f"✗ Error during integration test: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_actual_classifier_state():
    """Test 5: Check actual classifier state in running service"""
    print("\n" + "="*80)
    print("TEST 5: Check Actual Running Service State")
    print("="*80)

    try:
        import httpx

        print("\n📍 Checking if AI service is running...")
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8002/")
            print(f"✓ AI service is running: {response.json()}")

            # Try to get a response from the chat endpoint
            print("\n📍 Sending test message to chat endpoint...")
            response = await client.post(
                "http://localhost:8002/chat",
                json={
                    "symbol": "BYND",
                    "message": "last",  # This should trigger fast-path
                    "conversation_id": "test_123"
                },
                timeout=30.0
            )

            result = response.json()
            print(f"✓ Chat response: {result}")

    except Exception as e:
        print(f"✗ Error checking service: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all diagnostic tests"""
    print("\n" + "="*80)
    print("🔍 AI SERVICE DIAGNOSTIC TEST SUITE")
    print("="*80)

    # Test 1: Bar data
    classifier = await test_bar_data()

    # Test 2: Tools with data
    await test_tools_with_data(classifier)

    # Test 3: Claude API
    claude_ok = await test_claude_api()

    # Test 4: Full integration
    if claude_ok:
        await test_claude_with_tools(classifier)

    # Test 5: Check running service
    await test_actual_classifier_state()

    print("\n" + "="*80)
    print("✓ DIAGNOSTIC COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
