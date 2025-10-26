#!/usr/bin/env python3
"""
Test fast-path trade commands (no AI/LLM needed).
These should all execute in <50ms.
"""

import requests
import json
import time

API_URL = "http://localhost:8002"
SYMBOL = "BYND"

def test_command(message, description):
    """Test a trade command."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"📝 '{message}'")

    start = time.time()
    try:
        response = requests.post(
            f"{API_URL}/chat",
            json={"message": message, "symbol": SYMBOL},
            timeout=5
        )
        elapsed = (time.time() - start) * 1000  # ms

        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS ({elapsed:.0f}ms)")
            print(f"📤 {data['response']}")
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
║            FAST-PATH TRADE COMMANDS TEST                   ║
║        Testing Native Commands (No AI Required)            ║
╚════════════════════════════════════════════════════════════╝
    """)

    time.sleep(1)

    tests = [
        # === MARKET DATA (Fast) ===
        ("price", "Get current price"),
        ("last", "Get price (alias)"),
        ("volume", "Get volume"),
        ("vol", "Get volume (alias)"),
        ("range", "Get price range"),
        ("high", "Get high (alias)"),

        # === POSITION INQUIRY (Fast) ===
        ("position", "Check position (should be none)"),
        ("pos", "Check position (alias)"),

        # === ENTRY - Trading Notation (Fast) ===
        ("long 100 @ 0.57", "Open long position"),
        ("position", "Verify long position opened"),

        # Add to position (averaging)
        ("long 50 @ 0.60", "Add to long position (average in)"),
        ("position", "Check averaged position"),

        # === EXIT (Fast) ===
        ("close", "Close position"),
        ("position", "Verify closed"),

        # === REVERSAL (Fast) ===
        ("short 200 @ 0.68", "Open short position"),
        ("position", "Check short position"),

        ("long 200 @ 0.60", "Reverse: short → long"),
        ("position", "Check reversed to long"),

        # === FLATTEN (Fast) ===
        ("flat", "Flatten position (alias)"),
        ("position", "Verify flattened"),

        # === SCALE OUT (Fast) ===
        ("short 100 @ 0.65", "Open short for scale test"),
        ("position", "Check short before scaleout"),
        ("scaleout", "Scale out 25%"),
        ("position", "Check after scaleout"),

        # === ACCUMULATE (Fast) ===
        ("accumulate", "Accumulate 20% more"),
        ("position", "Check after accumulate"),

        # === REVERSE (Fast) ===
        ("reverse", "Reverse position"),
        ("position", "Check after reverse"),

        # === RISK MANAGEMENT (Fast - just sets values) ===
        ("stop", "Set stop loss"),
        ("bracket", "Create bracket order"),

        # === CLEANUP ===
        ("close", "Final cleanup"),
        ("position", "Final position check"),

        # === NATURAL LANGUAGE (Fast) ===
        ("exit", "Natural language: exit"),
        ("get me out", "Natural language: get me out"),
        ("sell everything", "Natural language: sell everything"),
    ]

    results = {"passed": 0, "failed": 0}

    for message, description in tests:
        success = test_command(message, description)
        if success:
            results["passed"] += 1
        else:
            results["failed"] += 1
        time.sleep(0.3)

    # Summary
    print(f"\n\n{'='*60}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Passed: {results['passed']}/{results['passed'] + results['failed']}")
    print(f"❌ Failed: {results['failed']}/{results['passed'] + results['failed']}")
    print(f"📈 Success Rate: {results['passed'] / (results['passed'] + results['failed']) * 100:.1f}%")
    print(f"{'='*60}\n")

    if results['failed'] == 0:
        print("🎉 ALL FAST-PATH COMMANDS WORKING!")
    else:
        print(f"⚠️  {results['failed']} test(s) failed.")

if __name__ == '__main__':
    main()
