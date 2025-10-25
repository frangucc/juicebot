#!/usr/bin/env python3
"""
Create a test position in Supabase for testing chart position lines.
This creates: SHORT 1000 BYND @ $0.71
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from position_storage import PositionStorage

def create_test_position():
    """Create test SHORT position for BYND."""
    storage = PositionStorage(user_id="default_user")

    # Record position: SHORT 1000 BYND @ $0.71
    result = storage.record_position(
        symbol="BYND",
        side="short",
        quantity=1000,
        entry_price=0.71,
        current_price=0.71  # Entry price = current at time of entry
    )

    print("✅ Test position created!")
    print(result['fast_response'])
    print("\nPosition data:")
    print(result['position'])

if __name__ == "__main__":
    create_test_position()
