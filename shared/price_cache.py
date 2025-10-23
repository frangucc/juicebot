"""Shared cache for recent price updates from the scanner using Redis."""
import json
from datetime import datetime, timezone
from typing import Dict, List
import redis

class PriceCache:
    """Redis-based cache for recent price updates (shared across processes)."""

    def __init__(self, maxlen: int = 100):
        self.maxlen = maxlen
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self.cache_key = 'price_updates'

    def add_price(self, symbol: str, bid: float, ask: float, mid: float):
        """Add a price update to the cache."""
        price_data = json.dumps({
            'symbol': symbol,
            'bid': bid,
            'ask': ask,
            'mid': mid,
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        })

        # Push to Redis list and trim to maxlen
        self.redis_client.rpush(self.cache_key, price_data)
        self.redis_client.ltrim(self.cache_key, -self.maxlen, -1)

    def get_recent_prices(self, limit: int = 20) -> List[Dict]:
        """Get the most recent price updates."""
        # Get the last 'limit' items from the Redis list
        items = self.redis_client.lrange(self.cache_key, -limit, -1)
        return [json.loads(item) for item in items]

    def clear(self):
        """Clear all cached prices."""
        self.redis_client.delete(self.cache_key)

# Global cache instance
price_cache = PriceCache(maxlen=100)
