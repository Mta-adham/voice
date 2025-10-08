# Response Generation System

## Overview

The Response Generation System creates dynamic, context-aware responses for Alex, the AI restaurant booking assistant. It uses LLM technology to generate natural, conversational responses that maintain a consistent personality throughout the booking flow.

## Features

- **Context-Aware**: References previously collected information in responses
- **Natural Language**: Generates conversational, non-robotic responses
- **Voice-Optimized**: Responses are designed to sound natural when spoken aloud
- **State-Based**: Different prompts for each conversation state
- **Multi-Provider**: Works with OpenAI, Google Gemini, and Anthropic Claude
- **Error Handling**: Graceful fallbacks when LLM generation fails
- **Comprehensive Logging**: Tracks all generated responses for debugging

## Agent Personality

**Name**: Alex  
**Role**: Professional restaurant host  
**Tone**: Warm, friendly, and helpful while maintaining professionalism

### Key Traits
- Welcoming and makes guests feel valued
- Patient and helpful with clarifications
- Efficient without rushing
- Enthusiastic about helping guests
- Natural and conversational

## Installation

The response generation system is part of the main application. Ensure you have:

```python
# Required dependencies (in requirements.txt)
openai
google-generativeai
anthropic
loguru
```

## Quick Start

### Basic Usage

```python
from src.response import generate_response

# Generate a greeting
response = generate_response("greeting")
print(response)
# Output: "Hello! This is Alex from our restaurant. I'd be happy to help you make a reservation today."
```

### With Context

```python
from datetime import date

# Ask for time with date already collected
context = {
    "date": date(2024, 12, 25),
    "party_size": 4
}

response = generate_response("collecting_time", context=context)
print(response)
# Output: "Perfect! For December 25th, what time works best for your party of four?"
```

### Present Available Slots

```python
from datetime import date, time

context = {
    "date": date(2024, 12, 25),
    "party_size": 4
}

data = {
    "available_slots": [
        time(18, 0),
        time(18, 30),
        time(19, 0),
        time(19, 30)
    ]
}

response = generate_response("presenting_availability", context=context, data=data)
print(response)
# Output: "Great! For December 25th, we have availability at 6:00 PM, 6:30 PM, 7:00 PM, and 7:30 PM. Which time works best for you?"
```

### Handle Errors

```python
data = {
    "issue": "Date is in the past"
}

response = generate_response("invalid_date", data=data)
print(response)
# Output: "I apologize, but that date has already passed. We can book reservations for today or any future date up to 30 days in advance. What date would work for you?"
```

## Available States

The system supports the following conversation states:

1. **greeting** - Initial welcome message
2. **collecting_date** - Ask for reservation date
3. **collecting_time** - Ask for reservation time
4. **collecting_party_size** - Ask for number of people
5. **collecting_name** - Ask for customer name
6. **collecting_phone** - Ask for phone number
7. **presenting_availability** - Present available time slots
8. **no_availability** - Handle no availability scenario
9. **invalid_date** - Handle invalid date errors
10. **party_too_large** - Handle party size exceeding maximum
11. **confirming** - Confirm all booking details
12. **completed** - Booking successfully created
13. **goodbye** - Close the conversation
14. **clarification** - Ask for clarification
15. **acknowledge_multiple_info** - Acknowledge multiple pieces of info at once

Get the full list programmatically:

```python
from src.response import get_available_states

states = get_available_states()
print(states)
```

## Advanced Usage

### Custom LLM Provider

```python
# Use a specific LLM provider
response = generate_response(
    "greeting",
    provider="claude",  # or "openai", "gemini"
    temperature=0.8,    # Higher for more variation
    max_tokens=200      # Longer responses
)
```

### Generate with Metadata

```python
from src.response import generate_response_sync

result = generate_response_sync("greeting")

if result["success"]:
    print(f"Response: {result['response']}")
else:
    print(f"Error: {result['error']}")
```

### Fallback Responses

```python
from src.response import get_fallback_response

# Get a simple fallback when LLM fails
fallback = get_fallback_response("greeting")
print(fallback)
# Output: "Hello! This is Alex. I can help you make a reservation today."
```

## Context Dictionary

The `context` dictionary should contain information already collected:

```python
context = {
    "date": date(2024, 12, 25),           # Booking date (date object or string)
    "time": time(18, 30),                  # Booking time (time object or string)
    "party_size": 4,                       # Number of people (int)
    "name": "John Doe",                    # Customer name (string)
    "phone": "+1234567890",                # Customer phone (string)
    "raw_context": "Additional context"    # Optional free-form context
}
```

## Data Dictionary

The `data` dictionary provides state-specific information:

### For `presenting_availability`
```python
data = {
    "available_slots": [time(18, 0), time(18, 30), time(19, 0)]
}
```

### For `no_availability`
```python
data = {
    "alternatives": "We have availability tomorrow or on Friday"
}
```

### For `invalid_date`
```python
data = {
    "issue": "Date is beyond our 30-day booking window"
}
```

### For `party_too_large`
```python
data = {
    "party_size": 12,
    "max_party_size": 8
}
```

### For `confirming` or `completed`
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

## Response Characteristics

### Length
- **Target**: 1-3 sentences
- **Maximum tokens**: 150 (configurable)
- Concise and to the point

### Voice Optimization
- Short, clear sentences
- Natural contractions (I'm, we're)
- Spoken time format ("7 PM" not "19:00")
- Numbers spelled out in context ("party of four")
- No complex punctuation

### Tone Progression
- **Early conversation**: Professional and welcoming
- **Mid conversation**: Warm and conversational
- **Confirmation**: Clear and reassuring
- **Closing**: Warm and appreciative

