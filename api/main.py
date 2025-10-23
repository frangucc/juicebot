"""
FastAPI backend for the trading SMS assistant.

Provides REST API and WebSocket endpoints for:
- Viewing screener alerts
- Managing trades
- SMS webhook handling (future)
- Real-time updates via WebSocket
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import pytz
from functools import lru_cache
import time

from shared.database import supabase
from shared.config import settings

# Cache for leaderboard data (30 second TTL)
_leaderboard_cache = {}
_cache_ttl = 30

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
    baseline: str = "yesterday"
):
    """
    Get leaderboard of symbols categorized by % move ranges - FAST version with caching.

    Args:
        threshold: Minimum % move to include (default: 1.0%)
        price_filter: Filter by stock price range: 'small' (<$20), 'mid' ($20-$100), 'large' (>$100)
        baseline: Which baseline to use: 'yesterday', 'open', '15min', '5min'

    Returns:
        Categorized symbols by move ranges: 20%+, 10-20%, 1-10%
    """
    try:
        # Check cache first
        cache_key = f"{baseline}:{price_filter}:{threshold}"
        now = time.time()

        if cache_key in _leaderboard_cache:
            cached_data, cache_time = _leaderboard_cache[cache_key]
            if now - cache_time < _cache_ttl:
                return cached_data

        pct_field = f"pct_from_{baseline}"

        # Build query with database-level filtering
        query = supabase.table("symbol_state").select("*")

        # Apply price filter at database level
        if price_filter == "small":
            query = query.lt("current_price", 20)
        elif price_filter == "mid":
            query = query.gte("current_price", 20).lt("current_price", 100)
        elif price_filter == "large":
            query = query.gte("current_price", 100)

        # Filter by threshold at database level using OR condition
        query = query.or_(f"{pct_field}.gte.{threshold},{pct_field}.lte.{-threshold}")

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

        # Sort each category by actual % (highest gains first, then negatives)
        # This ensures +22% comes before -23%
        col_20_plus.sort(key=lambda x: x.get(pct_field, 0) or 0, reverse=True)
        col_10_to_20.sort(key=lambda x: x.get(pct_field, 0) or 0, reverse=True)
        col_1_to_10.sort(key=lambda x: x.get(pct_field, 0) or 0, reverse=True)

        result = {
            "baseline": baseline,
            "threshold": threshold,
            "price_filter": price_filter,
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


# Run with: uvicorn api.main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
