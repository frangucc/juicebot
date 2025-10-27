"""
Real-time stock scanner for pre-market movers and gap-ups.
Based on Databento's real-time screener tutorial.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional
import databento as db
import pandas as pd
import pytz
from shared.config import settings
from shared.price_cache import price_cache
from shared.database import supabase
from shared.price_broadcaster import PriceBroadcaster
from screener.bar_aggregator import BarAggregator
import random
import time
import os


class PriceMovementScanner:
    """Scanner for detecting large price movements in all US equities."""

    # Constants
    PX_SCALE: float = 1e-9
    PX_NULL: int = 2**63 - 1

    def __init__(
        self,
        pct_threshold: float = None,
        today: str = None,
        on_alert: Optional[Callable] = None
    ) -> None:
        """
        Initialize scanner with configurable threshold and date.

        Args:
            pct_threshold: Percentage move threshold (default 0.03 = 3%)
            today: Date string in YYYY-MM-DD format (default: today)
            on_alert: Callback function when alert is triggered
        """
        self.pct_threshold = pct_threshold or settings.screener_pct_threshold
        self.today = today or pd.Timestamp.now("US/Eastern").strftime("%Y-%m-%d")
        self.today_midnight_ns = int(pd.Timestamp(self.today).timestamp() * 1e9)
        self.on_alert = on_alert

        # State dictionaries
        self.symbol_directory: Dict[int, str] = {}
        self.last_day_lookup: Dict[str, float] = {}
        self.last_alerted_price: Dict[str, float] = {}  # Track last price that triggered alert
        self.last_alert_time: Dict[str, float] = {}  # Track timestamp of last alert per symbol
        self.is_signal_lit: Dict[str, bool] = {}

        # Symbol state tracking for database updates
        self.symbol_state_cache: Dict[str, Dict] = {}  # In-memory cache to batch DB updates
        self.today_open_prices: Dict[str, float] = {}  # Track first price of day as "open"
        self.snapshot_15min: Dict[str, tuple] = {}  # (price, timestamp)
        self.snapshot_5min: Dict[str, tuple] = {}  # (price, timestamp)
        self.hod_tracker: Dict[str, tuple] = {}  # (price, pct, timestamp)
        self.lod_tracker: Dict[str, tuple] = {}  # (price, pct, timestamp)

        # Batch update counters
        self._state_update_counter = 0
        self._last_batch_update = time.time()

        # Priority-based sampling system
        self._symbol_counters: Dict[str, int] = {}  # Per-symbol message counters
        self._symbol_priorities: Dict[str, int] = {}  # Cached priority tier per symbol
        self._symbol_last_update: Dict[str, float] = {}  # When each symbol was last DB updated

        # OHLCV fallback for stale symbols
        self._last_ohlcv_fetch = time.time()
        self._ohlcv_fetch_interval = 300  # Fetch OHLCV every 5 minutes
        self._symbol_last_seen: Dict[str, float] = {}  # Track when we last saw each symbol

        # Price broadcaster for WebSocket real-time updates
        self.price_broadcaster = PriceBroadcaster()

        # Bar aggregator for 1-minute OHLCV bars (optional)
        enable_bars = os.getenv('ENABLE_PRICE_BARS', 'false').lower() == 'true'
        self.bar_aggregator = BarAggregator(enable_db_writes=enable_bars) if enable_bars else None
        if self.bar_aggregator:
            print(f"[Scanner] Bar aggregator ENABLED (db_writes={enable_bars})")

        # Initialize with yesterday's closing prices
        self._load_previous_close_prices()

    def _load_previous_close_prices(self) -> None:
        """Load previous trading day's closing prices for all symbols."""
        print(f"[{self._now()}] Loading previous trading day's closing prices...")

        client = db.Historical(key=settings.databento_api_key)

        # Find last trading day (skip weekends)
        last_trading_day = pd.Timestamp(self.today) - timedelta(days=1)
        while last_trading_day.weekday() >= 5:  # 5=Saturday, 6=Sunday
            last_trading_day -= timedelta(days=1)
        last_trading_day_date = last_trading_day.date()

        # Databento requires end > start, so use next day as end
        # (end is exclusive in Databento API)
        end_date = (last_trading_day + timedelta(days=1)).date()

        print(f"[{self._now()}] Loading closes from {last_trading_day_date} (last trading day)")

        # Get last trading day's closing prices from Databento
        data = client.timeseries.get_range(
            dataset="EQUS.SUMMARY",
            schema="ohlcv-1d",
            symbols="ALL_SYMBOLS",
            start=last_trading_day_date,
            end=end_date,
        )

        # Request symbology mapping
        symbology_json = data.request_symbology(client)
        data.insert_symbology_json(symbology_json, clear_existing=True)

        df = data.to_df()

        # Store closing prices
        self.last_day_lookup = dict(zip(df["symbol"], df["close"]))
        self.last_alerted_price = dict(zip(df["symbol"], df["close"]))  # Initialize with close prices
        self.is_signal_lit = {symbol: False for symbol in self.last_day_lookup}

        print(f"[{self._now()}] Loaded {len(self.last_day_lookup)} symbols with previous closing prices")

    def _calculate_priority_tier(self, pct_move: float, threshold: float) -> int:
        """
        Calculate priority tier based on how far above threshold the move is.

        Args:
            pct_move: Current percentage move from yesterday's close
            threshold: User's configured threshold percentage

        Returns:
            Priority tier: 1 (highest) to 4 (lowest)
            - Tier 1: 20x threshold or more (extreme movers)
            - Tier 2: 10x to 20x threshold (strong movers)
            - Tier 3: 5x to 10x threshold (moderate movers)
            - Tier 4: threshold to 5x threshold (normal movers)
        """
        abs_pct = abs(pct_move)

        if abs_pct >= threshold * 20:
            return 1
        elif abs_pct >= threshold * 10:
            return 2
        elif abs_pct >= threshold * 5:
            return 3
        else:
            return 4

    def scan(self, event: Any) -> None:
        """
        Scan for large price movements in market data events.

        This callback processes each market data event from Databento.
        """
        # Track message counts
        if not hasattr(self, '_debug_count'):
            self._debug_count = 0
            self._debug_last_print = 0
            self._message_types = {}

        self._debug_count += 1

        # Track message types
        msg_type = type(event).__name__
        self._message_types[msg_type] = self._message_types.get(msg_type, 0) + 1

        # Debug first SymbolMappingMsg to see its actual type
        if msg_type == 'SymbolMappingMsg' and not hasattr(self, '_checked_symbol_type'):
            print(f"[DEBUG] SymbolMappingMsg detected! Type: {type(event)}, isinstance check: {isinstance(event, db.SymbolMappingMsg)}")
            print(f"[DEBUG] Event attributes: {dir(event)}")
            self._checked_symbol_type = True

        # Print debug info every 1000 messages
        if self._debug_count - self._debug_last_print >= 1000:
            print(f"[DEBUG] Processed {self._debug_count} messages, {len(self.symbol_directory)} symbols mapped")
            print(f"[DEBUG] Message types: {self._message_types}")

            # Print priority distribution
            if hasattr(self, '_symbol_priorities') and len(self._symbol_priorities) > 0:
                priority_counts = {1: 0, 2: 0, 3: 0, 4: 0}
                for p in self._symbol_priorities.values():
                    priority_counts[p] = priority_counts.get(p, 0) + 1
                print(f"[DEBUG] Priority distribution: P1(20%+)={priority_counts[1]}, P2(10-20%)={priority_counts[2]}, P3(5-10%)={priority_counts[3]}, P4(1-5%)={priority_counts[4]}")

            self._debug_last_print = self._debug_count

        # Handle symbol mapping messages
        if isinstance(event, db.SymbolMappingMsg):
            symbol = event.stype_out_symbol
            inst_id = event.instrument_id  # NOT event.hd.instrument_id!

            # Debug: print first mapping to see what we're getting
            if not hasattr(self, '_first_map_printed'):
                print(f"[DEBUG] First mapping: symbol='{symbol}', inst_id={inst_id}, type={type(symbol)}")
                self._first_map_printed = True

            # Store the mapping
            self.symbol_directory[inst_id] = symbol

            # Print mapping milestones
            dict_len = len(self.symbol_directory)
            if dict_len <= 5:
                print(f"[DEBUG] Mapped {symbol} to ID {inst_id}, total={dict_len}")
            elif dict_len == 100:
                print(f"[DEBUG] Reached 100 symbol mappings")
            elif dict_len == 1000:
                print(f"[DEBUG] Reached 1000 symbol mappings")
            elif dict_len == 11938:
                print(f"[DEBUG] All 11938 symbols mapped!")
            return

        # Only process Trade messages (actual executions with volume)
        if not isinstance(event, db.TradeMsg):
            return

        # Get symbol from instrument ID
        symbol = self.symbol_directory.get(event.instrument_id)
        if not symbol or symbol not in self.last_day_lookup:
            return

        # Extract trade price and volume
        trade_price_raw = event.price
        trade_volume = event.size

        # Debug WGRX specifically
        is_wgrx = symbol == "WGRX"
        if is_wgrx and not hasattr(self, '_wgrx_debug_count'):
            self._wgrx_debug_count = 0

        if is_wgrx:
            self._wgrx_debug_count += 1

        # Skip if price is undefined
        if trade_price_raw == self.PX_NULL:
            if is_wgrx and self._wgrx_debug_count % 100 == 0:
                print(f"[DEBUG WGRX] Skipped - undefined price")
            return

        # Convert price from fixed-precision format
        price = trade_price_raw * self.PX_SCALE

        # Skip if price is invalid
        if price <= 0:
            if is_wgrx and self._wgrx_debug_count % 100 == 0:
                print(f"[DEBUG WGRX] Skipped - invalid price (${price:.4f})")
            return

        if is_wgrx and self._wgrx_debug_count % 100 == 0:
            print(f"[DEBUG WGRX] Processing trade! price=${price:.4f}, volume={trade_volume}")

        last_close = self.last_day_lookup[symbol]
        last_alerted = self.last_alerted_price.get(symbol, last_close)

        # Track when we last saw this symbol (for stale detection)
        self._symbol_last_seen[symbol] = time.time()

        # Get timestamp
        try:
            ts = pd.Timestamp(event.hd.ts_event, unit='ns').tz_localize('UTC').tz_convert('US/Eastern')
        except Exception:
            ts = pd.Timestamp.now('US/Eastern')

        # Calculate percentage from yesterday (needed for both bar aggregator and broadcaster)
        pct_from_yesterday = ((price - last_close) / last_close) * 100 if last_close else 0

        # Add tick to bar aggregator for 1-minute OHLCV bars (BEFORE filters to capture ALL symbols)
        if self.bar_aggregator:
            self.bar_aggregator.add_tick(
                symbol=symbol,
                price=price,
                timestamp=ts,
                volume=trade_volume  # ✅ Real trade volume from TRADES schema!
            )

        # Broadcast price update to WebSocket clients (real-time UI updates)
        self.price_broadcaster.broadcast_price(
            symbol=symbol,
            price=price,
            bid=price,  # No bid/ask in trades, use trade price
            ask=price,  # No bid/ask in trades, use trade price
            pct_from_yesterday=pct_from_yesterday,
            timestamp=ts.isoformat()
        )

        # Periodically fetch OHLCV fallback for stale symbols
        self._fetch_stale_symbol_prices()

        # Update symbol state tracking with TIME-BASED priority sampling
        # Calculate priority tier based on % move from yesterday
        priority = self._calculate_priority_tier(pct_from_yesterday, self.pct_threshold)

        # TIME-BASED update intervals (seconds) instead of message-count based
        # This ensures symbols update even if they stop trading actively
        PRIORITY_UPDATE_INTERVALS = {
            1: 5,    # Update every 5 seconds (extreme movers, 20%+)
            2: 30,   # Update every 30 seconds (strong movers, 10-20%)
            3: 60,   # Update every 60 seconds (moderate movers, 5-10%)
            4: 120,  # Update every 2 minutes (normal movers, threshold to 5x)
        }

        update_interval = PRIORITY_UPDATE_INTERVALS.get(priority, 120)
        current_time = time.time()

        # Initialize last update time if needed
        if symbol not in self._symbol_last_update:
            self._symbol_last_update[symbol] = 0

        # Check if enough time has passed since last update
        time_since_last_update = current_time - self._symbol_last_update[symbol]
        should_update = time_since_last_update >= update_interval

        if should_update:
            self._update_symbol_state(
                symbol=symbol,
                current_price=price,
                bid=price,  # Trades don't have bid/ask, use price
                ask=price,  # Trades don't have bid/ask, use price
                spread_pct=0.0,  # No spread in trades
                timestamp=ts
            )
            # Update the last update timestamp
            self._symbol_last_update[symbol] = current_time
            # Store priority for debugging
            self._symbol_priorities[symbol] = priority

            # Debug Priority 1 & 2 symbols
            if priority <= 2:
                print(f"[DEBUG P{priority}] {symbol}: ${price:.4f}, pct={pct_from_yesterday:.2f}%, last_update={time_since_last_update:.1f}s ago")

        # Ensure priority bars every minute (for leaderboard stocks with P1/P2)
        if self.bar_aggregator and priority <= 2:
            # Check if we need to update priority symbols list (every 30 seconds)
            if not hasattr(self, '_last_priority_update'):
                self._last_priority_update = time.time()
                self._priority_symbols_set = set()

            # Collect priority symbols
            self._priority_symbols_set.add(symbol)

            # Update bar aggregator every 30 seconds with latest priority list
            if current_time - self._last_priority_update >= 30:
                self.bar_aggregator.update_priority_symbols(self._priority_symbols_set)
                self._last_priority_update = current_time

        # GLOBAL heartbeat check - runs on EVERY message to ensure continuity
        # This is independent of priority and ensures bars are forced every minute
        if self.bar_aggregator:
            if not hasattr(self, '_last_priority_bar_check'):
                self._last_priority_bar_check = time.time()

            if current_time - self._last_priority_bar_check >= 60:
                self.bar_aggregator.ensure_priority_bars(ts)
                self._last_priority_bar_check = current_time
                print(f"[BarAggregator] Forced priority bars at {ts}, tracking {len(self._priority_symbols_set if hasattr(self, '_priority_symbols_set') else [])} symbols")

        # Cache every 10th price update for display (avoid overhead)
        if not hasattr(self, '_price_sample_counter'):
            self._price_sample_counter = 0
        self._price_sample_counter += 1
        if self._price_sample_counter % 10 == 0:
            price_cache.add_price(
                symbol=symbol,
                bid=price,  # Use trade price
                ask=price,  # Use trade price
                mid=price   # Use trade price
            )

        # Calculate percentage move from LAST ALERTED PRICE (not yesterday's close!)
        abs_r = abs(price - last_alerted) / last_alerted

        # 1% threshold for meaningful price movements
        threshold = 0.01  # 1%

        # Check if threshold exceeded
        if abs_r > threshold:
            # Cooldown: Don't alert same symbol within 30 seconds
            current_time = time.time()
            last_alert = self.last_alert_time.get(symbol, 0)

            if current_time - last_alert >= 30:  # 30 second cooldown
                self._trigger_alert(event, symbol, price, last_alerted, abs_r)
                self.last_alert_time[symbol] = current_time

    def _update_symbol_state(
        self,
        symbol: str,
        current_price: float,
        bid: float,
        ask: float,
        spread_pct: float,
        timestamp: pd.Timestamp
    ) -> None:
        """Update symbol state tracking for database persistence."""
        yesterday_close = self.last_day_lookup.get(symbol)
        if not yesterday_close:
            return

        # Track today's open (first price we see for this symbol)
        if symbol not in self.today_open_prices:
            self.today_open_prices[symbol] = current_price

        today_open = self.today_open_prices[symbol]

        # Calculate % moves from different baselines
        pct_from_yesterday = ((current_price - yesterday_close) / yesterday_close) * 100 if yesterday_close else None
        pct_from_open = ((current_price - today_open) / today_open) * 100 if today_open else None

        # Update 15min and 5min snapshots (rolling windows)
        current_ts = time.time()

        # 15min snapshot: update if 15min elapsed since last snapshot
        if symbol not in self.snapshot_15min or (current_ts - self.snapshot_15min[symbol][1]) >= 900:  # 900s = 15min
            self.snapshot_15min[symbol] = (current_price, current_ts)

        # 5min snapshot: update if 5min elapsed since last snapshot
        if symbol not in self.snapshot_5min or (current_ts - self.snapshot_5min[symbol][1]) >= 300:  # 300s = 5min
            self.snapshot_5min[symbol] = (current_price, current_ts)

        # Calculate % from snapshots
        price_15min_ago, _ = self.snapshot_15min.get(symbol, (current_price, current_ts))
        price_5min_ago, _ = self.snapshot_5min.get(symbol, (current_price, current_ts))

        pct_from_15min = ((current_price - price_15min_ago) / price_15min_ago) * 100 if price_15min_ago else None
        pct_from_5min = ((current_price - price_5min_ago) / price_5min_ago) * 100 if price_5min_ago else None

        # Update HOD (High of Day) tracking
        if symbol not in self.hod_tracker or pct_from_yesterday > self.hod_tracker[symbol][1]:
            self.hod_tracker[symbol] = (current_price, pct_from_yesterday, timestamp)

        # Update LOD (Low of Day) tracking
        if symbol not in self.lod_tracker or pct_from_yesterday < self.lod_tracker[symbol][1]:
            self.lod_tracker[symbol] = (current_price, pct_from_yesterday, timestamp)

        hod_price, hod_pct, hod_ts = self.hod_tracker.get(symbol, (None, None, None))
        lod_price, lod_pct, lod_ts = self.lod_tracker.get(symbol, (None, None, None))

        # Store in cache for batch update
        self.symbol_state_cache[symbol] = {
            "symbol": symbol,
            "current_price": current_price,
            "current_bid": bid,
            "current_ask": ask,
            "price_timestamp": timestamp.isoformat(),
            "yesterday_close": yesterday_close,
            "today_open": today_open,
            "pct_from_yesterday": pct_from_yesterday,
            "pct_from_open": pct_from_open,
            "pct_from_15min": pct_from_15min,
            "pct_from_5min": pct_from_5min,
            "hod_price": hod_price,
            "hod_pct": hod_pct,
            "hod_timestamp": hod_ts.isoformat() if hod_ts else None,
            "lod_price": lod_price,
            "lod_pct": lod_pct,
            "lod_timestamp": lod_ts.isoformat() if lod_ts else None,
            "spread_pct": spread_pct * 100,  # Store as percentage
            "last_updated": timestamp.isoformat(),
        }

        self._state_update_counter += 1

        # Aggressive flush for real-time updates:
        # - Flush every 10 symbol updates (down from 100)
        # - OR every 2 seconds (down from 5)
        # This ensures leaderboard symbols update much faster
        if self._state_update_counter >= 10 or (current_ts - self._last_batch_update) >= 2:
            self._flush_state_to_db()
            self._last_batch_update = current_ts

    def _flush_state_to_db(self) -> None:
        """Flush cached symbol state to database in batch."""
        if not self.symbol_state_cache:
            return

        try:
            # Use upsert to insert or update
            batch_data = list(self.symbol_state_cache.values())
            supabase.table("symbol_state").upsert(batch_data).execute()

            # Debug log
            if not hasattr(self, '_db_flush_count'):
                self._db_flush_count = 0
            self._db_flush_count += 1
            if self._db_flush_count % 10 == 0:
                print(f"[{self._now()}] Flushed {len(batch_data)} symbols to symbol_state table (batch #{self._db_flush_count})")

            # Clear cache after successful update
            self.symbol_state_cache.clear()
            self._state_update_counter = 0

        except Exception as e:
            print(f"[{self._now()}] ERROR: Failed to flush symbol state to DB: {e}")
            # Don't clear cache on error - will retry on next flush

    def _fetch_stale_symbol_prices(self) -> None:
        """
        Fetch latest OHLCV bars for symbols that haven't updated via live stream.
        This ensures we have accurate prices even when symbols stop trading.
        """
        current_time = time.time()

        # Only run every 5 minutes
        if current_time - self._last_ohlcv_fetch < self._ohlcv_fetch_interval:
            return

        self._last_ohlcv_fetch = current_time

        # Find symbols that haven't been seen in last 10 minutes
        stale_threshold = 600  # 10 minutes
        stale_symbols = []

        for symbol, last_seen in list(self._symbol_last_seen.items())[:100]:  # Limit to 100 symbols per batch
            if current_time - last_seen > stale_threshold:
                stale_symbols.append(symbol)

        if not stale_symbols:
            return

        print(f"[{self._now()}] Fetching OHLCV fallback prices for {len(stale_symbols)} stale symbols...")

        try:
            client = db.Historical(key=settings.databento_api_key)

            # Fetch last 30 minutes of 1-min bars
            end_time = pd.Timestamp.now("UTC")
            start_time = end_time - timedelta(minutes=30)

            data = client.timeseries.get_range(
                dataset="EQUS.MINI",
                schema="ohlcv-1m",
                symbols=stale_symbols[:50],  # Batch of 50 at a time to avoid rate limits
                start=start_time.isoformat(),
                end=end_time.isoformat(),
            )

            df = data.to_df()

            if len(df) > 0:
                # Group by symbol and get last bar for each
                for symbol in df.index.get_level_values('symbol').unique():
                    symbol_data = df.xs(symbol, level='symbol')
                    if len(symbol_data) > 0:
                        last_bar = symbol_data.iloc[-1]

                        # Update symbol state with OHLCV close price
                        ts = pd.Timestamp(last_bar.name, tz='UTC').tz_convert('US/Eastern')

                        # Force update with fallback price
                        self._update_symbol_state(
                            symbol=symbol,
                            current_price=last_bar['close'],
                            bid=last_bar['close'],  # Use close as bid/ask approximation
                            ask=last_bar['close'],
                            spread_pct=0.0,  # No spread data from OHLCV
                            timestamp=ts
                        )

                print(f"[{self._now()}] ✓ Updated {len(df.index.get_level_values('symbol').unique())} symbols from OHLCV fallback")

        except Exception as e:
            print(f"[{self._now()}] WARNING: OHLCV fallback fetch failed: {e}")

    def _trigger_alert(
        self,
        event: db.TradeMsg,  # ✅ Changed from MBP1Msg to TradeMsg
        symbol: str,
        current_price: float,
        last_reference_price: float,
        pct_move: float
    ) -> None:
        """Trigger an alert when threshold is exceeded."""
        try:
            ts = pd.Timestamp(event.hd.ts_event, unit='ns').tz_localize('UTC').tz_convert('US/Eastern')
        except Exception as e:
            ts = pd.Timestamp.now('US/Eastern')

        alert_data = {
            "symbol": symbol,
            "current_price": current_price,
            "previous_close": last_reference_price,
            "pct_move": pct_move * 100,
            "timestamp": ts,
            "volume": event.size,  # ✅ Trade volume instead of bid/ask
            "side": event.side,    # ✅ Trade side (buy/sell)
        }

        # Print to console with flush to ensure it appears immediately
        alert_msg = f"[{ts.isoformat()}] {symbol} moved by {pct_move * 100:.2f}% (current: {current_price:.4f}, last: {last_reference_price:.4f}, vol: {event.size})"
        print(alert_msg, flush=True)

        # Update the last alerted price to current price so we can detect next move
        self.last_alerted_price[symbol] = current_price

        # CRITICAL: Force an immediate symbol_state update when alert triggers
        # This ensures leaderboards stay in sync with recent alerts
        self._update_symbol_state(
            symbol=symbol,
            current_price=current_price,
            bid=current_price,  # Use trade price
            ask=current_price,  # Use trade price
            spread_pct=0.0,     # No spread in trades
            timestamp=ts
        )

        # Call callback if provided
        if self.on_alert:
            self.on_alert(alert_data)

    def run_live(self, replay_from_start: bool = False) -> None:
        """
        Start live scanning of market data.

        Args:
            replay_from_start: If True, replay from midnight before going live
        """
        print(f"[{self._now()}] Starting live scanner...")
        print(f"[{self._now()}] Threshold: {self.pct_threshold * 100:.1f}%")
        print(f"[{self._now()}] Dataset: {settings.screener_dataset}")
        print(f"[{self._now()}] Watching {len(self.last_day_lookup)} symbols")

        live = db.Live(key=settings.databento_api_key)

        # Subscribe to all symbols with MBP-1 (top of book)
        live.subscribe(
            dataset=settings.screener_dataset,
            schema=settings.screener_schema,
            symbols="ALL_SYMBOLS",
            stype_in="raw_symbol",  # Explicitly request symbol mappings
            start=0 if replay_from_start else None,  # 0 = replay from midnight UTC
        )

        # Register callback
        live.add_callback(self.scan)

        print(f"[{self._now()}] Scanner is running. Press Ctrl+C to stop.")

        # Start processing
        live.start()
        live.block_for_close()

    @staticmethod
    def _now() -> str:
        """Get current time in Eastern timezone."""
        return datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d %H:%M:%S")
