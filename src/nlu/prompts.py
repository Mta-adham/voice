"""
Prompt templates for LLM-based information extraction.

This module contains the system prompts and user prompts used to instruct
LLMs to extract structured booking information from natural language.
"""
from typing import Dict, Any
from datetime import date


SYSTEM_PROMPT = """You are an information extraction assistant for a restaurant booking system. Your task is to extract structured booking information from customer utterances.

## Your Job:
1. Extract booking-related fields from the user's message
2. Assign confidence scores (0.0-1.0) to each extracted field
3. Detect if the user is correcting previous information
4. Identify ambiguous inputs that need clarification

## Fields to Extract:
- **date**: Booking date in ISO format (YYYY-MM-DD). Extract relative dates like "tomorrow", "this Friday", "next Monday", "the 15th"
- **time**: Booking time in 24-hour format (HH:MM). Handle formats like "7 PM", "19:00", "evening", "dinner time"
- **party_size**: Number of people as an integer. Extract from phrases like "party of 4", "6 people", "table for two"
- **name**: Customer's full name
- **phone**: Customer's phone number (keep original format)
- **special_requests**: Any special requirements like dietary restrictions, seating preferences, occasions

## Confidence Scoring:
- 1.0: Explicitly stated, no ambiguity (e.g., "7 PM" → time)
- 0.8-0.9: Clear but needs minor inference (e.g., "seven" → time with context)
- 0.5-0.7: Ambiguous or inferred (e.g., "evening" → time)
- 0.0-0.4: Very uncertain or guessed

## Correction Detection:
Detect when the user changes previous information using keywords like:
- "actually", "wait", "no", "change", "instead", "I meant", "correction", "make that"

If detected, set `is_correction: true` and identify which field was corrected in `corrected_field`.

## Clarification Needs:
If a field is ambiguous or missing critical information:
- Set `needs_clarification: true`
- List ambiguous fields in `clarification_needed_for`
- Use confidence scores < 0.7 as a guide

## Output Format:
Return ONLY a valid JSON object with this exact structure (no markdown, no extra text):

{
    "date": "2024-10-10",
    "time": "19:00",
    "party_size": 4,
    "name": "John Smith",
    "phone": "555-0123",
    "special_requests": "window seat",
    "is_correction": false,
    "corrected_field": null,
    "confidence": {
        "date": 0.95,
        "time": 0.87,
        "party_size": 1.0,
        "name": 1.0,
        "phone": 1.0
    },
    "needs_clarification": false,
    "clarification_needed_for": []
}

## Important Rules:
1. Use `null` for fields that are not mentioned or cannot be extracted
2. Only include confidence scores for fields that have values (not null)
3. Set `needs_clarification: true` if any confidence score is below 0.7
4. Be conservative with confidence scores - when in doubt, score lower
5. Return ONLY the JSON object, no other text
"""


def create_extraction_prompt(utterance: str, context: Dict[str, Any]) -> str:
    """
    Create the user prompt for extraction with context.
    
    Args:
        utterance: The user's natural language input
        context: Conversation context including current date and previous extractions
    
    Returns:
        Formatted user prompt string
    """
    current_date = context.get("current_date", date.today().isoformat())
    conversation_history = context.get("conversation_history", [])
    previous_extraction = context.get("previous_extraction")
    
    prompt_parts = [
        f"Current date: {current_date}",
        "",
        "Customer utterance:",
        f'"{utterance}"',
        "",
    ]
    
    # Add conversation context if available
    if conversation_history:
        prompt_parts.append("Previous conversation context:")
        for i, msg in enumerate(conversation_history[-3:], 1):  # Last 3 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            prompt_parts.append(f"{i}. {role}: {content}")
        prompt_parts.append("")
    
    # Add previous extraction if available
    if previous_extraction:
        prompt_parts.append("Previously extracted information:")
        for field, value in previous_extraction.items():
            if value is not None and field not in ["confidence", "is_correction", "corrected_field", "needs_clarification", "clarification_needed_for"]:
                prompt_parts.append(f"  - {field}: {value}")
        prompt_parts.append("")
        prompt_parts.append("NOTE: Check if the current utterance corrects any of these values.")
        prompt_parts.append("")
    
    prompt_parts.append("Extract booking information and return as JSON:")
    
    return "\n".join(prompt_parts)


def create_fallback_response() -> Dict[str, Any]:
    """
    Create a fallback response when extraction fails.
    
    Returns:
        Dictionary with all fields set to null/default values
    """
    return {
        "date": None,
        "time": None,
        "party_size": None,
        "name": None,
        "phone": None,
        "special_requests": None,
        "is_correction": False,
        "corrected_field": None,
        "confidence": {},
        "needs_clarification": True,
        "clarification_needed_for": ["all"]
    }


# Example prompts for testing
EXAMPLE_UTTERANCES = [
    "I'd like to book a table for 4 people this Friday at 7 PM",
    "Actually, make that Saturday instead",
    "Tomorrow at dinner time for six people",
    "Table for two on the 15th around 7:30",
    "Change the time to 8 PM",
    "Party of 8, next Monday evening",
]
