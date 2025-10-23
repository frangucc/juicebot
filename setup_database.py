#!/usr/bin/env python3
"""
Automatically set up the Supabase database by running the migration.
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def setup_database():
    """Run the database migration."""
    print("🗄️  Setting up Supabase database...")

    # Read the SQL migration file
    sql_file = "sql/001_init_schema.sql"

    with open(sql_file, 'r') as f:
        sql = f.read()

    # Connect to Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in .env")
        return False

    print(f"📡 Connecting to: {supabase_url}")

    # Note: Supabase Python client doesn't support raw SQL execution
    # You need to use the Supabase dashboard SQL Editor

    print("\n" + "="*60)
    print("⚠️  MANUAL STEP REQUIRED")
    print("="*60)
    print("\nThe Supabase Python client doesn't support running raw SQL.")
    print("You need to run the migration manually:\n")
    print("1. Open: https://szuvtcbytepaflthqnal.supabase.co")
    print("2. Click 'SQL Editor' in the left sidebar")
    print("3. Copy the contents of: sql/001_init_schema.sql")
    print("4. Paste into the SQL Editor")
    print("5. Click 'Run' (or press Cmd+Enter)")
    print("\nOr use this direct link:")
    print("https://supabase.com/dashboard/project/szuvtcbytepaflthqnal/sql/new")
    print("\n" + "="*60)

    return False

if __name__ == "__main__":
    setup_database()
