"""
Alert handler for storing screener alerts in Supabase.
"""

from datetime import datetime
from typing import Dict, Any
from shared.database import supabase
import pytz


class AlertHandler:
    """Handles storage and processing of screener alerts."""

    def __init__(self):
        """Initialize alert handler."""
        self.alert_count = 0

    def handle_alert(self, alert_data: Dict[str, Any]) -> None:
        """
        Store alert in Supabase and trigger notifications.

        Args:
            alert_data: Dictionary containing alert information
        """
        try:
            # Prepare alert record
            alert_record = {
                "symbol": alert_data["symbol"],
                "alert_type": "gap_up" if alert_data["pct_move"] > 0 else "gap_down",
                "trigger_price": float(alert_data["current_price"]),
                "trigger_time": alert_data["timestamp"].isoformat(),
                "conditions": {
                    "pct_move": float(alert_data["pct_move"]),
                    "previous_close": float(alert_data["previous_close"]),
                    "threshold_exceeded": True,
                },
                "metadata": {
                    "volume": int(alert_data.get("volume", 0)),  # Trade volume
                    "side": alert_data.get("side", ""),  # Trade side (A=sell, B=buy)
                    "data_source": "trades",  # Mark as trades schema
                },
                "sent_to_users": [],  # Will be populated when SMS sent
                "active": True,
            }

            # Insert into Supabase
            response = supabase.table("screener_alerts").insert(alert_record).execute()

            if response.data:
                self.alert_count += 1
                alert_id = response.data[0]["id"]
                print(f"    ✓ Alert stored in database (ID: {alert_id[:8]}..., total: {self.alert_count})")

                # TODO: Trigger SMS notifications here
                # self._send_sms_notifications(alert_record, alert_id)

        except Exception as e:
            print(f"    ✗ Error storing alert: {e}")

    def _send_sms_notifications(self, alert_data: Dict[str, Any], alert_id: str) -> None:
        """
        Send SMS notifications to eligible users.
        (To be implemented in Phase 2)
        """
        pass

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for the current session."""
        return {
            "alerts_generated": self.alert_count,
            "timestamp": datetime.now(pytz.timezone("US/Eastern")).isoformat(),
        }
