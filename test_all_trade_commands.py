#!/usr/bin/env python3
"""
Test all 16 trade commands end-to-end.
"""

import requests
import json
import time

API_URL = "http://localhost:8002"
SYMBOL = "BYND"

def test_command(message, description):
    """Test a trade command."""
    print(f"\n{'='*60}")
    print(f"🧪 TEST: {description}")
    print(f"📝 Message: \"{message}\"")
    print(f"{'='*60}")

    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={"message": message, "symbol": SYMBOL},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS")
            print(f"📤 Response:\n{data['response']}\n")
            return True
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║         TRADE COMMAND SYSTEM - FULL TEST SUITE            ║
║                  Testing All 16 Commands                   ║
╚════════════════════════════════════════════════════════════╝
    """)

    # Wait for services to be ready
    print("⏳ Waiting for services...")
    time.sleep(2)

    tests = [
        # Market Data Commands (should work immediately)
        ("price", "Get current price"),
        ("volume", "Get current volume"),
        ("range", "Get price range"),
        ("last", "Get last price (alias)"),
        ("vol", "Get volume (alias)"),

        # Position Inquiry
        ("position", "Check position status"),
        ("pos", "Check position (alias)"),

        # Entry Commands - with trading notation
        ("long 100 @ 0.57", "Open long position"),
        ("position", "Check long position after entry"),

        # Exit Commands
        ("close", "Close position"),
        ("position", "Verify position closed"),

        # Entry again for testing other commands
        ("short 50 @ 0.68", "Open short position"),
        ("position", "Check short position"),

        # Advanced Exit Commands
        ("scaleout", "Scale out of position (25%)"),
        ("position", "Check position after scaleout"),

        # Accumulate Command
        ("accumulate", "Accumulate into position"),
        ("position", "Check position after accumulate"),

        # Flatten Commands
        ("flat", "Flatten position (alias)"),
        ("position", "Verify flattened"),

        # Reversal Commands
        ("long 200 @ 0.60", "Open long for reversal test"),
        ("reverse", "Reverse position (long → short)"),
        ("position", "Check reversed position"),

        # Smart Commands
        ("reverse-smart", "Smart reverse with AI check"),
        ("position", "Check after smart reverse"),

        # Gradual Exit
        ("flatten-smart", "Smart flatten (50% immediate)"),
        ("position", "Check after smart flatten"),

        # Risk Management
        ("stop", "Set stop loss"),
        ("bracket", "Create bracket order"),

        # Session Management
        ("close", "Clean up - close position"),
        ("reset", "Reset session P&L"),

        # Natural Language Phrases
        ("get me out", "Natural language: exit"),
        ("what's my position", "Natural language: position inquiry"),
        ("buy me 10 shares @ 0.55", "Natural language: long entry - SHOULD FAIL (needs 'long' keyword)"),
        ("long 10 @ 0.55", "Corrected: proper long entry"),
    ]

    results = {"passed": 0, "failed": 0}

    for message, description in tests:
        success = test_command(message, description)
        if success:
            results["passed"] += 1
        else:
            results["failed"] += 1

        time.sleep(0.5)  # Brief pause between tests

    # Print summary
    print(f"\n\n{'='*60}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"📈 Success Rate: {results['passed'] / (results['passed'] + results['failed']) * 100:.1f}%")
    print(f"{'='*60}\n")

    if results['failed'] == 0:
        print("🎉 ALL TESTS PASSED! Trade command system fully operational!")
    else:
        print(f"⚠️  {results['failed']} test(s) failed. Review errors above.")

if __name__ == '__main__':
    main()
