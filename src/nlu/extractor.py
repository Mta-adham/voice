"""
Information extraction module for restaurant booking system.

This module uses LLMs to extract structured booking information from
natural language utterances and provides validation and post-processing.
"""
import json
import re
from datetime import date, datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from loguru import logger

from ..services.llm_service import llm_chat, LLMError
from .prompts import SYSTEM_PROMPT, create_extraction_prompt, create_fallback_response
from .parsers import (
    parse_relative_date,
    parse_time_to_24hour,
    extract_party_size,
    validate_date_in_booking_window,
    validate_time_in_operating_hours,
)


@dataclass
class BookingExtractionResult:
    """
    Result of booking information extraction.
    
    Attributes:
        date: Booking date in ISO format (YYYY-MM-DD) or None
        time: Booking time in 24-hour format (HH:MM) or None
        party_size: Number of people or None
        name: Customer name or None
        phone: Customer phone or None
        special_requests: Special requests/notes or None
        is_correction: Whether this is a correction of previous info
        corrected_field: Which field was corrected (if any)
        confidence: Confidence scores for each field (0.0-1.0)
        needs_clarification: Whether clarification is needed
        clarification_needed_for: List of fields needing clarification
        raw_response: Raw LLM response for debugging
        extraction_errors: List of errors encountered during extraction
    """
    date: Optional[str] = None
    time: Optional[str] = None
    party_size: Optional[int] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    special_requests: Optional[str] = None
    is_correction: bool = False
    corrected_field: Optional[str] = None
    confidence: Dict[str, float] = field(default_factory=dict)
    needs_clarification: bool = False
    clarification_needed_for: List[str] = field(default_factory=list)
    raw_response: Optional[str] = None
    extraction_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)


def _detect_correction_keywords(utterance: str) -> bool:
    """
    Detect if utterance contains correction keywords.
    
    Args:
        utterance: User utterance to check
    
    Returns:
        True if correction keywords detected
    """
    correction_keywords = [
        r'\bactually\b',
        r'\bwait\b',
        r'\bno\b',
        r'\bchange\b',
        r'\binstead\b',
        r'\bi meant\b',
        r'\bcorrection\b',
        r'\bmake that\b',
        r'\bsorry\b',
        r'\bnot\b',
        r'\brather\b',
    ]
    
    utterance_lower = utterance.lower()
    for pattern in correction_keywords:
        if re.search(pattern, utterance_lower):
            return True
    return False


def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    """
    Parse LLM response text into structured dictionary.
    
    Handles various response formats and extracts JSON.
    
    Args:
        response_text: Raw LLM response text
    
    Returns:
        Parsed dictionary or fallback response
    """
    try:
        # Try to extract JSON from response (in case LLM added extra text)
        # Look for JSON object pattern
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        if matches:
            # Try the largest match first (likely the complete object)
            for match in sorted(matches, key=len, reverse=True):
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # Try parsing the entire response
        return json.loads(response_text)
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}")
        logger.debug(f"Response text: {response_text}")
        return create_fallback_response()


