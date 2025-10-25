"""
JuiceBot AI Service

FastAPI server providing AI-powered trading assistance.
Runs on port 8002.
"""

import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from pathlib import Path
from dotenv import load_dotenv

from agents.smc_agent import SMCAgent
from fast_classifier import TradingClassifier
from websocket_client import BarDataClient

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
    # Get or create classifier for this symbol
    if msg.symbol not in classifiers:
        classifiers[msg.symbol] = TradingClassifier()

    classifier = classifiers[msg.symbol]

    # Auto-subscribe to WebSocket bar data for this symbol
    if ws_client and ws_client.running and msg.symbol not in ws_client.subscribed_symbols:
        await ws_client.subscribe(msg.symbol)

    # Try fast-path first
    fast_response = classifier.classify(msg.message, msg.symbol)
    if fast_response:
        return ChatResponse(
            response=fast_response.text,
            conversation_id=msg.conversation_id or f"fast_{msg.symbol}",
            timestamp=datetime.now().isoformat()
        )

    # Slow path - use LLM
    conversation_id = msg.conversation_id or f"conv_{msg.symbol}_{datetime.now().timestamp()}"

    if conversation_id not in active_agents:
        active_agents[conversation_id] = SMCAgent()

    agent = active_agents[conversation_id]

    try:
        # Get bar history from classifier
        classifier = classifiers.get(msg.symbol)
        bar_history = classifier.bar_history if classifier else []

        # Analyze and respond (passing bar_history to tools)
        response = await agent.analyze(msg.symbol, msg.message, bar_history)

        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