## Configuration

### Environment Variables

Set your LLM provider API keys:

```bash
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_claude_key
```

### Default Settings

Override defaults by importing from `personality.py`:

```python
from src.response.personality import (
    LLM_TEMPERATURE,      # Default: 0.7
    LLM_MAX_TOKENS,       # Default: 150
    LLM_PREFERRED_PROVIDER # Default: "openai"
)
```

## Error Handling

The system includes comprehensive error handling:

```python
from src.response import ResponseGenerationError

try:
    response = generate_response("greeting")
except ResponseGenerationError as e:
    print(f"Generation failed: {e}")
    # Use fallback
    response = get_fallback_response("greeting")
except ValueError as e:
    print(f"Invalid state: {e}")
```

## Logging

All response generation is logged using `loguru`:

```python
# INFO level: Successful generations
# DEBUG level: Prompt details and response previews
# ERROR level: Failures and exceptions

# View logs
logger.info("Response generated | state: greeting | length: 67 chars")
```

## Examples

### Complete Booking Flow

```python
from datetime import date, time
from src.response import generate_response

# 1. Greeting
response = generate_response("greeting")
# "Hello! This is Alex from our restaurant. I'd be happy to help you make a reservation."

# 2. Collect date
response = generate_response("collecting_date")
# "What date would you like to dine with us?"

# 3. Collect time (with date context)
context = {"date": date(2024, 12, 25)}
response = generate_response("collecting_time", context=context)
# "Perfect! For December 25th, what time works best for you?"

# 4. Collect party size (with date and time)
context = {"date": date(2024, 12, 25), "time": time(18, 30)}
response = generate_response("collecting_party_size", context=context)
# "Great! And how many people will be dining at 6:30 PM on December 25th?"

# 5. Present availability
context = {"date": date(2024, 12, 25), "party_size": 4}
data = {"available_slots": [time(18, 0), time(18, 30), time(19, 0)]}
response = generate_response("presenting_availability", context=context, data=data)
# "We have availability for four at 6:00 PM, 6:30 PM, and 7:00 PM. Which would you prefer?"

# 6. Collect name
context = {"date": date(2024, 12, 25), "time": time(18, 30), "party_size": 4}
response = generate_response("collecting_name", context=context)
# "Excellent choice! Can I get your name for the reservation?"

# 7. Collect phone
context = {"date": date(2024, 12, 25), "time": time(18, 30), "party_size": 4, "name": "John"}
response = generate_response("collecting_phone", context=context)
# "Thank you, John! And what's the best phone number to reach you?"

# 8. Confirm details
data = {
    "booking_details": {
        "date": date(2024, 12, 25),
        "time": time(18, 30),
        "party_size": 4,
        "name": "John Doe",
        "phone": "+1234567890"
    }
}
response = generate_response("confirming", data=data)
# "Let me confirm: I have you down for Tuesday, December 25th at 6:30 PM for four people under the name John Doe. Is that correct?"

# 9. Complete booking
response = generate_response("completed", data=data)
# "Perfect! Your reservation is confirmed for December 25th at 6:30 PM. We look forward to seeing you, John!"

# 10. Say goodbye
response = generate_response("goodbye")
# "Thank you for calling! Have a wonderful day!"
```

## Testing

Test the system with different states and contexts:

```python
import pytest
from src.response import generate_response, get_fallback_response

def test_greeting():
    response = generate_response("greeting")
    assert len(response) > 0
    assert "Alex" in response or "alex" in response.lower()

def test_context_awareness():
    context = {"party_size": 4}
    response = generate_response("collecting_date", context=context)
    assert "4" in response or "four" in response.lower()

def test_fallback():
    fallback = get_fallback_response("greeting")
    assert "Alex" in fallback
```

## Best Practices

1. **Always provide context**: Include previously collected information
2. **Use appropriate states**: Select the right state for each conversation point
3. **Handle errors gracefully**: Always have fallback responses ready
4. **Log generation**: Monitor responses for quality and debugging
5. **Test with TTS**: Verify responses sound natural when spoken
6. **Limit slot presentations**: Don't overwhelm with too many options
7. **Reference customer name**: Use it when appropriate for personalization
8. **Be consistent**: Let the system maintain Alex's personality

## Troubleshooting

### Response too long
- Reduce `max_tokens` parameter
- Responses are designed to be concise by default

### Response sounds robotic
- The system uses temperature=0.7 for natural variation
- Check that context is being provided properly
- Review the prompt templates in `prompts.py`

### LLM errors
- Verify API keys are set in environment variables
- Check rate limits with your LLM provider
- Use fallback responses as backup
- Try a different provider

### Missing context
- Ensure context dictionary includes relevant fields
- Context fields are optional but improve quality
- Check that date/time objects are properly formatted

## Architecture

```
src/response/
├── __init__.py          # Public API exports
├── generator.py         # Core response generation logic
├── prompts.py          # State-specific prompt templates
└── personality.py      # Agent personality definition
```

### Dependencies
- `src.services.llm_service` - LLM abstraction layer
- `loguru` - Logging
- Python standard library (datetime, typing)

## Future Enhancements

Potential improvements:
- Response caching for common states
- Multi-language support
- Emotion detection and adaptation
- Response quality scoring
- A/B testing different prompts
- Streaming responses for real-time feedback

## Support

For issues or questions:
1. Check logs for error messages
2. Review the conversation state and context
3. Test with fallback responses
4. Verify LLM provider connectivity
5. Consult the example code above

---

**Version**: 1.0.0  
**Last Updated**: 2024
