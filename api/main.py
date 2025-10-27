"""
FastAPI backend for the trading SMS assistant.

Provides REST API and WebSocket endpoints for:
- Viewing screener alerts
- Managing trades
- SMS webhook handling (future)
- Real-time updates via WebSocket
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import pytz
from functools import lru_cache
import time
import json
import redis
import asyncio

from shared.database import supabase
from shared.config import settings

# Import Murphy classifier and Momo Advanced
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from murphy_classifier_v2 import MurphyClassifier, Bar
from momo_advanced import MomoAdvanced

# Cache for leaderboard data (30 second TTL)
_leaderboard_cache = {}
_cache_ttl = 30

# Initialize classifiers (singletons)
murphy_classifier = MurphyClassifier()
momo_classifier = MomoAdvanced()

# Initialize FastAPI app
app = FastAPI(
    title="Trading SMS Assistant API",
    description="Backend API for real-time stock screener with SMS alerts",
    version="0.1.0",
)

# CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class AlertResponse(BaseModel):
    """Response model for alerts."""
    id: str
    symbol: str
    alert_type: str
    trigger_price: float
    trigger_time: str
    pct_move: float
    conditions: dict  # Include conditions with pct_move and previous_close
    metadata: dict


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    database: str


class BarData(BaseModel):
    """Single bar data from chart"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class MurphyClassifyRequest(BaseModel):
    """Request model for Murphy classification."""
    bars: List[BarData]  # Bars from chart (in chronological order)
    structure_price: float
    signal_type: str  # 'bos_bullish', 'bos_bearish', 'choch_bullish', 'choch_bearish'


class MurphyClassifyResponse(BaseModel):
    """Response model for Murphy classification."""
    direction: str  # '↑', '↓', or '−'
    stars: int  # 0-4
    grade: int  # 1-10
    confidence: float
    label: str  # Formatted label like '↑ **** [8]'
    interpretation: str
    # V2 enhancements
    has_liquidity_sweep: bool = False
    rejection_type: Optional[str] = None
    pattern: Optional[str] = None
    fvg_momentum: Optional[str] = None


class MomoClassifyRequest(BaseModel):
    """Request model for Momo momentum classification."""
    bars: List[BarData]  # Bars from chart (in chronological order)
    yesterday_close: Optional[float] = None


class MomoClassifyResponse(BaseModel):
    """Response model for Momo momentum classification."""
    direction: str  # '↑', '↓', or '−'
    stars: int  # 5-7 (multi-timeframe alignment count)
    confidence: float  # 0-100%
    action: str  # STRONG_BUY, BUY, WAIT, SELL, STRONG_SELL
    juice_score: float  # Overall momentum strength
    label: str  # Formatted label like '↑ ★★★★★★★ [85%] STRONG_BUY'

    # VWAP context
    vwap_zone: str  # DEEP_VALUE, VALUE, FAIR, EXTENDED, EXTREME
    vwap_distance_pct: float
    vwap_price: float

    # Leg context
    current_leg: int
    next_leg_probability: float
    in_pullback_zone: bool

    # Shadow trading
    shadow_signal: str  # STRONG_BUY, BUY, NEUTRAL, SELL
    shadow_confidence: float

    # Time context
    time_period: str  # premarket_early, morning_run, lunch_chop, etc.
    time_bias: str  # bullish, bearish, neutral

    interpretation: str


# Routes
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(pytz.timezone("US/Eastern")).isoformat(),
        "database": "connected" if supabase else "disconnected",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        response = supabase.table("screener_alerts").select("id").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.now(pytz.timezone("US/Eastern")).isoformat(),
        "database": db_status,
    }


