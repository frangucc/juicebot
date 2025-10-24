"""
Real-time price broadcaster using Redis pub/sub.

This module broadcasts price updates to Redis channels so that:
- WebSocket clients can receive real-time updates
- Multiple consumers can subscribe without affecting the scanner
- No blocking operations in the main scanner loop
"""
import json
import redis
from typing import Optional
from datetime import datetime, timezone


class PriceBroadcaster:
    """Broadcasts price updates to Redis pub/sub for real-time distribution."""

    def __init__(self):
        """Initialize Redis connection for pub/sub."""
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        self.channel = 'price_updates'

    def broadcast_price(
        self,
        symbol: str,
        price: float,
        bid: float,
        ask: float,
        pct_from_yesterday: Optional[float] = None,
        timestamp: Optional[str] = None
    ) -> None:
        """
        Broadcast a price update to all subscribers.

        Args:
            symbol: Stock ticker
            price: Current mid price
            bid: Bid price
            ask: Ask price
            pct_from_yesterday: Percentage change from yesterday
            timestamp: ISO timestamp of the update
        """
        try:
            message = {
                'symbol': symbol,
                'price': price,
                'bid': bid,
                'ask': ask,
                'pct_from_yesterday': pct_from_yesterday,
                'timestamp': timestamp or datetime.now(timezone.utc).isoformat()
            }

            # Publish to Redis channel (non-blocking, fire-and-forget)
            self.redis_client.publish(
                self.channel,
                json.dumps(message)
            )
        except Exception as e:
            # Silently fail - don't let broadcasting errors affect the scanner
            pass


# Global broadcaster instance
price_broadcaster = PriceBroadcaster()
