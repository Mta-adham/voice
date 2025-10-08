# Response Generation Module

Dynamic, context-aware response generation for Alex, the AI restaurant booking assistant.

## Overview

This module generates natural, conversational responses using LLM technology while maintaining a consistent personality throughout the booking conversation. Responses are optimized for voice interaction and adapt based on conversation state and context.

## Files

- **`generator.py`** - Core response generation logic with `generate_response()` function
- **`prompts.py`** - System prompt and state-specific prompt templates (15 states)
- **`personality.py`** - Agent personality definition, tone guidelines, and constants
- **`__init__.py`** - Public API exports

## Quick Start

```python
from response import generate_response

# Generate a greeting
response = generate_response("greeting")

# Generate with context
context = {"date": "December 25, 2024", "party_size": 4}
response = generate_response("collecting_time", context=context)
```

## Features

✅ **Context-Aware**: References previously collected booking information  
✅ **Voice-Optimized**: Short sentences, natural phrasing, spoken time formats  
✅ **Personality-Consistent**: Professional yet warm tone throughout  
✅ **State-Based**: 15 different conversation states supported  
✅ **Multi-Provider**: Works with OpenAI, Gemini, and Claude  
✅ **Error Handling**: Fallback responses when LLM fails  
✅ **Logging**: Comprehensive logging for debugging and monitoring  

## Supported States

1. `greeting` - Initial welcome
2. `collecting_date` - Ask for date
3. `collecting_time` - Ask for time
4. `collecting_party_size` - Ask for party size
5. `collecting_name` - Ask for name
6. `collecting_phone` - Ask for phone number
7. `presenting_availability` - Show available slots
8. `no_availability` - Handle no availability
9. `invalid_date` - Handle invalid dates
10. `party_too_large` - Handle oversized parties
11. `confirming` - Confirm booking details
12. `completed` - Booking success message
13. `goodbye` - Close conversation
14. `clarification` - Ask for clarification
15. `acknowledge_multiple_info` - Acknowledge multiple inputs

## API Reference

### `generate_response(state, context=None, data=None, provider=None, temperature=None, max_tokens=None)`

Generate a natural response for the given conversation state.

**Parameters:**
- `state` (str): Conversation state (required)
- `context` (dict): Collected booking information (optional)
- `data` (dict): State-specific additional data (optional)
- `provider` (str): LLM provider - "openai", "gemini", or "claude" (optional)
- `temperature` (float): Sampling temperature, default 0.7 (optional)
- `max_tokens` (int): Max tokens to generate, default 150 (optional)

**Returns:** Generated response string

**Raises:** `ResponseGenerationError`, `ValueError`

### `generate_response_sync(state, context=None, data=None, **kwargs)`

Generate response and return with metadata.

**Returns:** Dictionary with `response`, `state`, `success`, and optional `error`

### `get_fallback_response(state)`

Get a simple fallback response when LLM fails.

**Returns:** Basic fallback response string

### `get_available_states()`

Get list of all supported conversation states.

**Returns:** List of state names

## Context Dictionary Format

```python
context = {
    "date": date(2024, 12, 25),      # or string
    "time": time(18, 30),             # or string
    "party_size": 4,                  # integer
    "name": "John Doe",               # string
    "phone": "+1234567890",           # string
    "raw_context": "optional text"    # string
}
```

## Data Dictionary Examples

### For `presenting_availability`:
```python
data = {
    "available_slots": [time(18, 0), time(18, 30), time(19, 0)]
}
```

### For `confirming` or `completed`:
```python
data = {
    "booking_details": {
        "date": date(2024, 12, 25),
        "time": time(18, 30),
        "party_size": 4,
        "name": "John Doe",
        "phone": "+1234567890"
    }
}
```

### For `no_availability`:
```python
data = {
    "alternatives": "Tomorrow at 7 PM or Friday at 6 PM"
}
```

## Configuration

### Environment Variables

```bash
# Set at least one LLM provider API key
OPENAI_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

### Default Settings

- **Temperature**: 0.7 (adds natural variation)
- **Max Tokens**: 150 (keeps responses concise)
- **Preferred Provider**: "openai" (can be changed)

## Agent Personality

**Name**: Alex  
**Role**: Restaurant Host  
**Tone**: Professional yet warm and friendly

### Key Characteristics
- Welcoming and makes guests feel valued
- Patient and helpful with clarifications
- Efficient without rushing
- Natural and conversational, never robotic

### Response Style
- 1-3 sentences typically
- Clear and concise
- Voice-friendly phrasing
- References collected information
- Ends with clear prompts for action

## Examples

See `examples/response_generation_example.py` for comprehensive usage examples.

## Error Handling

```python
from response import ResponseGenerationError, get_fallback_response

try:
    response = generate_response("greeting")
except ResponseGenerationError as e:
    # Use fallback
    response = get_fallback_response("greeting")
```

## Logging

Uses `loguru` for logging:
- **INFO**: Successful generations
- **DEBUG**: Prompt details and response previews
- **ERROR**: Failures and exceptions

## Testing

```python
from response import generate_response, get_available_states

# Test greeting generation
response = generate_response("greeting")
assert "Alex" in response or "alex" in response.lower()

# Test all states have fallbacks
for state in get_available_states():
    fallback = get_fallback_response(state)
    assert len(fallback) > 0
```

## Dependencies

- `services.llm_service` - LLM abstraction layer (required)
- `loguru` - Logging (required)
- Python 3.8+ with `datetime` and `typing` modules

## Documentation

For complete documentation, see `docs/RESPONSE_GENERATION.md`

## Version

1.0.0 - Initial release
