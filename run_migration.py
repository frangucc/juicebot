#!/usr/bin/env python3
"""
Run database migration using direct PostgreSQL connection
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def run_migration():
    # Supabase connection - try with IPv4 pooler
    db_url = os.getenv("DATABASE_URL")

    # Try connection pooler endpoint (port 6543) if direct connection fails
    pooler_url = db_url.replace(':5432/', ':6543/')

    print("Running database migration...")
    print("=" * 60)
    print("\nThis migration adds session-specific baseline columns:")
    print("  - pre_market_open, rth_open, post_market_open")
    print("  - pct_from_pre, pct_from_post")
    print()

    # Read the SQL file
    with open("migrations/add_session_columns.sql", "r") as f:
        sql = f.read()

    # Try direct connection first
    for attempt, url in enumerate([db_url, pooler_url], 1):
        try:
            print(f"\nAttempt {attempt}: Connecting to database...")
            port = "5432" if attempt == 1 else "6543 (pooler)"
            print(f"Using port: {port}")

            conn = psycopg2.connect(url)
            conn.autocommit = True
            cursor = conn.cursor()

            print("✅ Connected successfully!")
            print("\nExecuting migration SQL...")

            # Execute the entire SQL file
            cursor.execute(sql)

            print("✅ Migration completed successfully!")

            # Verify columns were added
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'symbol_state'
                AND column_name IN ('pre_market_open', 'rth_open', 'post_market_open', 'pct_from_pre', 'pct_from_post')
                ORDER BY column_name;
            """)

            columns = cursor.fetchall()
            print("\n📊 New columns in symbol_state table:")
            for col in columns:
                print(f"  ✅ {col[0]} ({col[1]})")

            cursor.close()
            conn.close()

            print("\n" + "=" * 60)
            print("🎉 Migration complete! Scanner will now track pre % and post % changes.")
            return

        except psycopg2.OperationalError as e:
            print(f"❌ Connection failed: {e}")
            if attempt == 2:
                print("\n" + "=" * 60)
                print("❌ Could not connect to database")
                print("\nPossible solutions:")
                print("1. Check if your IP is allowed in Supabase settings")
                print("2. Verify DATABASE_URL is correct in .env")
                print("3. Check Supabase project is running")
                raise
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_migration()
