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

from shared.database import supabase
from shared.config import settings

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
        # Get alerts from last 24 hours
        cutoff = datetime.now(pytz.UTC) - timedelta(hours=24)

        response = (
            supabase.table("screener_alerts")
            .select("*")
            .gte("trigger_time", cutoff.isoformat())
            .execute()
        )

        alerts = response.data

        # Calculate stats
        total_alerts = len(alerts)
        symbols = set(a["symbol"] for a in alerts)
        avg_move = sum(a["conditions"].get("pct_move", 0) for a in alerts) / total_alerts if total_alerts > 0 else 0

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


# Run with: uvicorn api.main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
