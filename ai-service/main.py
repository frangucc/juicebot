"""
JuiceBot AI Service

FastAPI server providing AI-powered trading assistance.
Runs on port 8002.
"""

import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from pathlib import Path
from dotenv import load_dotenv

from agents.smc_agent import SMCAgent
from fast_classifier_v2 import TradingClassifierV2 as TradingClassifier
from websocket_client import BarDataClient
from position_storage import PositionStorage

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Initialize FastAPI
app = FastAPI(
    title="JuiceBot AI Service",
    description="AI trading assistant with SMC analysis",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory agent storage (will move to database later)
active_agents: Dict[str, SMCAgent] = {}

# Fast-path classifier per symbol
classifiers: Dict[str, TradingClassifier] = {}

# WebSocket client for bar data
ws_client: Optional[BarDataClient] = None


# Pydantic models
class ChatMessage(BaseModel):
    """Chat message from user."""
    symbol: str
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from AI."""
    response: str
    conversation_id: str
    timestamp: str
    prompt: Optional[str] = None  # Full prompt sent to LLM


class MemoryItem(BaseModel):
    """Memory item saved by user."""
    content: str
    tags: Optional[List[str]] = None


class MarketDataUpdate(BaseModel):
    """Market data update from WebSocket."""
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


# Startup and shutdown
@app.on_event("startup")
async def startup_event():
    """Initialize WebSocket client on startup."""
    global ws_client
    ws_client = BarDataClient(classifiers)
    # Start WebSocket client in background
    import asyncio
    asyncio.create_task(ws_client.start())
    print("[AI Service] 🚀 Starting WebSocket client for bar data...")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global ws_client
    if ws_client:
        await ws_client.stop()
    print("[AI Service] 👋 Shutting down...")


# Slash Command Handler
async def handle_slash_command(msg: ChatMessage) -> Optional[ChatResponse]:
    """Handle slash commands like /trade, /test, etc."""
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    from trade_command_executor import TradeCommandExecutor

    message = msg.message.strip()
    parts = message.split()
    command = parts[0].lower()

    # /trade command - show available commands
    if command == '/trade':
        help_text = """TRADE COMMANDS:
Type directly (no slash):

BASIC:
  long <qty> @ <price> → enter long ● F
  short <qty> @ <price> → enter short ● F
  pos / position → check position + P&L ● F
  close / exit → close position ● F
  flat → flatten all positions ● F
  price / last → current price ● F
  volume / vol → current volume ● F
  range / high / low → today's range ● F

ADVANCED:
  accumulate → scale into position ● F
  scaleout → scale out of position ● F
  reverse → flip position instantly ● F
  stop / sl → set stop loss ● F
  bracket → entry + stop + target ● F
  reset → clear session P&L ● F

AI-ASSISTED:
  flatten-smart → AI exit with limits ● F+AI
  reverse-smart → AI reversal w/ safety ● F+AI

EXAMPLES:
  > long 1000 @ 0.57
  > pos
  > flat
  > reverse

All commands save to database."""

        return ChatResponse(
            response=help_text,
            conversation_id=msg.conversation_id or "slash_trade",
            timestamp=datetime.now().isoformat()
        )

    # /test command - run test suites
    elif command == '/test':
        if len(parts) < 2:
            help_text = """/test - Test Suite

Available tests:
  /test trade        Test /trade commands
  /test indicators   Test /indicators commands
  /test strategy     Test /strategy commands

Type: /test trade"""

            return ChatResponse(
                response=help_text,
                conversation_id=msg.conversation_id or "slash_test",
                timestamp=datetime.now().isoformat()
            )

        # Check for /test trade subcommands
        if parts[1].lower() == 'trade':
            # Default to 'fast' if no subcommand provided
            if len(parts) < 3:
                test_type = 'fast'
                # Show confirmation that we're defaulting to fast
                confirm_msg = "Running /test trade fast (default)...\n\n"
            else:
                test_type = parts[2].lower()
                confirm_msg = ""

            # Map: fast → core, all → all, ai → ai, -quick → core --fast
            if test_type == 'fast':
                suite = 'core'
                fast_flag = False
            elif test_type == 'all':
                suite = 'all'
                fast_flag = False
            elif test_type == '-quick':
                suite = 'core'
                fast_flag = True
            elif test_type == 'ai':
                suite = 'ai'
                fast_flag = False
            else:
                return ChatResponse(
                    response=f"❌ Unknown test type: {test_type}\nUse: fast, all, ai, or -quick",
                    conversation_id=msg.conversation_id or "slash_test_error",
                    timestamp=datetime.now().isoformat()
                )

        elif parts[1].lower() == 'indicators':
            return ChatResponse(
                response="📊 Indicator tests coming soon...",
                conversation_id=msg.conversation_id or "slash_test_indicators",
                timestamp=datetime.now().isoformat()
            )

        elif parts[1].lower() == 'strategy':
            return ChatResponse(
                response="🔴 Strategy tests coming soon...",
                conversation_id=msg.conversation_id or "slash_test_strategy",
                timestamp=datetime.now().isoformat()
            )

        else:
            return ChatResponse(
                response=f"❌ Unknown test category: {parts[1]}\nUse: trade, indicators, or strategy",
                conversation_id=msg.conversation_id or "slash_test_error",
                timestamp=datetime.now().isoformat()
            )

        try:
            # Import test suite
            import asyncio
            import subprocess

            # Run tests in subprocess
            cmd = ['python3', 'test_trade_commands.py', suite]
            if fast_flag:
                cmd.append('--fast')
            cmd.extend(['--symbol', msg.symbol])

            result = subprocess.run(
                cmd,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                capture_output=True,
                text=True,
                timeout=60
            )

            output = confirm_msg + result.stdout + result.stderr if 'confirm_msg' in locals() else result.stdout + result.stderr

            return ChatResponse(
                response=output,
                conversation_id=msg.conversation_id or "test_results",
                timestamp=datetime.now().isoformat()
            )

        except subprocess.TimeoutExpired:
            return ChatResponse(
                response="⚠️ Test suite timed out after 60s",
                conversation_id=msg.conversation_id or "test_error",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            return ChatResponse(
                response=f"❌ Test error: {str(e)}",
                conversation_id=msg.conversation_id or "test_error",
                timestamp=datetime.now().isoformat()
            )

    return None


# Routes
@app.get("/")
async def root():
    """Health check."""
    return {
        "service": "JuiceBot AI",
        "status": "running",
        "version": "1.0.0",
        "websocket_connected": ws_client.running if ws_client else False,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(msg: ChatMessage):
    """
    Chat with AI agent.

    Args:
        msg: Chat message with symbol and content

    Returns:
        AI response
    """
    # Check for slash commands
    if msg.message.startswith('/'):
        slash_response = await handle_slash_command(msg)
        if slash_response:
            return slash_response

    # Get or create classifier for this symbol
    conversation_id = msg.conversation_id or f"conv_{msg.symbol}_{datetime.now().timestamp()}"

    if msg.symbol not in classifiers:
        classifiers[msg.symbol] = TradingClassifier(conversation_id=conversation_id)

    classifier = classifiers[msg.symbol]

    # Update classifier's conversation_id for state tracking
    classifier.conversation_id = conversation_id
    classifier.executor.conversation_id = conversation_id

    # Auto-subscribe to WebSocket bar data for this symbol
    if ws_client and ws_client.running and msg.symbol not in ws_client.subscribed_symbols:
        await ws_client.subscribe(msg.symbol)

    # Try fast-path first
    fast_response = await classifier.classify(msg.message, msg.symbol)
    if fast_response:
        return ChatResponse(
            response=fast_response.text,
            conversation_id=msg.conversation_id or f"fast_{msg.symbol}",
            timestamp=datetime.now().isoformat()
        )

    # Slow path - use LLM (reuse conversation_id from above)
    if conversation_id not in active_agents:
        active_agents[conversation_id] = SMCAgent()

    agent = active_agents[conversation_id]

    try:
        # Get bar history from classifier
        classifier = classifiers.get(msg.symbol)
        bar_history = classifier.bar_history if classifier else []

        # Analyze and respond (passing bar_history to tools) - returns (response, prompt)
        response, prompt = await agent.analyze(msg.symbol, msg.message, bar_history)

        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat(),
            prompt=prompt
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")


@app.websocket("/events/{symbol}")
async def events_stream(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for server-side event streaming.

    Client connects and automatically receives all events published for this symbol.
    Used for: scaleout progress, order fills, alerts, etc.
    """
    from event_bus import event_bus

    await websocket.accept()
    conversation_id = f"ws_{symbol}_{datetime.now().timestamp()}"

    # Subscribe to event bus
    event_bus.subscribe(symbol, conversation_id, websocket)

    try:
        # Keep connection alive and listen for events
        while True:
            # Just wait for disconnect or periodic ping
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping", "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect:
        print(f"[WebSocket] {symbol} disconnected")
        event_bus.unsubscribe(symbol, conversation_id)
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        event_bus.unsubscribe(symbol, conversation_id)


@app.websocket("/chat/stream")
async def chat_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.

    Client sends: {"symbol": "BYND", "message": "What do you see?", "conversation_id": "..."}
    Server streams: {"type": "chunk", "content": "..."} or {"type": "done", "response": "..."}
    """
    await websocket.accept()

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            symbol = data.get("symbol")
            message = data.get("message")
            conversation_id = data.get("conversation_id", f"conv_{symbol}_{datetime.now().timestamp()}")

            if not symbol or not message:
                await websocket.send_json({"type": "error", "message": "Missing symbol or message"})
                continue

            # Get or create agent
            if conversation_id not in active_agents:
                active_agents[conversation_id] = SMCAgent()

            agent = active_agents[conversation_id]

            # Analyze (streaming not implemented yet, will send full response)
            response = await agent.analyze(symbol, message)

            # Send response
            await websocket.send_json({
                "type": "done",
                "response": response,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            })

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})


@app.get("/memories")
async def get_memories():
    """Get all saved memories."""
    memories_file = Path(__file__).parent / "memories" / "user_memories.json"

    if not memories_file.exists():
        return {"memories": []}

    with open(memories_file, "r") as f:
        memories = json.load(f)

    return {"memories": memories}


@app.post("/memory")
async def save_memory(memory: MemoryItem):
    """Save a new memory."""
    memories_dir = Path(__file__).parent / "memories"
    memories_dir.mkdir(exist_ok=True)

    memories_file = memories_dir / "user_memories.json"

    # Load existing memories
    if memories_file.exists():
        with open(memories_file, "r") as f:
            memories = json.load(f)
    else:
        memories = []

    # Add new memory
    memories.append({
        "content": memory.content,
        "tags": memory.tags or [],
        "timestamp": datetime.now().isoformat()
    })

    # Save
    with open(memories_file, "w") as f:
        json.dump(memories, f, indent=2)

    return {"status": "saved", "memory": memories[-1]}


@app.post("/market_data")
async def update_market_data(data: MarketDataUpdate):
    """
    Receive market data update from WebSocket stream.

    Updates the classifier's in-memory buffer for fast-path responses.
    """
    if data.symbol not in classifiers:
        classifiers[data.symbol] = TradingClassifier()

    classifier = classifiers[data.symbol]
    classifier.update_market_data(data.symbol, {
        'timestamp': data.timestamp,
        'open': data.open,
        'high': data.high,
        'low': data.low,
        'close': data.close,
        'volume': data.volume
    })

    return {"status": "ok", "symbol": data.symbol, "price": data.close}


@app.post("/analyze/levels")
async def analyze_levels(symbol: str):
    """
    Analyze bar data and return key price levels.

    Uses in-memory bar history from WebSocket feed.
    Returns: concentration levels, support/resistance, next BoS up/down, high/low
    """
    if symbol not in classifiers:
        return {"error": f"No data available for {symbol}"}

    classifier = classifiers[symbol]

    if not classifier.bar_history:
        return {"error": f"No bar history for {symbol}"}

    from tools.bar_analysis import analyze_price_levels

    levels = await analyze_price_levels(symbol, classifier.bar_history)
    return levels


@app.get("/agents")
async def list_agents():
    """List available agents."""
    return {
        "agents": [
            {
                "name": "SMC Agent",
                "strategy": "smart_money_concepts",
                "description": "Expert in Fair Value Gaps, Break of Structure, and Change of Character patterns",
                "active": len([a for a in active_agents.values() if a.strategy == "smart_money_concepts"])
            }
        ]
    }


@app.get("/position/{symbol}")
async def get_position(symbol: str):
    """
    Get the current open position for a symbol with real-time P&L.

    Returns:
        Position data with calculated P&L based on current price.
    """
    try:
        storage = PositionStorage()
        position = storage.get_open_position(symbol)

        if not position:
            return {"position": None}

        # Get current price from classifier if available
        current_price = None
        if symbol in classifiers:
            classifier = classifiers[symbol]
            if classifier.market_data and symbol in classifier.market_data:
                current_price = classifier.market_data[symbol].get('price')

        # If no current price from classifier, use entry price as fallback
        if current_price is None:
            current_price = position['entry_price']

        # Calculate P&L
        entry_price = position['entry_price']
        quantity = position['quantity']
        side = position['side']

        if side == 'long':
            pnl = (current_price - entry_price) * quantity
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:  # short
            pnl = (entry_price - current_price) * quantity
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Add realized P&L
        realized_pnl = position.get('realized_pnl', 0.0)
        total_pnl = realized_pnl + pnl

        return {
            "position": {
                "id": position['id'],
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "entry_price": entry_price,
                "current_price": current_price,
                "unrealized_pnl": pnl,
                "unrealized_pnl_pct": pnl_pct,
                "realized_pnl": realized_pnl,
                "total_pnl": total_pnl,
                "entry_time": position['entry_time'],
                "status": position['status']
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching position: {str(e)}")


@app.post("/scaleout/{symbol}/cancel")
async def cancel_scaleout(symbol: str):
    """Cancel active scaleout for a symbol."""
    from event_bus import event_bus

    try:
        cancelled = event_bus.cancel_task(symbol, "scaleout")

        if cancelled:
            # Publish cancellation event
            await event_bus.publish(symbol, {
                "type": "scaleout_cancelled",
                "message": "⚠️ SCALEOUT CANCELLED BY USER"
            })
            return {"success": True, "message": "Scaleout cancelled"}
        else:
            return {"success": False, "message": "No active scaleout found"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling scaleout: {str(e)}")


@app.post("/scalein/{symbol}/cancel")
async def cancel_scalein(symbol: str):
    """Cancel active scalein for a symbol."""
    from event_bus import event_bus

    try:
        cancelled = event_bus.cancel_task(symbol, "scalein")

        if cancelled:
            # Publish cancellation event
            await event_bus.publish(symbol, {
                "type": "scalein_cancelled",
                "message": "⚠️ SCALEIN CANCELLED BY USER"
            })
            return {"success": True, "message": "Scalein cancelled"}
        else:
            return {"success": False, "message": "No active scalein found"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling scalein: {str(e)}")


@app.get("/events/{symbol}")
async def get_events(symbol: str, since: str = None, limit: int = 50):
    """
    Get event history for a symbol (for polling-based updates).

    Args:
        symbol: Stock symbol
        since: ISO timestamp to get events after (optional)
        limit: Maximum number of events to return (default 50)

    Returns:
        List of events in chronological order
    """
    from event_bus import event_bus
    from datetime import datetime as dt

    try:
        # Get event history
        events = event_bus.get_history(symbol, limit=limit)

        # Filter by timestamp if 'since' provided
        if since:
            try:
                # Parse and ensure both timestamps are timezone-aware
                since_dt = dt.fromisoformat(since.replace('Z', '+00:00'))

                # Make sure since_dt has timezone
                if since_dt.tzinfo is None:
                    from datetime import timezone
                    since_dt = since_dt.replace(tzinfo=timezone.utc)

                events = [
                    e for e in events
                    if dt.fromisoformat(e['timestamp'].replace('Z', '+00:00')) > since_dt
                ]
            except (ValueError, AttributeError) as e:
                print(f"[Events] Error parsing timestamp: {e}")
                pass  # Invalid timestamp, return all

        return {
            "symbol": symbol,
            "events": events,
            "count": len(events),
            "timestamp": dt.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching events: {str(e)}")


@app.get("/indicators/{symbol}")
async def get_smc_indicators(symbol: str, lookback: int = 200):
    """
    Get BoS (Break of Structure) and CHoCH (Change of Character) indicators for chart display.

    Args:
        symbol: Stock symbol
        lookback: Number of bars to analyze (default 200)

    Returns:
        {
            "bos_levels": [
                {
                    "price": 0.5750,
                    "type": "bullish" or "bearish",
                    "target": 0.5850,
                    "invalidation": 0.5745,
                    "confidence": 7.8,
                    "color": "white",
                    "label": "BoS (bullish)",
                    "formed_at": "2024-01-15T10:30:00",
                    "bars_ago": 15
                }
            ],
            "choch_levels": [
                {
                    "price": 0.5650,
                    "type": "bullish_to_bearish" or "bearish_to_bullish",
                    "target": 0.5720,
                    "invalidation": 0.5645,
                    "confidence": 6.5,
                    "color": "cyan",
                    "label": "CHoCH (reversal)",
                    "formed_at": "2024-01-15T09:45:00",
                    "bars_ago": 25
                }
            ],
            "symbol": "BYND",
            "timestamp": "2024-01-15T11:00:00"
        }
    """
    try:
        # Get classifier for this symbol
        classifier = classifiers.get(symbol)
        if not classifier or not classifier.bar_history:
            return {
                "bos_levels": [],
                "choch_levels": [],
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "message": f"No bar data available for {symbol}"
            }

        # Import SMC indicators
        from smc_indicators import SMCIndicators

        # Create indicator instance and get overlays
        indicators = SMCIndicators()
        overlays = indicators.get_chart_overlays(classifier.bar_history, lookback=lookback)

        # Add metadata
        overlays['symbol'] = symbol
        overlays['timestamp'] = datetime.now().isoformat()
        overlays['bars_available'] = len(classifier.bar_history)

        return overlays

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating indicators: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
