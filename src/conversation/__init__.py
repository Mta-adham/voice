"""
Conversation package for managing booking conversation state and context.

This package provides:
- ConversationState: Enum for conversation states
- ConversationContext: Pydantic model for storing conversation data
- ConversationStateManager: Main class for managing state transitions and context
"""

from .states import ConversationState
from .context import ConversationContext
from .state_manager import ConversationStateManager

__all__ = [
    "ConversationState",
    "ConversationContext",
    "ConversationStateManager",
]
