"""
Event Bus - Pub/Sub System for Real-Time Chat Updates
======================================================
Allows background workers to publish events that get delivered to active chat sessions.

Usage:
    # Subscribe to events
    event_bus.subscribe(symbol, conversation_id, websocket)

    # Publish events from anywhere
    event_bus.publish(symbol, {
        "type": "scaleout_progress",
        "message": "✓ Sold 500 @ $0.65 | P&L: +$125.00",
        "data": {...}
    })
"""

import asyncio
from typing import Dict, Set, Callable, Any
from datetime import datetime
import json


class EventBus:
    """Global pub-sub event bus for real-time updates."""

    def __init__(self):
        # Symbol -> {conversation_id: websocket}
        self.subscribers: Dict[str, Dict[str, Any]] = {}

        # Symbol -> active tasks
        self.active_tasks: Dict[str, asyncio.Task] = {}

        # Event history for replay (last 50 events per symbol)
        self.event_history: Dict[str, list] = {}

    def subscribe(self, symbol: str, conversation_id: str, websocket):
        """Subscribe to events for a symbol."""
        if symbol not in self.subscribers:
            self.subscribers[symbol] = {}

        self.subscribers[symbol][conversation_id] = {
            'websocket': websocket,
            'subscribed_at': datetime.now().isoformat()
        }

        print(f"[EventBus] Subscribed: {conversation_id} → {symbol}")

    def unsubscribe(self, symbol: str, conversation_id: str):
        """Unsubscribe from events."""
        if symbol in self.subscribers and conversation_id in self.subscribers[symbol]:
            del self.subscribers[symbol][conversation_id]
            print(f"[EventBus] Unsubscribed: {conversation_id} → {symbol}")

            if not self.subscribers[symbol]:
                del self.subscribers[symbol]

    async def publish(self, symbol: str, event: Dict[str, Any]):
        """
        Publish an event to all subscribers of a symbol.

        Event format:
        {
            "type": "scaleout_progress",
            "message": "✓ Sold 500 @ $0.65",
            "data": {...},
            "timestamp": "2025-10-26T14:30:00"
        }
        """
        event['timestamp'] = datetime.now().isoformat()

        # Store in history
        if symbol not in self.event_history:
            self.event_history[symbol] = []
        self.event_history[symbol].append(event)

        # Keep only last 50 events
        if len(self.event_history[symbol]) > 50:
            self.event_history[symbol] = self.event_history[symbol][-50:]

        # Publish to all subscribers
        if symbol in self.subscribers:
            dead_subscribers = []

            for conversation_id, sub_info in self.subscribers[symbol].items():
                try:
                    websocket = sub_info['websocket']
                    await websocket.send_json({
                        "type": "event",
                        "event": event
                    })
                    print(f"[EventBus] Published to {conversation_id}: {event['type']}")

                except Exception as e:
                    print(f"[EventBus] Failed to publish to {conversation_id}: {e}")
                    dead_subscribers.append(conversation_id)

            # Clean up dead subscribers
            for conv_id in dead_subscribers:
                self.unsubscribe(symbol, conv_id)

    def get_history(self, symbol: str, limit: int = 10) -> list:
        """Get recent event history for a symbol."""
        if symbol not in self.event_history:
            return []
        return self.event_history[symbol][-limit:]

    def register_task(self, symbol: str, task_name: str, task: asyncio.Task):
        """Register an active background task."""
        key = f"{symbol}:{task_name}"
        self.active_tasks[key] = task
        print(f"[EventBus] Registered task: {key}")

    def get_task(self, symbol: str, task_name: str) -> asyncio.Task:
        """Get an active task."""
        key = f"{symbol}:{task_name}"
        return self.active_tasks.get(key)

    def cancel_task(self, symbol: str, task_name: str):
        """Cancel a background task."""
        key = f"{symbol}:{task_name}"
        task = self.active_tasks.get(key)

        if task:
            task.cancel()
            del self.active_tasks[key]
            print(f"[EventBus] Cancelled task: {key}")
            return True
        return False

    def list_active_tasks(self, symbol: str = None) -> Dict[str, Any]:
        """List all active tasks, optionally filtered by symbol."""
        if symbol:
            prefix = f"{symbol}:"
            return {k: v for k, v in self.active_tasks.items() if k.startswith(prefix)}
        return dict(self.active_tasks)


# Global singleton
event_bus = EventBus()
