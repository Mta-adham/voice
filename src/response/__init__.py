"""
Response Generation Module for Restaurant Booking Voice Agent.

This module provides dynamic, context-aware response generation using LLM
technology. It creates natural, conversational responses for Alex, the AI
restaurant host, maintaining a consistent personality across all interactions.

Main Components:
    - generator: Core response generation logic
    - prompts: State-specific prompt templates
    - personality: Agent personality definition and constants

Public API:
    - generate_response(): Main function to generate responses
    - generate_response_sync(): Generate response with metadata
    - get_fallback_response(): Get simple fallback responses
    - get_available_states(): List all conversation states
"""

from .generator import (
    generate_response,
    generate_response_sync,
    get_fallback_response,
    ResponseGenerationError,
)
from .prompts import get_available_states, get_state_prompt
from .personality import (
    AGENT_NAME,
    AGENT_ROLE,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_PREFERRED_PROVIDER,
)

__all__ = [
    # Main functions
    "generate_response",
    "generate_response_sync",
    "get_fallback_response",
    "get_available_states",
    "get_state_prompt",
    
    # Exceptions
    "ResponseGenerationError",
    
    # Constants
    "AGENT_NAME",
    "AGENT_ROLE",
    "LLM_TEMPERATURE",
    "LLM_MAX_TOKENS",
    "LLM_PREFERRED_PROVIDER",
]

__version__ = "1.0.0"
