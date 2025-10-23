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

    # Read the SQL file
    with open("sql/001_init_schema.sql", "r") as f:
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

            # Verify tables were created
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)

            tables = cursor.fetchall()
            print("\n📊 Database tables:")
            for table in tables:
                print(f"  ✅ {table[0]}")

            cursor.close()
            conn.close()

            print("\n" + "=" * 60)
            print("🎉 Database is ready!")
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
