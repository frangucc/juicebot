"""
OHLCV Bar Aggregator for 1-minute price bars.

This module aggregates tick-level price data into 1-minute OHLCV (Open, High, Low, Close, Volume) bars.
Bars are flushed to the database every minute to enable:
- Accurate baseline calculations (% YEST, % OPEN, % PRE)
- Foundation for algorithmic trading systems
- Ability to reconstruct complete 1-minute charts
"""

from datetime import datetime
from typing import Dict, Optional
import pandas as pd
import psycopg2
from shared.config import settings
import time


class Bar:
    """Represents a single 1-minute OHLCV bar."""

    def __init__(
        self,
        symbol: str,
        timestamp: pd.Timestamp,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: int = 0,
        trade_count: int = 1
    ):
        self.symbol = symbol
        self.timestamp = timestamp
        self.open = open_price
        self.high = high_price
        self.low = low_price
        self.close = close_price
        self.volume = volume
        self.trade_count = trade_count

    def update_with_tick(self, price: float, volume: int = 0) -> None:
        """Update bar with new tick data."""
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume
        self.trade_count += 1

    def to_dict(self) -> dict:
        """Convert bar to dictionary for database insertion."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "trade_count": self.trade_count
        }


class BarAggregator:
    """Aggregates tick data into 1-minute OHLCV bars."""

    def __init__(self, enable_db_writes: bool = False):
        """
        Initialize bar aggregator.

        Args:
            enable_db_writes: Whether to write bars to database (default: False for testing)
        """
        self.current_bars: Dict[str, Bar] = {}  # symbol -> current bar
        self.completed_bars: Dict[str, Bar] = {}  # symbol -> completed bar (for batch flush)
        self.enable_db_writes = enable_db_writes
        self._last_flush_time = time.time()
        self._flush_interval = 60  # Flush every 60 seconds
        self._bars_created_count = 0
        self._bars_flushed_count = 0

        # Database connection (only if writes enabled)
        self._db_conn = None
        if self.enable_db_writes:
            try:
                self._db_conn = psycopg2.connect(settings.database_url)
                print(f"[BarAggregator] Connected to database for price_bars writes")
            except Exception as e:
                print(f"[BarAggregator] ERROR: Failed to connect to database: {e}")
                self.enable_db_writes = False

    def add_tick(self, symbol: str, price: float, timestamp: pd.Timestamp, volume: int = 0) -> None:
        """
        Add a tick to the aggregator.

        Args:
            symbol: Stock ticker
            price: Trade price (mid-price or trade price)
            timestamp: Timestamp of the tick
            volume: Volume of the trade (0 if not available)
        """
        # Round timestamp to minute boundary (floor to start of minute)
        bar_timestamp = timestamp.floor('1min')

        # Check if we have a current bar for this symbol
        if symbol in self.current_bars:
            current_bar = self.current_bars[symbol]

            # Check if tick belongs to a new minute
            if bar_timestamp > current_bar.timestamp:
                # Complete current bar and store for flushing
                self.completed_bars[symbol] = current_bar
                self._bars_created_count += 1

                # Start new bar
                self.current_bars[symbol] = Bar(
                    symbol=symbol,
                    timestamp=bar_timestamp,
                    open_price=price,
                    high_price=price,
                    low_price=price,
                    close_price=price,
                    volume=volume,
                    trade_count=1
                )
            else:
                # Update current bar with new tick
                current_bar.update_with_tick(price, volume)
        else:
            # First tick for this symbol - start new bar
            self.current_bars[symbol] = Bar(
                symbol=symbol,
                timestamp=bar_timestamp,
                open_price=price,
                high_price=price,
                low_price=price,
                close_price=price,
                volume=volume,
                trade_count=1
            )

        # Periodically flush completed bars to database
        current_time = time.time()
        if current_time - self._last_flush_time >= self._flush_interval:
            self._flush_bars()
            self._last_flush_time = current_time

    def _flush_bars(self) -> None:
        """Flush completed bars to database in batch."""
        if not self.completed_bars:
            return

        # Log flush attempt
        bars_to_flush = len(self.completed_bars)
        print(f"[BarAggregator] Flushing {bars_to_flush} completed bars...")

        if not self.enable_db_writes:
            print(f"[BarAggregator] DB writes DISABLED - would have written {bars_to_flush} bars")
            print(f"[BarAggregator] Stats: {self._bars_created_count} bars created, {self._bars_flushed_count} bars flushed")
            # Show sample of what would be written
            if self.completed_bars:
                sample_symbol = list(self.completed_bars.keys())[0]
                sample_bar = self.completed_bars[sample_symbol]
                print(f"[BarAggregator] Sample bar: {sample_symbol} @ {sample_bar.timestamp} O={sample_bar.open:.4f} H={sample_bar.high:.4f} L={sample_bar.low:.4f} C={sample_bar.close:.4f} trades={sample_bar.trade_count}")
            self.completed_bars.clear()
            return

        # Build batch insert
        try:
            cursor = self._db_conn.cursor()

            # Prepare batch data
            batch_data = []
            for bar in self.completed_bars.values():
                batch_data.append((
                    bar.symbol,
                    bar.timestamp,
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.volume,
                    bar.trade_count
                ))

            # Execute batch insert with ON CONFLICT to handle duplicates
            insert_query = """
                INSERT INTO price_bars (symbol, timestamp, open, high, low, close, volume, trade_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, timestamp) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    trade_count = EXCLUDED.trade_count
            """

            cursor.executemany(insert_query, batch_data)
            self._db_conn.commit()
            cursor.close()

            self._bars_flushed_count += len(batch_data)
            print(f"[BarAggregator] Successfully flushed {len(batch_data)} bars to database")
            print(f"[BarAggregator] Total stats: {self._bars_created_count} bars created, {self._bars_flushed_count} bars flushed")

            # Clear completed bars
            self.completed_bars.clear()

        except Exception as e:
            print(f"[BarAggregator] ERROR flushing bars to database: {e}")
            # Don't clear completed_bars - try again next flush

    def get_stats(self) -> dict:
        """Get aggregator statistics."""
        return {
            "bars_created": self._bars_created_count,
            "bars_flushed": self._bars_flushed_count,
            "current_bars_count": len(self.current_bars),
            "pending_flush_count": len(self.completed_bars),
            "db_writes_enabled": self.enable_db_writes
        }

    def force_flush(self) -> None:
        """Force flush all completed bars immediately."""
        self._flush_bars()

    def close(self) -> None:
        """Close database connection and flush any remaining bars."""
        if self.completed_bars:
            self._flush_bars()

        if self._db_conn:
            self._db_conn.close()
            print(f"[BarAggregator] Closed database connection")
