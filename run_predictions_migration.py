#!/usr/bin/env python3
"""
Run the trade_predictions table migration.
This creates the table for storing LLM predictions and outcomes.
"""

import asyncio
import os
from supabase import create_client, Client

async def run_migration():
    """Run the 005_trade_predictions migration."""

    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        return False

    print("🔧 Connecting to Supabase...")
    supabase: Client = create_client(supabase_url, supabase_key)

    # Read migration file
    migration_file = "migrations/005_trade_predictions.sql"
    print(f"📄 Reading migration: {migration_file}")

    with open(migration_file, 'r') as f:
        sql = f.read()

    # Execute migration
    print("🚀 Running migration...")
    try:
        # Split by semicolons to execute each statement separately
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

        for i, statement in enumerate(statements, 1):
            if statement:
                print(f"  Executing statement {i}/{len(statements)}...")
                result = supabase.rpc('exec_sql', {'sql': statement}).execute()

        print("✅ Migration completed successfully!")
        print("\n📊 Created table: trade_predictions")
        print("   - Stores all LLM predictions with confidence scores")
        print("   - Tracks outcomes for reinforcement learning")
        print("   - Ready for continuous improvement system")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        print("\n💡 Note: You may need to run this SQL manually in Supabase SQL Editor")
        print(f"   The SQL is in: {migration_file}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)
