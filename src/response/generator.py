"""
Response Generator - Dynamic, context-aware response generation using LLM.

This module provides the main response generation functionality for the
restaurant booking voice agent. It uses the LLM abstraction layer to generate
natural, conversational responses based on conversation state and context.
"""
from typing import Dict, Any, Optional, List
from datetime import date, time, datetime
from loguru import logger

from ..services.llm_service import llm_chat, LLMError
from .prompts import SYSTEM_PROMPT, get_state_prompt, get_available_states
from .personality import (
    AGENT_NAME,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_PREFERRED_PROVIDER,
)


class ResponseGenerationError(Exception):
    """Exception raised when response generation fails."""
    pass


def _format_collected_info(context: Dict[str, Any]) -> str:
    """
    Format already-collected information for inclusion in prompts.
    
    Args:
        context: Dictionary containing conversation context
        
    Returns:
        Formatted string describing collected information
    """
    collected = []
    
    if context.get("date"):
        date_val = context["date"]
        if isinstance(date_val, date):
            collected.append(f"Date: {date_val.strftime('%A, %B %d, %Y')}")
        else:
            collected.append(f"Date: {date_val}")
    
    if context.get("time"):
        time_val = context["time"]
        if isinstance(time_val, time):
            collected.append(f"Time: {time_val.strftime('%I:%M %p').lstrip('0')}")
        else:
            collected.append(f"Time: {time_val}")
    
    if context.get("party_size"):
        party_size = context["party_size"]
        collected.append(f"Party size: {party_size} {'person' if party_size == 1 else 'people'}")
    
    if context.get("name"):
        collected.append(f"Name: {context['name']}")
    
    if context.get("phone"):
        collected.append(f"Phone: {context['phone']}")
    
    if not collected:
        return "None yet"
    
    return ", ".join(collected)


def _format_booking_details(data: Dict[str, Any]) -> str:
    """
    Format complete booking details for confirmation/completion messages.
    
    Args:
        data: Dictionary containing booking information
        
    Returns:
        Formatted string with all booking details
    """
    details = []
    
    # Date
    if data.get("date"):
        date_val = data["date"]
        if isinstance(date_val, date):
            details.append(f"Date: {date_val.strftime('%A, %B %d, %Y')}")
        else:
            details.append(f"Date: {date_val}")
    
    # Time
    if data.get("time"):
        time_val = data["time"]
        if isinstance(time_val, time):
            details.append(f"Time: {time_val.strftime('%I:%M %p').lstrip('0')}")
        else:
            details.append(f"Time: {time_val}")
    
    # Party size
    if data.get("party_size"):
        party_size = data["party_size"]
        details.append(f"Party size: {party_size} {'person' if party_size == 1 else 'people'}")
    
    # Name
    if data.get("name"):
        details.append(f"Name: {data['name']}")
    
    # Phone
    if data.get("phone"):
        details.append(f"Phone: {data['phone']}")
    
    return "\n".join(details)


def _format_time_slots(slots: List[Any]) -> str:
    """
    Format available time slots for presentation.
    
    Args:
        slots: List of available time slot objects or strings
        
    Returns:
        Formatted string presenting time options
    """
    if not slots:
        return "No slots available"
    
    formatted_slots = []
    
    for slot in slots[:5]:  # Limit to 5 slots for voice clarity
        if isinstance(slot, dict):
            time_val = slot.get("time")
        elif hasattr(slot, "time"):
            time_val = slot.time
        else:
            time_val = str(slot)
        
        # Format time for spoken output
        if isinstance(time_val, time):
            formatted_time = time_val.strftime('%I:%M %p').lstrip('0')
        else:
            formatted_time = str(time_val)
        
        formatted_slots.append(formatted_time)
    
    if len(slots) > 5:
        return f"Available times: {', '.join(formatted_slots)}, and {len(slots) - 5} more options"
    else:
        return f"Available times: {', '.join(formatted_slots)}"


def _build_prompt_context(state: str, context: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, str]:
    """
    Build the context dictionary for prompt template formatting.
    
    Args:
        state: Current conversation state
        context: Conversation context with collected information
        data: Additional data specific to current state
        
    Returns:
        Dictionary with formatted context for prompt template
    """
    # Base context
    prompt_context = {
        "context": context.get("raw_context", "Conversation in progress"),
        "collected_info": _format_collected_info(context),
    }
    
    # Add state-specific data
    if state == "presenting_availability":
        if "available_slots" in data:
            prompt_context["available_slots"] = _format_time_slots(data["available_slots"])
        else:
            prompt_context["available_slots"] = "No specific slots provided"
    
    elif state in ["confirming", "completed"]:
        prompt_context["booking_details"] = _format_booking_details(
            data.get("booking_details", context)
        )
    
    elif state == "no_availability":
        prompt_context["alternatives"] = data.get("alternatives", "Other dates or times may be available")
    
    elif state == "invalid_date":
        prompt_context["issue"] = data.get("issue", "Invalid date provided")
    
    elif state == "party_too_large":
        prompt_context["party_size"] = data.get("party_size", "unknown")
        prompt_context["max_party_size"] = data.get("max_party_size", "8")
    
    elif state == "clarification":
        prompt_context["clarification_needed"] = data.get("clarification_needed", "the information provided")
    
    elif state == "acknowledge_multiple_info":
        prompt_context["received_info"] = data.get("received_info", "multiple details")
        prompt_context["needed_info"] = data.get("needed_info", "remaining information")
    
    return prompt_context