@app.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    limit: int = 50,
    hours: Optional[int] = 24,
    symbol: Optional[str] = None
):
    """
    Get recent screener alerts.

    Args:
        limit: Maximum number of alerts to return (default: 50)
        hours: Only return alerts from last N hours (default: 24)
        symbol: Filter by symbol (optional)
    """
    try:
        # Build query
        query = supabase.table("screener_alerts").select("*")

        # Filter by time
        if hours:
            cutoff = datetime.now(pytz.UTC) - timedelta(hours=hours)
            query = query.gte("trigger_time", cutoff.isoformat())

        # Filter by symbol
        if symbol:
            query = query.eq("symbol", symbol.upper())

        # Order and limit
        query = query.order("trigger_time", desc=True).limit(limit)

        # Execute
        response = query.execute()

        # Format response
        alerts = []
        for alert in response.data:
            alerts.append({
                "id": alert["id"],
                "symbol": alert["symbol"],
                "alert_type": alert["alert_type"],
                "trigger_price": alert["trigger_price"],
                "trigger_time": alert["trigger_time"],
                "pct_move": alert["conditions"].get("pct_move", 0),
                "conditions": alert["conditions"],  # Include full conditions object
                "metadata": alert["metadata"],
            })

        return alerts

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch alerts: {str(e)}")


