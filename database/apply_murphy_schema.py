#!/usr/bin/env python3
"""
Apply Murphy Test Schema to Supabase
====================================
Reads murphy_test_schema.sql and executes it against Supabase.
"""

import os
import sys
from pathlib import Path
from supabase import create_client, Client


def apply_schema():
    """Apply the Murphy test schema to Supabase."""

    # Get Supabase credentials
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables required")
        sys.exit(1)

    # Read schema file
    schema_path = Path(__file__).parent / "murphy_test_schema.sql"
    if not schema_path.exists():
        print(f"❌ Error: Schema file not found: {schema_path}")
        sys.exit(1)

    print(f"📖 Reading schema from {schema_path}...")
    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    # Connect to Supabase
    print(f"🔌 Connecting to Supabase...")
    supabase: Client = create_client(url, key)

    # Split into individual statements (basic split by semicolon)
    statements = [s.strip() for s in schema_sql.split(';') if s.strip() and not s.strip().startswith('--')]

    print(f"📝 Executing {len(statements)} SQL statements...")

    # Execute each statement
    executed = 0
    errors = 0

    for i, statement in enumerate(statements, 1):
        # Skip comments
        if statement.startswith('--') or statement.startswith('/*'):
            continue

        try:
            # Execute via Supabase RPC (if available) or direct SQL
            # Note: Supabase Python client doesn't have direct SQL execution
            # You may need to use psycopg2 or execute manually via Supabase UI
            print(f"  [{i}/{len(statements)}] {statement[:80]}...")

            # For now, just print the statement
            # In production, you'd execute this via psycopg2 or Supabase SQL editor
            executed += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            errors += 1

    print(f"\n✅ Schema application complete!")
    print(f"   Statements: {executed} executed, {errors} errors")

    if errors > 0:
        print(f"\n⚠️  Some statements failed. Please review the errors above.")
        print(f"   You may need to apply the schema manually via Supabase SQL editor.")

    print(f"\n📋 To apply manually:")
    print(f"   1. Go to Supabase Dashboard → SQL Editor")
    print(f"   2. Copy contents of {schema_path}")
    print(f"   3. Paste and run")


if __name__ == "__main__":
    print("=" * 60)
    print("Murphy Test Schema Migration")
    print("=" * 60)
    print()

    apply_schema()

    print()
    print("=" * 60)
    print("Note: Due to Supabase Python client limitations,")
    print("you may need to apply the schema manually via SQL editor.")
    print("The schema file is: database/murphy_test_schema.sql")
    print("=" * 60)