def generate_response(
    state: str,
    context: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    provider: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Generate a natural, context-aware response for the given conversation state.
    
    This is the main entry point for response generation. It takes the current
    conversation state and context, builds an appropriate prompt, and uses the
    LLM to generate a natural response that fits Alex's personality.
    
    Args:
        state: Current conversation state (e.g., 'greeting', 'collecting_date')
        context: Dictionary containing conversation context and collected information.
                Expected keys: date, time, party_size, name, phone, raw_context
        data: Additional state-specific data (e.g., available_slots, error details)
        provider: LLM provider to use (defaults to LLM_PREFERRED_PROVIDER)
        temperature: Sampling temperature (defaults to LLM_TEMPERATURE)
        max_tokens: Maximum tokens to generate (defaults to LLM_MAX_TOKENS)
        
    Returns:
        Generated response string suitable for voice output
        
    Raises:
        ResponseGenerationError: If response generation fails
        ValueError: If state is invalid
        
    Examples:
        >>> # Generate initial greeting
        >>> response = generate_response("greeting")
        >>> print(response)
        "Hello! This is Alex from our restaurant. I'd be happy to help you make a reservation."
        
        >>> # Request date with some context
        >>> context = {"party_size": 4}
        >>> response = generate_response("collecting_date", context=context)
        >>> print(response)
        "Great! For a party of four, what date were you thinking of?"
        
        >>> # Present available time slots
        >>> context = {"date": date(2024, 12, 25), "party_size": 4}
        >>> data = {"available_slots": [time(18, 0), time(18, 30), time(19, 0)]}
        >>> response = generate_response("presenting_availability", context=context, data=data)
    """
    # Validate state
    if state not in get_available_states():
        raise ValueError(
            f"Invalid conversation state: {state}. "
            f"Valid states: {', '.join(get_available_states())}"
        )
    
    # Initialize defaults
    context = context or {}
    data = data or {}
    provider = provider or LLM_PREFERRED_PROVIDER
    temperature = temperature if temperature is not None else LLM_TEMPERATURE
    max_tokens = max_tokens if max_tokens is not None else LLM_MAX_TOKENS
    
    logger.info(
        f"Generating response | state: {state} | "
        f"context_keys: {list(context.keys())} | "
        f"provider: {provider}"
    )
    
    try:
        # Build the state-specific prompt
        prompt_context = _build_prompt_context(state, context, data)
        state_prompt = get_state_prompt(state, **prompt_context)
        
        logger.debug(f"State prompt built | length: {len(state_prompt)} chars")
        
        # Call LLM to generate response
        messages = [{"role": "user", "content": state_prompt}]
        
        llm_response = llm_chat(
            provider=provider,
            messages=messages,
            system_prompt=SYSTEM_PROMPT,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        response_text = llm_response["content"].strip()
        
        logger.info(
            f"Response generated | state: {state} | "
            f"length: {len(response_text)} chars | "
            f"tokens: {llm_response.get('tokens_used', 'unknown')} | "
            f"provider: {llm_response.get('provider', provider)}"
        )
        
        logger.debug(f"Generated response: {response_text[:100]}...")
        
        return response_text
        
    except LLMError as e:
        logger.error(f"LLM error during response generation: {e}")
        raise ResponseGenerationError(
            f"Failed to generate response for state '{state}': {str(e)}"
        ) from e
    
    except Exception as e:
        logger.error(f"Unexpected error during response generation: {e}")
        raise ResponseGenerationError(
            f"Unexpected error generating response for state '{state}': {str(e)}"
        ) from e


def generate_response_sync(
    state: str,
    context: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate response and return with metadata.
    
    This is a convenience wrapper around generate_response() that returns
    both the response text and metadata about the generation.
    
    Args:
        state: Current conversation state
        context: Conversation context dictionary
        data: Additional state-specific data
        **kwargs: Additional arguments passed to generate_response
        
    Returns:
        Dictionary containing:
            - response (str): The generated response text
            - state (str): The conversation state used
            - success (bool): Whether generation succeeded
            - error (str, optional): Error message if failed
            
    Examples:
        >>> result = generate_response_sync("greeting")
        >>> if result["success"]:
        ...     print(result["response"])
        ... else:
        ...     print(f"Error: {result['error']}")
    """
    try:
        response = generate_response(state, context, data, **kwargs)
        return {
            "response": response,
            "state": state,
            "success": True,
        }
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return {
            "response": "",
            "state": state,
            "success": False,
            "error": str(e),
        }


def get_fallback_response(state: str) -> str:
    """
    Get a simple fallback response for a given state.
    
    Used when LLM generation fails and we need a basic response to keep
    the conversation going.
    
    Args:
        state: Conversation state
        
    Returns:
        Basic fallback response string
    """
    fallbacks = {
        "greeting": f"Hello! This is {AGENT_NAME}. I can help you make a reservation today.",
        "collecting_date": "What date would you like to make your reservation for?",
        "collecting_time": "What time works best for you?",
        "collecting_party_size": "How many people will be dining with us?",
        "collecting_name": "Can I get your name for the reservation?",
        "collecting_phone": "And a phone number where we can reach you?",
        "presenting_availability": "We have several time slots available. Which would you prefer?",
        "no_availability": "I'm sorry, we don't have availability at that time. Can I suggest an alternative?",
        "invalid_date": "I'm sorry, that date doesn't work. Could you provide a different date?",
        "party_too_large": "I apologize, but that party size exceeds our maximum. Please call us directly for large parties.",
        "confirming": "Let me confirm those details. Does everything sound correct?",
        "completed": "Perfect! Your reservation is confirmed. We look forward to seeing you!",
        "goodbye": "Thank you for calling! Have a wonderful day.",
        "clarification": "I'm sorry, could you repeat that?",
    }
    
    return fallbacks.get(state, "I'm here to help with your reservation.")
