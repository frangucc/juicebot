#!/usr/bin/env python3
"""Run the historical data tables migration via Supabase."""

from shared.config import settings
import psycopg2

# Read migration file
with open('migrations/003_historical_data_tables.sql', 'r') as f:
    migration_sql = f.read()

print("Connecting to Supabase database...")
print(f"Database URL: {settings.database_url[:30]}...")

# Connect using DATABASE_URL from settings
conn = psycopg2.connect(settings.database_url)
cursor = conn.cursor()

print("\nRunning migration: 003_historical_data_tables.sql")
print("=" * 80)

try:
    # Execute migration
    cursor.execute(migration_sql)
    conn.commit()

    print("✅ Migration completed successfully!\n")

    # Verify tables were created
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('historical_bars', 'historical_symbols')
        ORDER BY table_name
    """)

    tables = cursor.fetchall()
    print("Tables created:")
    for table in tables:
        print(f"  ✓ {table[0]}")

    # Check view
    cursor.execute("""
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = 'public'
        AND table_name = 'historical_data_summary'
    """)

    views = cursor.fetchall()
    if views:
        print("\nViews created:")
        for view in views:
            print(f"  ✓ {view[0]}")

    print("\n" + "=" * 80)
    print("Ready to fetch historical data!")
    print("\nNext step: python test_historical_bynd.py")

except Exception as e:
    conn.rollback()
    print(f"❌ Migration failed: {e}")
    import traceback
    traceback.print_exc()

finally:
    cursor.close()
    conn.close()
