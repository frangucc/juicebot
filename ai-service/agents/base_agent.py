"""
Base Agent Class

All JuiceBot agents inherit from this base class.
"""

from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class Message:
    """Represents a conversation message."""

    def __init__(self, role: str, content: str):
        self.role = role  # 'user' or 'assistant'
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class BaseAgent(ABC):
    """Base class for all trading agents."""

    def __init__(self, name: str, strategy: str):
        self.name = name
        self.strategy = strategy
        self.conversation_history: List[Message] = []

    @abstractmethod
    async def analyze(self, symbol: str, user_message: str) -> str:
        """
        Analyze market data and respond to user message.

        Args:
            symbol: Stock symbol being analyzed
            user_message: User's question or request

        Returns:
            Agent's response
        """
        pass

    @abstractmethod
    def get_system_prompt(self, symbol: str) -> str:
        """
        Get the system prompt for this agent.

        Args:
            symbol: Stock symbol for context

        Returns:
            System prompt text
        """
        pass

    def add_message(self, role: str, content: str):
        """Add a message to conversation history."""
        self.conversation_history.append(Message(role, content))

    def get_conversation_messages(self) -> List[Dict[str, str]]:
        """Get conversation history as list of dicts for API."""
        return [msg.to_dict() for msg in self.conversation_history]

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