def _post_process_extraction(
    extracted: Dict[str, Any],
    utterance: str,
    context: Dict[str, Any]
) -> BookingExtractionResult:
    """
    Post-process extracted information with validation and parsing.
    
    Args:
        extracted: Raw extracted dictionary from LLM
        utterance: Original user utterance
        context: Conversation context
    
    Returns:
        BookingExtractionResult with validated and processed data
    """
    errors = []
    current_date = context.get("current_date")
    if isinstance(current_date, str):
        current_date = datetime.fromisoformat(current_date).date()
    elif current_date is None:
        current_date = date.today()
    
    # Process date
    date_str = extracted.get("date")
    if date_str:
        # Try parsing if it looks like relative date
        if not re.match(r'\d{4}-\d{2}-\d{2}', str(date_str)):
            parsed_date = parse_relative_date(str(date_str), current_date)
            if parsed_date:
                date_str = parsed_date.isoformat()
            else:
                errors.append(f"Failed to parse date: {date_str}")
                date_str = None
        else:
            # Validate ISO format date
            try:
                datetime.fromisoformat(date_str)
            except ValueError:
                errors.append(f"Invalid date format: {date_str}")
                date_str = None
    
    # Process time
    time_str = extracted.get("time")
    if time_str:
        # Try parsing if not in HH:MM format
        if not re.match(r'\d{2}:\d{2}', str(time_str)):
            parsed_time = parse_time_to_24hour(str(time_str))
            if parsed_time:
                time_str = parsed_time
            else:
                errors.append(f"Failed to parse time: {time_str}")
                time_str = None
        else:
            # Validate HH:MM format
            if not re.match(r'^([0-1]\d|2[0-3]):[0-5]\d$', time_str):
                errors.append(f"Invalid time format: {time_str}")
                time_str = None
    
    # Process party size
    party_size = extracted.get("party_size")
    if party_size is not None:
        try:
            party_size = int(party_size)
            if party_size < 1 or party_size > 20:
                errors.append(f"Party size out of range: {party_size}")
                party_size = None
        except (ValueError, TypeError):
            # Try extracting from original utterance as fallback
            party_size = extract_party_size(utterance)
            if party_size is None:
                errors.append(f"Invalid party size: {extracted.get('party_size')}")
    
    # Validate phone format if provided
    phone = extracted.get("phone")
    if phone:
        # Basic phone validation - should have at least 10 digits
        digits_only = re.sub(r'\D', '', str(phone))
        if len(digits_only) < 10:
            errors.append(f"Phone number too short: {phone}")
    
    # Extract confidence scores
    confidence = extracted.get("confidence", {})
    if not isinstance(confidence, dict):
        confidence = {}
    
    # Check if correction was detected
    is_correction = extracted.get("is_correction", False)
    if not is_correction:
        # Also check utterance for correction keywords as fallback
        is_correction = _detect_correction_keywords(utterance)
    
    corrected_field = extracted.get("corrected_field")
    
    # Determine if clarification is needed
    needs_clarification = extracted.get("needs_clarification", False)
    clarification_needed_for = extracted.get("clarification_needed_for", [])
    
    # Auto-detect clarification need based on confidence scores
    low_confidence_fields = []
    for field, score in confidence.items():
        if score < 0.7:
            low_confidence_fields.append(field)
    
    if low_confidence_fields:
        needs_clarification = True
        clarification_needed_for.extend(
            [f for f in low_confidence_fields if f not in clarification_needed_for]
        )
    
    # Create result
    result = BookingExtractionResult(
        date=date_str,
        time=time_str,
        party_size=party_size,
        name=extracted.get("name"),
        phone=phone,
        special_requests=extracted.get("special_requests"),
        is_correction=is_correction,
        corrected_field=corrected_field,
        confidence=confidence,
        needs_clarification=needs_clarification,
        clarification_needed_for=clarification_needed_for,
        extraction_errors=errors,
    )
    
    return result


