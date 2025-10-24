"""
Monitor TRADES schema migration progress.

Run this in the background to track migration success.
Usage: nohup python -m tests.monitor_migration > migration_monitor.log 2>&1 &
"""

import psycopg2
from shared.config import settings
import time
from datetime import datetime, timedelta


def check_migration_status():
    """Check and print migration status."""
    try:
        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor()

        # Check latest bars
        cur.execute("""
            SELECT
                COUNT(*) as new_bars,
                COALESCE(SUM(volume), 0) as total_volume,
                MAX(timestamp) as latest_bar,
                COUNT(DISTINCT symbol) as unique_symbols
            FROM price_bars
            WHERE is_legacy = false
            AND timestamp > NOW() - INTERVAL '1 hour'
        """)

        result = cur.fetchone()
        new_bars, total_volume, latest_bar, unique_symbols = result

        # Check if we're getting volume
        cur.execute("""
            SELECT
                COUNT(*) as bars_with_volume
            FROM price_bars
            WHERE is_legacy = false
            AND volume > 0
            AND timestamp > NOW() - INTERVAL '1 hour'
        """)

        bars_with_volume = cur.fetchone()[0]

        # Check legacy count
        cur.execute("""
            SELECT COUNT(*)
            FROM price_bars
            WHERE is_legacy = true
        """)

        legacy_count = cur.fetchone()[0]

        # Print status
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'=' * 80}")
        print(f"[{now}] TRADES Migration Status")
        print(f"{'=' * 80}")
        print(f"\n📊 New Bars (last hour):")
        print(f"   Total bars:           {new_bars:,}")
        print(f"   Bars with volume:     {bars_with_volume:,} ({bars_with_volume/new_bars*100 if new_bars else 0:.1f}%)")
        print(f"   Unique symbols:       {unique_symbols}")
        print(f"   Total volume:         {total_volume:,} shares")
        print(f"   Latest bar:           {latest_bar}")

        print(f"\n📦 Legacy Data:")
        print(f"   Legacy bars (MBP-1):  {legacy_count:,}")

        # Health check
        print(f"\n🔍 Health Check:")
        if new_bars == 0:
            print("   ❌ WARNING: No new bars in last hour!")
        elif bars_with_volume == 0:
            print("   ❌ WARNING: No volume data! TRADES schema may not be working.")
        elif bars_with_volume / new_bars < 0.5:
            print(f"   ⚠️  WARNING: Only {bars_with_volume/new_bars*100:.1f}% of bars have volume")
        else:
            print(f"   ✅ HEALTHY: {bars_with_volume} bars with volume")

        if latest_bar:
            time_since_last = datetime.now(latest_bar.tzinfo) - latest_bar
            if time_since_last > timedelta(minutes=10):
                print(f"   ⚠️  WARNING: Last bar was {time_since_last.seconds//60} minutes ago")
            else:
                print(f"   ✅ Recent data: Last bar {time_since_last.seconds} seconds ago")

        cur.close()
        conn.close()

        return new_bars, bars_with_volume, total_volume

    except Exception as e:
        print(f"\n❌ Error checking migration status: {e}")
        return 0, 0, 0


def main():
    """Main monitoring loop."""
    print("\n🚀 Starting TRADES Migration Monitor")
    print("📊 Checking every 5 minutes...")
    print("⏹️  Press Ctrl+C to stop\n")

    check_interval = 300  # 5 minutes
    iteration = 0

    try:
        while True:
            iteration += 1
            print(f"\n{'#' * 80}")
            print(f"Check #{iteration}")
            print(f"{'#' * 80}")

            check_migration_status()

            print(f"\n⏰ Next check in {check_interval} seconds...")
            time.sleep(check_interval)

    except KeyboardInterrupt:
        print("\n\n👋 Migration monitor stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")


if __name__ == "__main__":
    main()
