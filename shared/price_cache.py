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
        price_data = {
            'symbol': symbol,
            'bid': bid,
            'ask': ask,
            'mid': mid,
            'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
        price_json = json.dumps(price_data)

        # Store in Redis list for recent history
        self.redis_client.rpush(self.cache_key, price_json)
        self.redis_client.ltrim(self.cache_key, -self.maxlen, -1)

        # ALSO store per-symbol for fast lookup (with 5 minute TTL)
        symbol_key = f'price:{symbol}'
        self.redis_client.setex(symbol_key, 300, price_json)  # 5 minute expiry

    def get_recent_prices(self, limit: int = 20) -> List[Dict]:
        """Get the most recent price updates."""
        # Get the last 'limit' items from the Redis list
        items = self.redis_client.lrange(self.cache_key, -limit, -1)
        return [json.loads(item) for item in items]

    def get_price(self, symbol: str) -> Dict:
        """Get the most recent price for a specific symbol."""
        # Check Redis hash first (per-symbol storage)
        symbol_key = f'price:{symbol}'
        data = self.redis_client.get(symbol_key)
        if data:
            return json.loads(data)

        # Fallback: search through recent prices list
        items = self.redis_client.lrange(self.cache_key, -self.maxlen, -1)
        for item in reversed(items):  # Most recent first
            price_data = json.loads(item)
            if price_data.get('symbol') == symbol:
                return price_data
        return None

    def clear(self):
        """Clear all cached prices."""
        self.redis_client.delete(self.cache_key)

# Global cache instance
price_cache = PriceCache(maxlen=100)