def extract_booking_info(
    utterance: str,
    context: Optional[Dict[str, Any]] = None,
    provider: str = "openai",
    temperature: float = 0.3,
) -> BookingExtractionResult:
    """
    Extract structured booking information from natural language utterance.
    
    This function uses an LLM to parse user utterances and extract booking-related
    information such as date, time, party size, customer details, and special requests.
    It handles relative dates, various time formats, corrections, and ambiguous inputs.
    
    Args:
        utterance: Natural language input from the user
        context: Optional conversation context containing:
            - current_date: Reference date for relative date parsing (default: today)
            - conversation_history: Previous conversation messages
            - previous_extraction: Previously extracted booking info
            - booking_window_days: Maximum days to allow bookings (default: 30)
            - operating_hours: Dict of operating hours by day
        provider: LLM provider to use ("openai", "gemini", or "claude")
        temperature: Sampling temperature for LLM (0.0-1.0, lower = more focused)
    
    Returns:
        BookingExtractionResult with extracted information and metadata
    
    Raises:
        LLMError: If LLM call fails after retries
    
    Examples:
        >>> result = extract_booking_info("Table for 4 this Friday at 7 PM")
        >>> print(result.date)  # "2024-10-13"
        >>> print(result.time)  # "19:00"
        >>> print(result.party_size)  # 4
        
        >>> # With context for corrections
        >>> context = {"previous_extraction": {"date": "2024-10-13"}}
        >>> result = extract_booking_info("Actually, make that Saturday", context)
        >>> print(result.is_correction)  # True
        >>> print(result.corrected_field)  # "date"
    """
    if context is None:
        context = {}
    
    # Set default current_date if not provided
    if "current_date" not in context:
        context["current_date"] = date.today().isoformat()
    
    logger.info(f"Extracting booking info from utterance: '{utterance}'")
    logger.debug(f"Context: {context}")
    
    try:
        # Create the extraction prompt
        user_prompt = create_extraction_prompt(utterance, context)
        
        # Call LLM with retry logic (built into llm_service)
        messages = [{"role": "user", "content": user_prompt}]
        
        response = llm_chat(
            provider=provider,
            messages=messages,
            system_prompt=SYSTEM_PROMPT,
            temperature=temperature,
            max_tokens=500,
        )
        
        response_text = response["content"]
        logger.debug(f"LLM response: {response_text}")
        
        # Parse LLM response
        extracted = _parse_llm_response(response_text)
        
        # Post-process and validate
        result = _post_process_extraction(extracted, utterance, context)
        result.raw_response = response_text
        
        # Log results
        logger.info(
            f"Extraction complete | "
            f"date={result.date} | "
            f"time={result.time} | "
            f"party_size={result.party_size} | "
            f"needs_clarification={result.needs_clarification}"
        )
        
        if result.extraction_errors:
            logger.warning(f"Extraction errors: {result.extraction_errors}")
        
        return result
        
    except LLMError as e:
        logger.error(f"LLM error during extraction: {e}")
        # Return fallback result with error info
        result = BookingExtractionResult(
            needs_clarification=True,
            clarification_needed_for=["all"],
            extraction_errors=[f"LLM error: {str(e)}"]
        )
        return result
    
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {e}")
        # Return fallback result
        result = BookingExtractionResult(
            needs_clarification=True,
            clarification_needed_for=["all"],
            extraction_errors=[f"Unexpected error: {str(e)}"]
        )
        return result


def validate_extraction_for_booking(
    extraction: BookingExtractionResult,
    config: Optional[Dict[str, Any]] = None
) -> tuple[bool, List[str]]:
    """
    Validate that extracted information is sufficient and valid for creating a booking.
    
    Args:
        extraction: BookingExtractionResult to validate
        config: Optional restaurant configuration containing:
            - booking_window_days: Maximum days for advance booking
            - operating_hours: Operating hours by day of week
            - max_party_size: Maximum allowed party size
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if config is None:
        config = {}
    
    # Check required fields
    if not extraction.date:
        errors.append("Date is required")
    
    if not extraction.time:
        errors.append("Time is required")
    
    if not extraction.party_size:
        errors.append("Party size is required")
    
    if not extraction.name:
        errors.append("Customer name is required")
    
    if not extraction.phone:
        errors.append("Customer phone is required")
    
    # Validate date if present
    if extraction.date:
        try:
            booking_date = datetime.fromisoformat(extraction.date).date()
            booking_window = config.get("booking_window_days", 30)
            is_valid, error_msg = validate_date_in_booking_window(
                booking_date,
                booking_window
            )
            if not is_valid:
                errors.append(error_msg)
        except ValueError:
            errors.append(f"Invalid date format: {extraction.date}")
    
    # Validate time if present
    if extraction.time:
        # This would need operating hours from config
        # For now, basic format validation
        if not re.match(r'^([0-1]\d|2[0-3]):[0-5]\d$', extraction.time):
            errors.append(f"Invalid time format: {extraction.time}")
    
    # Validate party size if present
    if extraction.party_size:
        max_party_size = config.get("max_party_size", 8)
        if extraction.party_size < 1:
            errors.append("Party size must be at least 1")
        elif extraction.party_size > max_party_size:
            errors.append(f"Party size cannot exceed {max_party_size}")
    
    # Add extraction errors
    if extraction.extraction_errors:
        errors.extend(extraction.extraction_errors)
    
    return len(errors) == 0, errors
