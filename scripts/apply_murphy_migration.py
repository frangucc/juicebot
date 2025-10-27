#!/usr/bin/env python3
"""
Apply Murphy Test Schema V2 Migration
======================================
Reads the SQL file and executes it against Supabase.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client, Client


def main():
    print("=" * 60)
    print("Murphy Test Schema V2 Migration")
    print("=" * 60)
    print()

    # Get Supabase credentials
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables required")
        print("   Make sure your .env file is set up correctly")
        sys.exit(1)

    print(f"✓ Found Supabase credentials")
    print(f"  URL: {url[:30]}...")
    print()

    # Read schema file
    schema_path = Path(__file__).parent.parent / "database" / "murphy_test_schema_v2.sql"
    if not schema_path.exists():
        print(f"❌ Error: Schema file not found: {schema_path}")
        sys.exit(1)

    print(f"📖 Reading schema from {schema_path.name}...")
    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    print(f"✓ Read {len(schema_sql)} characters")
    print()

    # Connect to Supabase
    print(f"🔌 Connecting to Supabase...")
    try:
        supabase: Client = create_client(url, key)
        print(f"✓ Connected successfully")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    print()
    print("🚀 Executing SQL migration...")
    print()

    # Execute via RPC call to Supabase
    # Note: Supabase Python client doesn't have direct SQL execution
    # We need to use the REST API or PostgREST
    try:
        # Use the Supabase REST API to execute raw SQL
        # This requires direct PostgreSQL connection or using Supabase's SQL execution endpoint

        # For now, we'll use psycopg2 if available
        try:
            import psycopg2
            from urllib.parse import urlparse

            # Parse Supabase URL to get PostgreSQL connection string
            # Supabase format: https://<project-ref>.supabase.co
            # PostgreSQL format: postgresql://postgres:<password>@<host>:5432/postgres

            print("📦 Using PostgreSQL direct connection...")

            # Check if we have DATABASE_URL environment variable
            db_url = os.environ.get("DATABASE_URL")
            if not db_url:
                print("⚠️  DATABASE_URL not found in environment")
                print("   Please add to .env file:")
                print("   DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres")
                print()
                print("   You can find this in Supabase Dashboard → Project Settings → Database")
                print()
                print("📋 Manual migration required:")
                print("   1. Go to Supabase Dashboard → SQL Editor")
                print("   2. Create new query")
                print(f"   3. Copy contents of: {schema_path}")
                print("   4. Run query")
                sys.exit(1)

            # Connect and execute
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()

            print("✓ PostgreSQL connection established")
            print("📝 Executing SQL...")

            cursor.execute(schema_sql)
            conn.commit()

            cursor.close()
            conn.close()

            print()
            print("✅ Migration completed successfully!")
            print()
            print("Created tables:")
            print("  ✓ murphy_test_sessions")
            print("  ✓ murphy_signal_records")
            print("  ✓ murphy_session_stats (view)")
            print()
            print("🎉 Murphy Test Lab is ready to use!")
            print()
            print("Next steps:")
            print("  1. Restart services: npm stop && npm start")
            print("  2. Type 'murphy live' in chat")
            print("  3. Click flask icon to see Test Lab")

        except ImportError:
            print("⚠️  psycopg2 not installed")
            print()
            print("Option 1: Install psycopg2")
            print("  pip install psycopg2-binary")
            print("  Then run this script again")
            print()
            print("Option 2: Manual migration (EASIER)")
            print("  1. Go to Supabase Dashboard → SQL Editor")
            print("  2. Create new query")
            print(f"  3. Copy contents of: {schema_path}")
            print("  4. Run query")
            print()
            sys.exit(1)

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("📋 Try manual migration:")
        print("  1. Go to Supabase Dashboard → SQL Editor")
        print("  2. Create new query")
        print(f"  3. Copy contents of: {schema_path}")
        print("  4. Run query")
        sys.exit(1)


if __name__ == "__main__":
    main()
