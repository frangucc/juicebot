#!/usr/bin/env python3
"""
Run database migration to add session columns.
This script applies the migration using Supabase's REST API.
"""

from shared.config import settings
import requests

# Read the migration SQL
with open('migrations/add_session_columns.sql') as f:
    sql = f.read()

print("=" * 80)
print("DATABASE MIGRATION: Add Session Columns")
print("=" * 80)
print()
print("This migration adds the following columns to symbol_state:")
print("  - pre_market_open (DECIMAL)")
print("  - rth_open (DECIMAL)")
print("  - post_market_open (DECIMAL)")
print("  - pct_from_pre (DECIMAL)")
print("  - pct_from_post (DECIMAL)")
print()
print("=" * 80)
print()

# For Supabase, we need to run this via the SQL Editor or direct psql connection
print("⚠️  MANUAL STEP REQUIRED:")
print()
print("Please run the following SQL in Supabase Dashboard → SQL Editor:")
print()
print("-" * 80)
print(sql)
print("-" * 80)
print()
print("After running the migration, the scanner will automatically start")
print("populating the new columns.")
print()
print("✅ Migration script ready at: migrations/add_session_columns.sql")
