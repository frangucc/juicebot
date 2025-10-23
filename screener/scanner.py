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
import random
import time


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

        # OHLCV fallback for stale symbols
        self._last_ohlcv_fetch = time.time()
        self._ohlcv_fetch_interval = 300  # Fetch OHLCV every 5 minutes
        self._symbol_last_seen: Dict[str, float] = {}  # Track when we last saw each symbol

        # Initialize with yesterday's closing prices
        self._load_previous_close_prices()

    def _load_previous_close_prices(self) -> None:
        """Load yesterday's closing prices for all symbols."""
        print(f"[{self._now()}] Loading previous day's closing prices...")

        client = db.Historical(key=settings.databento_api_key)

        now = pd.Timestamp(self.today).date()
        yesterday = (pd.Timestamp(self.today) - timedelta(days=1)).date()

        # Get yesterday's closing prices from Databento
        data = client.timeseries.get_range(
            dataset="EQUS.SUMMARY",
            schema="ohlcv-1d",
            symbols="ALL_SYMBOLS",
            start=yesterday,
            end=now,
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

        # Only process MBP-1 (top of book) messages
        if not isinstance(event, db.MBP1Msg):
            return

        # Get symbol from instrument ID
        symbol = self.symbol_directory.get(event.instrument_id)
        if not symbol or symbol not in self.last_day_lookup:
            return

        # Extract bid and ask prices
        bid = event.levels[0].bid_px
        ask = event.levels[0].ask_px

        # Debug WGRX specifically
        is_wgrx = symbol == "WGRX"
        if is_wgrx and not hasattr(self, '_wgrx_debug_count'):
            self._wgrx_debug_count = 0

        if is_wgrx:
            self._wgrx_debug_count += 1

        # Skip if one side of book is empty
        if bid == self.PX_NULL or ask == self.PX_NULL:
            if is_wgrx and self._wgrx_debug_count % 100 == 0:
                print(f"[DEBUG WGRX] Skipped - empty book (bid={bid}, ask={ask})")
            return

        # Calculate mid price and spread
        bid_price = bid * self.PX_SCALE
        ask_price = ask * self.PX_SCALE
        mid = (bid_price + ask_price) * 0.5
        spread_pct = (ask_price - bid_price) / mid if mid > 0 else 0

        # Skip illiquid stocks with wide spreads (likely erratic pricing)
        # If spread > 2%, skip - these create false alerts
        if spread_pct > 0.02:
            if is_wgrx and self._wgrx_debug_count % 100 == 0:
                print(f"[DEBUG WGRX] Skipped - wide spread ({spread_pct*100:.2f}%)")
            return

        if is_wgrx and self._wgrx_debug_count % 100 == 0:
            print(f"[DEBUG WGRX] Processing! bid=${bid_price:.4f}, ask=${ask_price:.4f}, spread={spread_pct*100:.2f}%")

        last_close = self.last_day_lookup[symbol]
        last_alerted = self.last_alerted_price.get(symbol, last_close)

        # Track when we last saw this symbol (for stale detection)
        self._symbol_last_seen[symbol] = time.time()

        # Get timestamp
        try:
            ts = pd.Timestamp(event.hd.ts_event, unit='ns').tz_localize('UTC').tz_convert('US/Eastern')
        except Exception:
            ts = pd.Timestamp.now('US/Eastern')

        # Periodically fetch OHLCV fallback for stale symbols
        self._fetch_stale_symbol_prices()

        # Update symbol state tracking with priority-based sampling
        # Calculate priority tier based on % move from yesterday
        pct_from_yesterday = ((mid - last_close) / last_close) * 100 if last_close else 0
        priority = self._calculate_priority_tier(pct_from_yesterday, self.pct_threshold)

        # Priority-based sampling rates
        PRIORITY_SAMPLE_RATES = {
            1: 1,   # Every message (extreme movers, 20%+)
            2: 3,   # Every 3rd message (strong movers, 10-20%)
            3: 5,   # Every 5th message (moderate movers, 5-10%)
            4: 10,  # Every 10th message (normal movers, threshold to 5x)
        }

        sample_rate = PRIORITY_SAMPLE_RATES.get(priority, 10)

        # Initialize per-symbol counter
        if symbol not in self._symbol_counters:
            self._symbol_counters[symbol] = 0

        self._symbol_counters[symbol] += 1

        # Update state if sample rate reached
        if self._symbol_counters[symbol] % sample_rate == 0:
            self._update_symbol_state(
                symbol=symbol,
                current_price=mid,
                bid=bid_price,
                ask=ask_price,
                spread_pct=spread_pct,
                timestamp=ts
            )
            # Store priority for debugging
            self._symbol_priorities[symbol] = priority

        # Cache every 10th price update for display (avoid overhead)
        if not hasattr(self, '_price_sample_counter'):
            self._price_sample_counter = 0
        self._price_sample_counter += 1
        if self._price_sample_counter % 10 == 0:
            price_cache.add_price(
                symbol=symbol,
                bid=bid_price,
                ask=ask_price,
                mid=mid
            )

        # Calculate percentage move from LAST ALERTED PRICE (not yesterday's close!)
        abs_r = abs(mid - last_alerted) / last_alerted

        # 1% threshold for meaningful price movements
        threshold = 0.01  # 1%

        # Check if threshold exceeded
        if abs_r > threshold:
            # Cooldown: Don't alert same symbol within 30 seconds
            current_time = time.time()
            last_alert = self.last_alert_time.get(symbol, 0)

            if current_time - last_alert >= 30:  # 30 second cooldown
                self._trigger_alert(event, symbol, mid, last_alerted, abs_r)
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
            "price_15min_ago": price_15min_ago,
            "price_5min_ago": price_5min_ago,
            "snapshot_15min_ts": pd.Timestamp(self.snapshot_15min[symbol][1], unit='s', tz='UTC').tz_convert('US/Eastern').isoformat() if symbol in self.snapshot_15min else None,
            "snapshot_5min_ts": pd.Timestamp(self.snapshot_5min[symbol][1], unit='s', tz='UTC').tz_convert('US/Eastern').isoformat() if symbol in self.snapshot_5min else None,
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

        # Batch update every 100 symbols or every 5 seconds
        if self._state_update_counter >= 100 or (current_ts - self._last_batch_update) >= 5:
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
        event: db.MBP1Msg,
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
            "bid": event.levels[0].bid_px * self.PX_SCALE,
            "ask": event.levels[0].ask_px * self.PX_SCALE,
            "bid_size": event.levels[0].bid_sz,
            "ask_size": event.levels[0].ask_sz,
        }

        # Print to console with flush to ensure it appears immediately
        alert_msg = f"[{ts.isoformat()}] {symbol} moved by {pct_move * 100:.2f}% (current: {current_price:.4f}, last: {last_reference_price:.4f})"
        print(alert_msg, flush=True)

        # Update the last alerted price to current price so we can detect next move
        self.last_alerted_price[symbol] = current_price

        # CRITICAL: Force an immediate symbol_state update when alert triggers
        # This ensures leaderboards stay in sync with recent alerts
        self._update_symbol_state(
            symbol=symbol,
            current_price=current_price,
            bid=event.levels[0].bid_px * self.PX_SCALE,
            ask=event.levels[0].ask_px * self.PX_SCALE,
            spread_pct=(event.levels[0].ask_px - event.levels[0].bid_px) / ((event.levels[0].ask_px + event.levels[0].bid_px) / 2) if (event.levels[0].ask_px + event.levels[0].bid_px) > 0 else 0,
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
