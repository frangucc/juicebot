"""
Conversation State Manager
==========================
Tracks conversation state for interactive multi-turn commands.

Examples:
- Scaleout: User types "scaleout" → Bot asks "1, 2, or 3?" → User replies "1" → Bot executes fast scaleout
- Close: User types "close" → Bot asks "market or price?" → User replies "market" → Bot closes at market
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class ConversationState:
    """Manages stateful conversations for interactive commands."""

    def __init__(self):
        # conversation_id -> state data
        self.states: Dict[str, Dict[str, Any]] = {}

        # Timeout for states (5 minutes)
        self.timeout_seconds = 300

    def set_state(self, conversation_id: str, symbol: str, command: str, context: Dict[str, Any] = None):
        """Set conversation state for interactive command."""
        self.states[conversation_id] = {
            'symbol': symbol,
            'command': command,
            'context': context or {},
            'created_at': datetime.now()
        }

    def get_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get current conversation state."""
        state = self.states.get(conversation_id)

        if not state:
            return None

        # Check timeout
        if datetime.now() - state['created_at'] > timedelta(seconds=self.timeout_seconds):
            self.clear_state(conversation_id)
            return None

        return state

    def clear_state(self, conversation_id: str):
        """Clear conversation state."""
        if conversation_id in self.states:
            del self.states[conversation_id]

    def is_waiting_for_input(self, conversation_id: str, command: str) -> bool:
        """Check if conversation is waiting for user input for a specific command."""
        state = self.get_state(conversation_id)
        return state and state['command'] == command


# Global singleton
conversation_state = ConversationState()