@app.get("/alerts/today")
async def get_todays_alerts():
    """Get all alerts from today."""
    try:
        # Get today's date in Eastern time
        et = pytz.timezone("US/Eastern")
        today = datetime.now(et).date()
        today_start = et.localize(datetime.combine(today, datetime.min.time()))

        response = (
            supabase.table("screener_alerts")
            .select("*")
            .gte("trigger_time", today_start.isoformat())
            .order("trigger_time", desc=True)
            .execute()
        )

        return {
            "date": today.isoformat(),
            "count": len(response.data),
            "alerts": response.data,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch today's alerts: {str(e)}")


@app.get("/alerts/stats")
async def get_alert_stats():
    """Get statistics about alerts."""
    try:
        # Get alerts from last 24 hours with count
        cutoff = datetime.now(pytz.UTC) - timedelta(hours=24)

        # First get the ACTUAL count
        count_response = (
            supabase.table("screener_alerts")
            .select("*", count="exact")
            .gte("trigger_time", cutoff.isoformat())
            .limit(5000)  # Increase limit to get more alerts
            .execute()
        )

        alerts = count_response.data
        actual_count = count_response.count if hasattr(count_response, 'count') else len(alerts)

        # Calculate stats
        total_alerts = actual_count
        symbols = set(a["symbol"] for a in alerts)
        avg_move = sum(a["conditions"].get("pct_move", 0) for a in alerts) / len(alerts) if len(alerts) > 0 else 0

        # Group by alert type
        by_type = {}
        for alert in alerts:
            alert_type = alert["alert_type"]
            by_type[alert_type] = by_type.get(alert_type, 0) + 1

        return {
            "period": "last_24h",
            "total_alerts": total_alerts,
            "unique_symbols": len(symbols),
            "avg_pct_move": round(avg_move, 2),
            "by_type": by_type,
            "note": f"Stats based on {len(alerts)} sampled alerts" if len(alerts) < total_alerts else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@app.get("/prices/recent")
async def get_recent_prices(limit: int = 20):
    """
    Get the most recent price updates from the scanner cache.

    Args:
        limit: Number of recent price updates to return (default: 20)

    Returns:
        List of recent price updates with symbol, bid, ask, mid, and timestamp
    """
    try:
        from shared.price_cache import price_cache
        return price_cache.get_recent_prices(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent prices: {str(e)}")


@app.get("/bars/{symbol}")
async def get_bars(symbol: str, limit: int = 500, include_legacy: bool = False):
    """
    Get 1-minute OHLCV bars for a specific symbol.

    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        limit: Number of bars to return (default: 500, max: 1000)
        include_legacy: Include legacy MBP-1 data (volume=0) (default: False)

    Returns:
        List of 1-minute OHLCV bars with timestamp, open, high, low, close, volume
    """
    try:
        # Cap limit at 1000
        limit = min(limit, 1000)

        # Query price_bars table
        query = supabase.table("price_bars").select("*").eq("symbol", symbol.upper())

        # ✅ Filter out legacy data unless explicitly requested
        if not include_legacy:
            query = query.or_("is_legacy.is.null,is_legacy.eq.false")

        response = query.order("timestamp", desc=True).limit(limit).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail=f"No bar data found for symbol {symbol}")

        # Reverse to get chronological order (oldest first)
        bars = list(reversed(response.data))

        return bars
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bar data: {str(e)}")


@app.get("/bars/{symbol}/historical")
async def get_historical_bars(symbol: str, limit: int = 500):
    """
    Get historical 1-minute OHLCV bars for a specific symbol from historical_bars table.

    Args:
        symbol: Stock symbol (e.g., 'BYND')
        limit: Number of bars to return (default: 500, max: 10000)

    Returns:
        List of 1-minute OHLCV bars with timestamp, open, high, low, close, volume
    """
    try:
        # Cap limit at 10000 for historical data (allow loading all available bars)
        limit = min(limit, 10000)

        # Supabase Python client has a max limit of 1000 per request
        # Need to paginate to get all bars
        all_bars = []
        page_size = 1000
        offset = 0

        while len(all_bars) < limit:
            response = (supabase.table("historical_bars")
                       .select("*")
                       .eq("symbol", symbol.upper())
                       .order("timestamp", desc=True)
                       .range(offset, offset + page_size - 1)
                       .execute())

            if not response.data:
                break  # No more data

            all_bars.extend(response.data)
            offset += page_size

            if len(response.data) < page_size:
                break  # Last page

        if not all_bars:
            raise HTTPException(status_code=404, detail=f"No historical bar data found for symbol {symbol}")

        # Reverse to get chronological order (oldest first)
        bars = list(reversed(all_bars[:limit]))

        return bars
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch historical bar data: {str(e)}")


@app.get("/symbols/state")
async def get_symbol_state(
    threshold: float = 1.0,
    price_filter: Optional[str] = None,
    baseline: str = "yesterday",
    limit: int = 200
):
    """
    Get current state of all symbols with significant moves.

    Args:
        threshold: Minimum % move to include (default: 1.0%)
        price_filter: Filter by stock price range: 'small' (<$20), 'mid' ($20-$100), 'large' (>$100)
        baseline: Which baseline to use for filtering: 'yesterday', 'open', '15min', '5min'
        limit: Maximum number of symbols to return (default: 200)

    Returns:
        List of symbols with current state including all timeframe % moves
    """
    try:
        # Build query
        query = supabase.table("symbol_state").select("*")

        # Filter by % move threshold based on baseline
        pct_field = f"pct_from_{baseline}"
        query = query.or_(f"{pct_field}.gte.{threshold},{pct_field}.lte.{-threshold}")

        # Apply price filter
        if price_filter == "small":
            query = query.lt("current_price", 20)
        elif price_filter == "mid":
            query = query.gte("current_price", 20).lt("current_price", 100)
        elif price_filter == "large":
            query = query.gte("current_price", 100)

        # Order by absolute % move (descending) and limit
        query = query.order(pct_field, desc=True).limit(limit)

        response = query.execute()

        return response.data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch symbol state: {str(e)}")


@app.get("/symbols/leaderboard")
async def get_leaderboard(
    threshold: float = 1.0,
    price_filter: Optional[str] = None,
    baseline: str = "yesterday",
    direction: str = "up"
):
    """
    Get leaderboard of symbols categorized by % move ranges - FAST version with caching.

    Args:
        threshold: Minimum % move to include (default: 1.0%)
        price_filter: Filter by stock price range: 'small' (<$20), 'mid' ($20-$100), 'large' (>$100)
        baseline: Which baseline to use: 'yesterday', 'open', '15min', '5min'
        direction: 'up' for gap ups (positive %), 'down' for gap downs (negative %)

    Returns:
        Categorized symbols by move ranges: 20%+, 10-20%, 1-10%
    """
    try:
        # Check cache first
        cache_key = f"{baseline}:{price_filter}:{threshold}:{direction}"
        now = time.time()

        if cache_key in _leaderboard_cache:
            cached_data, cache_time = _leaderboard_cache[cache_key]
            if now - cache_time < _cache_ttl:
                return cached_data

        pct_field = f"pct_from_{baseline}"

        # Build query with database-level filtering
        query = supabase.table("symbol_state").select("*")

        # CRITICAL: Smart time filtering based on market status
        # Show most recent trading data, even on weekends/holidays
        et = pytz.timezone("US/Eastern")
        now_et = datetime.now(et)

        # Market hours: 9:30 AM - 4:00 PM ET, Mon-Fri
        is_weekend = now_et.weekday() >= 5  # Saturday=5, Sunday=6
        market_open_time = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close_time = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        is_market_hours = not is_weekend and market_open_time <= now_et <= market_close_time + timedelta(hours=1)

        if is_market_hours:
            # Market is LIVE - show data from last 4 hours only (current session)
            cutoff_time = datetime.now(pytz.UTC) - timedelta(hours=4)
        else:
            # Market is CLOSED - find the last trading day's data
            # Go back up to 7 days to cover long weekends/holidays
            # This ensures Friday data shows on Saturday/Sunday
            cutoff_time = datetime.now(pytz.UTC) - timedelta(days=7)

        query = query.gte("last_updated", cutoff_time.isoformat())

        # Apply price filter at database level
        if price_filter == "small":
            query = query.lt("current_price", 20)
        elif price_filter == "mid":
            query = query.gte("current_price", 20).lt("current_price", 100)
        elif price_filter == "large":
            query = query.gte("current_price", 100)

        # Filter by direction (gap ups vs gap downs)
        if direction == "down":
            # Gap downs: negative % moves only
            query = query.lte(pct_field, -threshold)
            # CRITICAL: Order by most negative first to get biggest losers before limit
            query = query.order(pct_field, desc=False)
        else:
            # Gap ups (default): positive % moves only
            query = query.gte(pct_field, threshold)
            # CRITICAL: Order by most positive first to get biggest gainers before limit
            query = query.order(pct_field, desc=True)

        # Limit to top movers only - we don't need ALL symbols
        query = query.limit(2000)

        response = query.execute()
        symbols = response.data

        # Categorize by % ranges
        col_20_plus = []
        col_10_to_20 = []
        col_1_to_10 = []

        for symbol in symbols:
            pct = symbol.get(pct_field, 0) or 0
            if pct is None:
                continue
            abs_pct = abs(pct)

            if abs_pct >= 20:
                col_20_plus.append(symbol)
            elif abs_pct >= 10:
                col_10_to_20.append(symbol)
            elif abs_pct >= threshold:
                col_1_to_10.append(symbol)

        # Sort each category based on direction
        if direction == "down":
            # Gap downs: sort by most negative first (-62% → -50% → -25%)
            col_20_plus.sort(key=lambda x: x.get(pct_field, 0) or 0, reverse=False)
            col_10_to_20.sort(key=lambda x: x.get(pct_field, 0) or 0, reverse=False)
            col_1_to_10.sort(key=lambda x: x.get(pct_field, 0) or 0, reverse=False)
        else:
            # Gap ups: sort by most positive first (+62% → +50% → +25%)
            col_20_plus.sort(key=lambda x: x.get(pct_field, 0) or 0, reverse=True)
            col_10_to_20.sort(key=lambda x: x.get(pct_field, 0) or 0, reverse=True)
            col_1_to_10.sort(key=lambda x: x.get(pct_field, 0) or 0, reverse=True)

        result = {
            "baseline": baseline,
            "threshold": threshold,
            "price_filter": price_filter,
            "direction": direction,
            "col_20_plus": col_20_plus,
            "col_10_to_20": col_10_to_20,
            "col_1_to_10": col_1_to_10,
            "total_symbols": len(symbols)
        }

        # Cache the result
        _leaderboard_cache[cache_key] = (result, now)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch leaderboard: {str(e)}")


@app.get("/symbols/{symbol}/latest-price")
async def get_latest_price(symbol: str):
    """
    Get the most recent price for a symbol from price_bars.

    Returns:
        Latest OHLCV bar data with the close price
    """
    try:
        # Get most recent bar from price_bars
        response = (
            supabase.table("price_bars")
            .select("*")
            .eq("symbol", symbol.upper())
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            bar = response.data[0]
            return {
                "symbol": symbol.upper(),
                "price": bar["close"],
                "timestamp": bar["timestamp"],
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar["volume"],
                "trade_count": bar["trade_count"]
            }
        else:
            # Fallback to symbol_state if no bars yet
            response = (
                supabase.table("symbol_state")
                .select("current_price,last_updated")
                .eq("symbol", symbol.upper())
                .limit(1)
                .execute()
            )
            if response.data:
                return {
                    "symbol": symbol.upper(),
                    "price": response.data[0]["current_price"],
                    "timestamp": response.data[0]["last_updated"],
                    "source": "symbol_state"
                }
            else:
                raise HTTPException(status_code=404, detail=f"No price data found for {symbol}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest price: {str(e)}")


@app.get("/symbols/{symbol}/realtime-price")
async def get_realtime_price(symbol: str):
    """
    Get real-time price directly from symbol_state (updated every 2s by screener).
    This is faster than latest-price which checks price_bars first (60s bars).

    Returns:
        Real-time price data from live screener
    """
    try:
        response = (
            supabase.table("symbol_state")
            .select("*")
            .eq("symbol", symbol.upper())
            .limit(1)
            .execute()
        )

        if response.data:
            data = response.data[0]
            return {
                "symbol": symbol.upper(),
                "price": data["current_price"],
                "timestamp": data["last_updated"],
                "pct_from_yesterday": data.get("pct_from_yesterday"),
                "pct_from_open": data.get("pct_from_open"),
                "source": "symbol_state"
            }
        else:
            raise HTTPException(status_code=404, detail=f"No real-time data found for {symbol}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch real-time price: {str(e)}")


@app.get("/discord/juice-boxes")
async def get_discord_juice_boxes():
    """
    Get Discord juice box counts (3+) for all tickers.

    Returns:
        Dictionary mapping symbols to juice box counts (only symbols with 3+ juice boxes)
    """
    try:
        import psycopg2
        from shared.config import settings

        if not settings.database2_url:
            return {}

        conn = psycopg2.connect(settings.database2_url)
        cursor = conn.cursor()

        query = '''
        WITH ticker_stats AS (
          SELECT
            t.symbol,
            COUNT(DISTINCT td.message_id) as mention_count,
            COUNT(DISTINCT td.message_id) FILTER (WHERE m.discord_timestamp >= NOW() - INTERVAL '5 minutes') as mentions_5min,
            COUNT(DISTINCT td.message_id) FILTER (WHERE m.discord_timestamp >= NOW() - INTERVAL '15 minutes') as mentions_15min
          FROM tickers t
          JOIN ticker_detections td ON t.symbol = td.ticker_symbol
          JOIN messages m ON td.message_id = m.id
          WHERE m.discord_timestamp >= CURRENT_DATE
          GROUP BY t.symbol
        )
        SELECT
          symbol,
          LEAST(
            CASE
              WHEN mention_count >= 20 THEN 4
              WHEN mention_count >= 10 THEN 3
              WHEN mention_count >= 5 THEN 2
              WHEN mention_count >= 2 THEN 1
              ELSE 0
            END +
            CASE
              WHEN mentions_5min >= 3 THEN 1
              WHEN mentions_15min >= 5 THEN 1
              ELSE 0
            END,
            4
          ) as total_juice_boxes
        FROM ticker_stats
        WHERE LEAST(
            CASE
              WHEN mention_count >= 20 THEN 4
              WHEN mention_count >= 10 THEN 3
              WHEN mention_count >= 5 THEN 2
              WHEN mention_count >= 2 THEN 1
              ELSE 0
            END +
            CASE
              WHEN mentions_5min >= 3 THEN 1
              WHEN mentions_15min >= 5 THEN 1
              ELSE 0
            END,
            4
          ) >= 3;
        '''

        cursor.execute(query)
        results = cursor.fetchall()

        # Convert to dictionary
        juice_boxes = {row[0]: row[1] for row in results}

        cursor.close()
        conn.close()

        return juice_boxes

    except Exception as e:
        # Return empty dict on error (graceful degradation)
        print(f"Discord juice box query failed: {str(e)}")
        return {}


@app.post("/murphy/classify", response_model=MurphyClassifyResponse)
async def classify_with_murphy(request: MurphyClassifyRequest):
    """
    Classify a BoS/CHoCH signal using Murphy's classifier.

    Args:
        request: Murphy classification request with symbol, structure_price, and signal_type

    Returns:
        Murphy's analysis with direction, stars, grade, and interpretation
    """
    try:
        # Use bars provided by chart (already in chronological order)
        if not request.bars or len(request.bars) < 20:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient bar data (need at least 20 bars, got {len(request.bars)})"
            )

        # Convert to Bar objects
        bars = []
        for idx, bar_data in enumerate(request.bars):
            bars.append(Bar(
                timestamp=bar_data.timestamp,
                open=bar_data.open,
                high=bar_data.high,
                low=bar_data.low,
                close=bar_data.close,
                volume=int(bar_data.volume),
                index=idx
            ))

        # Calculate structure age (time since the signal)
        current_index = len(bars) - 1
        structure_age_bars = 10  # Default assumption: structure formed ~10 bars ago

        # Run Murphy classification with timeout protection
        print(f"[Murphy API] Classifying {len(bars)} bars for {request.structure_price}")

        try:
            murphy_signal = murphy_classifier.classify(
                bars=bars,
                signal_index=current_index,
                structure_age_bars=structure_age_bars,
                level_price=request.structure_price
            )
            print(f"[Murphy API] Classification complete: {murphy_signal.direction} {murphy_signal.stars} stars")
        except Exception as classify_error:
            print(f"[Murphy API] Classification error: {str(classify_error)}")
            raise

        # Format the label
        label = murphy_classifier.format_label(murphy_signal)

        return MurphyClassifyResponse(
            direction=murphy_signal.direction,
            stars=murphy_signal.stars,
            grade=murphy_signal.grade,
            confidence=murphy_signal.confidence,
            label=label,
            interpretation=murphy_signal.interpretation,
            has_liquidity_sweep=murphy_signal.has_liquidity_sweep,
            rejection_type=murphy_signal.rejection_type,
            pattern=murphy_signal.pattern,
            fvg_momentum=murphy_signal.fvg_momentum
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Murphy classification failed: {str(e)}"
        )


@app.post("/momo/classify", response_model=MomoClassifyResponse)
async def classify_with_momo(request: MomoClassifyRequest):
    """
    Classify momentum using Momo Advanced multi-timeframe classifier.

    Args:
        request: Momo classification request with bars and optional yesterday_close

    Returns:
        Momo's analysis with direction, stars (5-7), confidence, VWAP context, legs, etc.
    """
    try:
        # Use bars provided by chart (already in chronological order)
        if not request.bars or len(request.bars) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient bar data (need at least 50 bars, got {len(request.bars)})"
            )

        # Convert to Bar objects
        bars = []
        for idx, bar_data in enumerate(request.bars):
            bars.append(Bar(
                timestamp=bar_data.timestamp,
                open=bar_data.open,
                high=bar_data.high,
                low=bar_data.low,
                close=bar_data.close,
                volume=int(bar_data.volume),
                index=idx
            ))

        # Classify at most recent bar
        current_index = len(bars) - 1

        # Run Momo classification
        print(f"[Momo API] Classifying {len(bars)} bars with yesterday_close={request.yesterday_close}")

        try:
            momo_signal = momo_classifier.classify(
                bars=bars,
                signal_index=current_index,
                yesterday_close=request.yesterday_close
            )
            print(f"[Momo API] Classification complete: {momo_signal.direction} {momo_signal.stars}/7 stars, {momo_signal.action}")
        except Exception as classify_error:
            print(f"[Momo API] Classification error: {str(classify_error)}")
            raise

        # Format the label
        stars_str = '★' * momo_signal.stars
        conf_pct = int(momo_signal.confidence * 100)
        label = f"{momo_signal.direction} {stars_str} [{conf_pct}%] {momo_signal.action}"

        # Build interpretation
        interpretation_parts = []

        # Overall momentum
        if momo_signal.stars >= 7:
            interpretation_parts.append(f"MAX JUICE! All 7 timeframes aligned {momo_signal.direction}")
        elif momo_signal.stars >= 6:
            interpretation_parts.append(f"Strong momentum with {momo_signal.stars}/7 timeframes aligned")
        else:
            interpretation_parts.append(f"Moderate momentum with {momo_signal.stars}/7 timeframes aligned")

        # VWAP context
        if momo_signal.vwap_context.zone == 'DEEP_VALUE':
            interpretation_parts.append(f"Deep value zone ({momo_signal.vwap_context.distance_pct:.1f}% below VWAP) - excellent entry")
        elif momo_signal.vwap_context.zone == 'VALUE':
            interpretation_parts.append(f"Value zone ({momo_signal.vwap_context.distance_pct:.1f}% below VWAP) - buying value")
        elif momo_signal.vwap_context.zone == 'EXTENDED':
            interpretation_parts.append(f"Extended ({momo_signal.vwap_context.distance_pct:.1f}% above VWAP) - caution")
        elif momo_signal.vwap_context.zone == 'EXTREME':
            interpretation_parts.append(f"Extreme extension ({momo_signal.vwap_context.distance_pct:.1f}% from VWAP) - avoid entry")

        # Leg context
        if momo_signal.leg_context.in_pullback_zone:
            interpretation_parts.append(f"In pullback zone after leg {momo_signal.leg_context.current_leg} - prime for continuation ({momo_signal.leg_context.next_leg_probability:.0%} probability)")
        else:
            interpretation_parts.append(f"Leg {momo_signal.leg_context.current_leg}, next leg probability: {momo_signal.leg_context.next_leg_probability:.0%}")

        # Time context
        if momo_signal.time_period.bias == 'bullish':
            interpretation_parts.append(f"{momo_signal.time_period.period} - favorable time window")
        elif momo_signal.time_period.bias == 'bearish':
            interpretation_parts.append(f"{momo_signal.time_period.period} - caution on timing")

        interpretation = ". ".join(interpretation_parts) + "."

        return MomoClassifyResponse(
            direction=momo_signal.direction,
            stars=momo_signal.stars,
            confidence=momo_signal.confidence * 100,  # Convert to percentage
            action=momo_signal.action,
            juice_score=momo_signal.juice_score,
            label=label,
            vwap_zone=momo_signal.vwap_context.zone,
            vwap_distance_pct=momo_signal.vwap_context.distance_pct,
            vwap_price=momo_signal.vwap,
            current_leg=momo_signal.leg_context.current_leg,
            next_leg_probability=momo_signal.leg_context.next_leg_probability * 100,  # Convert to percentage
            in_pullback_zone=momo_signal.leg_context.in_pullback_zone,
            shadow_signal=momo_signal.shadow_signal.get('signal', 'NEUTRAL'),
            shadow_confidence=momo_signal.shadow_signal.get('confidence', 0) * 100,  # Convert to percentage
            time_period=momo_signal.time_period.period,
            time_bias=momo_signal.time_period.bias,
            interpretation=interpretation
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Momo classification failed: {str(e)}"
        )


# ===== MURPHY TEST & RECORDING ENDPOINTS =====

# Pydantic models for request/response
class CreateTestSessionRequest(BaseModel):
    symbol: str
    config: Optional[dict] = None
    notes: Optional[str] = None

class EndTestSessionRequest(BaseModel):
    status: str = 'completed'  # 'completed' or 'cancelled'


@app.post("/murphy-test/sessions")
async def create_test_session(request: CreateTestSessionRequest):
    """Create a new Murphy test session."""
    try:
        from murphy_test_recorder import murphy_recorder

        if murphy_recorder is None:
            raise HTTPException(
                status_code=503,
                detail="Murphy test recorder not available. Check Supabase connection and environment variables."
            )

        session = murphy_recorder.create_session(
            symbol=request.symbol,
            config=request.config,
            notes=request.notes
        )

        return {
            "success": True,
            "session": {
                "id": session.id,
                "symbol": session.symbol,
                "started_at": session.started_at.isoformat(),
                "status": session.status,
                "config": session.config,
                "metrics": session.metrics
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@app.get("/murphy-test/sessions/{symbol}/active")
async def get_active_test_session(symbol: str):
    """Get active test session for a symbol."""
    try:
        from murphy_test_recorder import murphy_recorder

        if murphy_recorder is None:
            return {"success": True, "session": None, "message": "Test recorder not available"}

        session = murphy_recorder.get_active_session(symbol)

        if not session:
            return {"success": True, "session": None}

        return {
            "success": True,
            "session": {
                "id": session.id,
                "symbol": session.symbol,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "status": session.status,
                "config": session.config,
                "metrics": session.metrics,
                "notes": session.notes
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@app.get("/murphy-test/sessions/{session_id}")
async def get_test_session(session_id: str):
    """Get test session by ID."""
    try:
        from murphy_test_recorder import murphy_recorder

        session = murphy_recorder.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "success": True,
            "session": {
                "id": session.id,
                "symbol": session.symbol,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "status": session.status,
                "config": session.config,
                "metrics": session.metrics,
                "notes": session.notes
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@app.post("/murphy-test/sessions/{session_id}/end")
async def end_test_session(session_id: str, request: EndTestSessionRequest):
    """End a test session."""
    try:
        from murphy_test_recorder import murphy_recorder

        murphy_recorder.end_session(session_id, request.status)

        return {"success": True, "message": f"Session ended with status: {request.status}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")


@app.get("/murphy-test/sessions/{session_id}/signals")
async def get_test_session_signals(
    session_id: str,
    limit: int = 100,
    passed_filter: Optional[bool] = None
):
    """Get signals for a test session."""
    try:
        from murphy_test_recorder import murphy_recorder

        signals = murphy_recorder.get_session_signals(
            session_id=session_id,
            limit=limit,
            passed_filter=passed_filter
        )

        return {
            "success": True,
            "signals": signals,
            "count": len(signals)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get signals: {str(e)}")


@app.get("/murphy-test/sessions")
async def get_recent_test_sessions(symbol: Optional[str] = None, limit: int = 10):
    """Get recent test sessions."""
    try:
        from murphy_test_recorder import murphy_recorder

        sessions = murphy_recorder.get_recent_sessions(symbol=symbol, limit=limit)

        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")


@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """
    WebSocket endpoint for real-time price updates.

    Subscribes to Redis pub/sub and streams price updates to connected clients.
    """
    await websocket.accept()

    # Create Redis subscriber
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    pubsub = redis_client.pubsub()
    pubsub.subscribe('price_updates')

    try:
        # Send initial connection success message
        await websocket.send_json({"type": "connected", "message": "Real-time price feed connected"})

        # Listen for messages from Redis and forward to WebSocket
        async def redis_listener():
            """Listen to Redis pub/sub in the background."""
            for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # Parse and forward the price update
                        price_data = json.loads(message['data'])
                        await websocket.send_json({
                            "type": "price_update",
                            "data": price_data
                        })
                    except Exception as e:
                        # Skip malformed messages
                        pass

                # Allow other async tasks to run
                await asyncio.sleep(0)

        # Run the Redis listener
        await redis_listener()

    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        pubsub.unsubscribe()
        pubsub.close()
        redis_client.close()


# Run with: uvicorn api.main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
