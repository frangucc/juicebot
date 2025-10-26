#!/usr/bin/env python3
"""
JuiceBot Trade Commands Test Suite
===================================
Comprehensive testing of all trade commands with real database operations.
"""

import sys
import os
import asyncio
import json
import argparse
from datetime import datetime
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from shared.database import supabase

# Test configuration
TEST_SYMBOL = "BYND"
TEST_USER_ID = None  # Will use default/anonymous user
AI_SERVICE_URL = "http://localhost:8002/chat"

class TradeTestSuite:
    """Test suite for trade commands."""
    
    def __init__(self, symbol: str = TEST_SYMBOL, fast_mode: bool = False):
        self.symbol = symbol
        self.fast_mode = fast_mode
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    def log(self, emoji: str, message: str):
        """Log test output."""
        print(f"{emoji} {message}")
    
    async def execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a trade command via API."""
        import aiohttp
        
        payload = {
            "message": command,
            "symbol": self.symbol,
            "user_id": TEST_USER_ID
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(AI_SERVICE_URL, json=payload, timeout=5) as resp:
                    return await resp.json()
            except Exception as e:
                return {"error": str(e)}
    
    def get_position(self) -> Dict[str, Any]:
        """Get current open position from database."""
        query = supabase.table('trades').select('*')\
            .eq('symbol', self.symbol)\
            .eq('status', 'open')

        if TEST_USER_ID:
            query = query.eq('user_id', TEST_USER_ID)
        else:
            query = query.is_('user_id', 'null')

        result = query.order('entry_time', desc=True)\
            .limit(1)\
            .execute()

        return result.data[0] if result.data else None
    
    def clear_all_positions(self):
        """Clear all positions for test user."""
        self.log("🧹", "Clearing all test positions...")

        # Build query for user
        if TEST_USER_ID:
            # Close all open positions
            supabase.table('trades').update({'status': 'closed'})\
                .eq('user_id', TEST_USER_ID)\
                .eq('status', 'open')\
                .execute()

            # Delete all test user trades
            supabase.table('trades').delete()\
                .eq('user_id', TEST_USER_ID)\
                .execute()
        else:
            # For anonymous/null user, close open positions for test symbol
            supabase.table('trades').update({'status': 'closed'})\
                .eq('symbol', self.symbol)\
                .is_('user_id', 'null')\
                .eq('status', 'open')\
                .execute()

            # Delete test symbol trades for null user
            supabase.table('trades').delete()\
                .eq('symbol', self.symbol)\
                .is_('user_id', 'null')\
                .execute()

        self.log("✓", "All positions cleared")
    
    def assert_position(self, expected_side: str = None, expected_qty: int = None, 
                       expected_min_qty: int = None):
        """Assert position state."""
        pos = self.get_position()
        
        if expected_side is None and expected_qty is None:
            # Expecting no position
            if pos:
                raise AssertionError(f"Expected no position, but found {pos['side']} {pos['quantity']}")
            return True
        
        if not pos:
            raise AssertionError(f"Expected position {expected_side} {expected_qty}, but found none")
        
        if expected_side and pos['side'] != expected_side:
            raise AssertionError(f"Expected {expected_side}, got {pos['side']}")
        
        if expected_qty and pos['quantity'] != expected_qty:
            raise AssertionError(f"Expected qty {expected_qty}, got {pos['quantity']}")
        
        if expected_min_qty and pos['quantity'] < expected_min_qty:
            raise AssertionError(f"Expected qty >= {expected_min_qty}, got {pos['quantity']}")
        
        return True
    
    async def test(self, name: str, command: str, assertion_func=None):
        """Run a single test."""
        self.total_tests += 1
        
        try:
            self.log("▶️", f"Test {self.total_tests}: {name}")
            self.log("📝", f"Command: '{command}'")
            
            # Execute command
            response = await self.execute_command(command)
            
            # Check for errors
            if "error" in response:
                raise Exception(f"API Error: {response['error']}")
            
            # Run assertion if provided
            if assertion_func:
                assertion_func()
            
            self.log("✅", f"PASSED: {name}")
            self.passed_tests += 1
            self.results.append({"test": name, "status": "PASSED"})
            print()
            
        except Exception as e:
            self.log("❌", f"FAILED: {name}")
            self.log("💥", f"Error: {str(e)}")
            self.failed_tests += 1
            self.results.append({"test": name, "status": "FAILED", "error": str(e)})
            print()
    
    async def run_core_tests(self):
        """Run core fast-path command tests."""
        self.log("🚀", "=== CORE TESTS: Fast-Path Commands ===")
        print()
        
        # Clear before starting
        self.clear_all_positions()
        
        # Test 1: Market buy
        await self.test(
            "Market Buy - Long 100",
            "buy 100",
            lambda: self.assert_position('long', 100)
        )
        
        # Test 2: Position check
        await self.test(
            "Position Check",
            "pos",
            lambda: self.assert_position('long', 100)
        )

        # Test 3: P&L Summary (pl)
        await self.test(
            "P&L Summary - pl",
            "pl",
            None  # No position assertion, just checks command works
        )

        # Test 4: P&L Summary (pnl alias)
        await self.test(
            "P&L Summary - pnl",
            "pnl",
            None
        )

        # Test 5: P&L Summary (profit alias)
        await self.test(
            "P&L Summary - profit",
            "profit",
            None
        )

        # Test 7: Accumulate
        await self.test(
            "Accumulate - Add 50",
            "add 50",
            lambda: self.assert_position('long', 150)
        )

        # Test 8: Scale out 50%
        await self.test(
            "Scale Out 50%",
            "sell half",
            lambda: self.assert_position('long', 75)
        )

        # Test 9: Flatten
        await self.test(
            "Flatten Position",
            "flat",
            lambda: self.assert_position(None, None)
        )

        # Test 10: Limit order
        await self.test(
            "Limit Buy - Long 200 @ 0.55",
            "long 200 @ 0.55",
            lambda: self.assert_position('long', 200)
        )

        # Test 11: Reverse
        await self.test(
            "Reverse to Short",
            "reverse",
            lambda: self.assert_position('short', expected_min_qty=1)
        )

        # Test 12: Market data - Price
        await self.test(
            "Get Price",
            "price",
            None  # No position assertion
        )

        # Test 13: Market data - Volume
        await self.test(
            "Get Volume",
            "volume",
            None
        )

        # Test 14: Flatten final
        await self.test(
            "Final Flatten",
            "flat",
            lambda: self.assert_position(None, None)
        )
    
    async def run_advanced_tests(self):
        """Run advanced command tests (bracket, stops, etc.)."""
        if self.fast_mode:
            self.log("⏭️", "Skipping advanced tests (--fast mode)")
            return

        self.log("🛡️", "=== ADVANCED TESTS: Bracket & Stop Orders ===")
        print()

        # Clear before starting
        self.clear_all_positions()

        # Test 1: Simple bracket order with explicit prices
        await self.test(
            "Bracket Order - Long with Stop & Target",
            "bracket long 100 @ 0.55 stop 0.50 target 0.70",
            lambda: self.assert_position('long', expected_min_qty=1)
        )

        # Cleanup
        await self.execute_command("flat")

        # Test 2: Bracket order short
        await self.test(
            "Bracket Order - Short with Stop & Target",
            "bracket short 200 @ 0.60 stop 0.65 target 0.50",
            lambda: self.assert_position('short', expected_min_qty=1)
        )

        # Cleanup
        await self.execute_command("flat")

        # Test 3: Set stop loss on existing position
        await self.test(
            "Enter Long Position",
            "long 100 @ 0.55",
            lambda: self.assert_position('long', 100)
        )

        await self.test(
            "Set Stop Loss",
            "stop 0.50",
            lambda: self.assert_position('long', 100)  # Position should still exist
        )

        # Cleanup
        await self.execute_command("flat")

        # Test 4: Bracket with market entry
        await self.test(
            "Bracket Market Entry",
            "bracket long 150",
            lambda: self.assert_position('long', expected_min_qty=1)
        )

        # Cleanup
        await self.execute_command("flat")

        # Test 5: Interactive scaleout - Prompt
        await self.test(
            "Enter Position for Scaleout",
            "long 1000 @ 0.55",
            lambda: self.assert_position('long', 1000)
        )

        await self.test(
            "Interactive Scaleout - Prompt Display",
            "scaleout",
            None  # Just verify the prompt appears without errors
        )

        # Test 6: Interactive scaleout - FAST mode execution
        # Note: This simulates user selecting option 1 (FAST)
        await self.test(
            "Interactive Scaleout - Select FAST (1)",
            "1",
            lambda: self.assert_position('long', expected_min_qty=1)  # Position should start reducing
        )

        # Give worker a moment to execute first chunk
        await asyncio.sleep(2)

        # Verify position is being reduced
        pos = self.get_position()
        if pos and pos['quantity'] < 1000:
            self.log("✓", f"Scaleout working: Position reduced to {pos['quantity']}")

        # Cleanup - flatten any remaining position
        await self.execute_command("flat")

        # Test 7: Interactive scaleout - MEDIUM mode
        await self.test(
            "Enter Position for Medium Scaleout",
            "long 800 @ 0.55",
            lambda: self.assert_position('long', 800)
        )

        await self.test(
            "Interactive Scaleout - Prompt for Medium",
            "scaleout",
            None
        )

        await self.test(
            "Interactive Scaleout - Select MEDIUM (2)",
            "2",
            lambda: self.assert_position('long', expected_min_qty=1)
        )

        # Give worker a moment
        await asyncio.sleep(2)

        # Cleanup
        await self.execute_command("flat")

        # Test 8: Interactive scaleout - SLOW mode
        await self.test(
            "Enter Position for Slow Scaleout",
            "short 500 @ 0.60",
            lambda: self.assert_position('short', 500)
        )

        await self.test(
            "Interactive Scaleout - Prompt for Slow",
            "scaleout",
            None
        )

        await self.test(
            "Interactive Scaleout - Select SLOW (3)",
            "3",
            lambda: self.assert_position('short', expected_min_qty=1)
        )

        # Give worker a moment
        await asyncio.sleep(2)

        # Cleanup
        await self.execute_command("flat")

    async def run_ai_tests(self):
        """Run AI-assisted command tests."""
        if self.fast_mode:
            self.log("⏭️", "Skipping AI tests (--fast mode)")
            return

        self.log("🤖", "=== AI TESTS: Natural Language Commands ===")
        print()

        # Clear before starting
        self.clear_all_positions()

        # Test natural language commands that require LLM
        await self.test(
            "Natural Language - Entry",
            "I want to go long 100 shares at fifty five cents",
            lambda: self.assert_position('long', expected_min_qty=1)
        )

        # Cleanup
        await self.execute_command("flat")
    
    def print_summary(self):
        """Print test summary."""
        print()
        print("=" * 60)
        self.log("📊", "TEST SUMMARY")
        print("=" * 60)
        self.log("📝", f"Total Tests: {self.total_tests}")
        self.log("✅", f"Passed: {self.passed_tests}")
        self.log("❌", f"Failed: {self.failed_tests}")
        
        if self.failed_tests == 0:
            self.log("🎉", "ALL TESTS PASSED!")
        else:
            self.log("⚠️", f"{self.failed_tests} test(s) failed")
        
        print("=" * 60)
        
        # Cleanup
        self.log("🧹", "Cleaning up test data...")
        self.clear_all_positions()
        self.log("✓", "Cleanup complete")
    
    async def run_all(self, suite: str):
        """Run specified test suite."""
        if suite in ['core', 'all']:
            await self.run_core_tests()

        if suite == 'all':
            await self.run_advanced_tests()

        if suite in ['ai', 'all']:
            await self.run_ai_tests()

        self.print_summary()

        return self.failed_tests == 0


async def main():
    parser = argparse.ArgumentParser(description='Test JuiceBot trade commands')
    parser.add_argument('suite', choices=['core', 'ai', 'all'], 
                       help='Test suite to run')
    parser.add_argument('--fast', action='store_true',
                       help='Skip slow tests')
    parser.add_argument('--symbol', default='BYND',
                       help='Symbol to test with')
    
    args = parser.parse_args()
    
    print()
    print("=" * 60)
    print("  JUICEBOT TRADE COMMANDS TEST SUITE")
    print("=" * 60)
    print(f"  Suite: {args.suite}")
    print(f"  Symbol: {args.symbol}")
    print(f"  Fast Mode: {args.fast}")
    print("=" * 60)
    print()
    
    tester = TradeTestSuite(symbol=args.symbol, fast_mode=args.fast)
    success = await tester.run_all(args.suite)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
