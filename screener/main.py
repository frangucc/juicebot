"""
Main entry point for the stock screener service.

Usage:
    python -m screener.main [--threshold 0.05] [--replay]
"""

import argparse
import sys
from screener.scanner import PriceMovementScanner
from screener.alert_handler import AlertHandler


def main():
    """Main function to run the screener."""
    parser = argparse.ArgumentParser(description="Real-time stock screener")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.03,
        help="Percentage move threshold (default: 0.03 = 3%%)",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Replay from midnight UTC before going live",
    )
    parser.add_argument(
        "--today",
        type=str,
        default=None,
        help="Date to scan (YYYY-MM-DD format, default: today)",
    )

    args = parser.parse_args()

    # Create alert handler
    alert_handler = AlertHandler()

    # Create scanner with alert callback
    scanner = PriceMovementScanner(
        pct_threshold=args.threshold,
        today=args.today,
        on_alert=alert_handler.handle_alert,
    )

    try:
        # Run the scanner
        scanner.run_live(replay_from_start=args.replay)
    except KeyboardInterrupt:
        print("\n[STOP] Scanner stopped by user")
        stats = alert_handler.get_performance_stats()
        print(f"[STATS] Alerts generated: {stats['alerts_generated']}")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Scanner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
