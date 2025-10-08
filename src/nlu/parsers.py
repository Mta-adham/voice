"""
Helper functions for parsing dates, times, and party sizes from natural language.

This module provides utilities to normalize various formats of dates, times,
and party sizes into standardized formats.
"""
import re
from datetime import datetime, date, time, timedelta
from typing import Optional, Tuple
from loguru import logger


def parse_relative_date(date_str: str, reference_date: Optional[date] = None) -> Optional[date]:
    """
    Convert relative date expressions to absolute dates.
    
    Handles expressions like:
    - "today", "tomorrow"
    - "this Friday", "next Monday"
    - "the 15th", "15th", "the 15"
    - "next week"
    
    Args:
        date_str: Date string to parse (e.g., "this Friday", "tomorrow")
        reference_date: Reference date for relative calculations (defaults to today)
    
    Returns:
        Parsed date object or None if parsing fails
    """
    if not date_str:
        return None
    
    if reference_date is None:
        reference_date = date.today()
    
    date_str = date_str.lower().strip()
    
    # Handle "today"
    if date_str in ["today"]:
        return reference_date
    
    # Handle "tomorrow"
    if date_str in ["tomorrow", "tmrw"]:
        return reference_date + timedelta(days=1)
    
    # Handle "day after tomorrow"
    if "day after tomorrow" in date_str:
        return reference_date + timedelta(days=2)
    
    # Handle specific day names (this/next Monday, Tuesday, etc.)
    weekdays = {
        "monday": 0, "mon": 0,
        "tuesday": 1, "tue": 1, "tues": 1,
        "wednesday": 2, "wed": 2,
        "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
        "friday": 4, "fri": 4,
        "saturday": 5, "sat": 5,
        "sunday": 6, "sun": 6,
    }
    
    for day_name, day_num in weekdays.items():
        if day_name in date_str:
            current_weekday = reference_date.weekday()
            
            # "this [day]" - next occurrence of that day
            if "this" in date_str or ("next" not in date_str and "following" not in date_str):
                days_ahead = day_num - current_weekday
                if days_ahead <= 0:  # If it's today or past, go to next week
                    days_ahead += 7
                return reference_date + timedelta(days=days_ahead)
            
            # "next [day]" - the occurrence after "this [day]"
            if "next" in date_str or "following" in date_str:
                days_ahead = day_num - current_weekday
                if days_ahead <= 0:
                    days_ahead += 7
                days_ahead += 7  # Add another week for "next"
                return reference_date + timedelta(days=days_ahead)
    
    # Handle "next week"
    if "next week" in date_str:
        return reference_date + timedelta(days=7)
    
    # Handle day of month (e.g., "the 15th", "15th", "the 15")
    day_pattern = r'(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?'
    match = re.search(day_pattern, date_str)
    if match:
        try:
            day = int(match.group(1))
            if 1 <= day <= 31:
                # Try current month first
                current_year = reference_date.year
                current_month = reference_date.month
                
                try:
                    target_date = date(current_year, current_month, day)
                    # If the date is in the past, try next month
                    if target_date < reference_date:
                        next_month = current_month + 1
                        next_year = current_year
                        if next_month > 12:
                            next_month = 1
                            next_year += 1
                        target_date = date(next_year, next_month, day)
                    return target_date
                except ValueError:
                    # Day doesn't exist in current month, try next month
                    next_month = current_month + 1
                    next_year = current_year
                    if next_month > 12:
                        next_month = 1
                        next_year += 1
                    try:
                        return date(next_year, next_month, day)
                    except ValueError:
                        pass
        except (ValueError, IndexError):
            pass
    
    # Try to parse as ISO format date (YYYY-MM-DD)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        pass
    
    return None


def parse_time_to_24hour(time_str: str) -> Optional[str]:
    """
    Convert various time formats to 24-hour format (HH:MM).
    
    Handles formats like:
    - "7 PM", "7PM", "7 p.m."
    - "7:00", "7:30"
    - "19:00", "19:30"
    - "around 7", "about 7pm"
    - "evening", "dinner time", "lunch"
    
    Args:
        time_str: Time string to parse
    
    Returns:
        Time in 24-hour format (HH:MM) or None if parsing fails
    """
    if not time_str:
        return None
    
    time_str = time_str.lower().strip()
    
    # Handle common meal times
    meal_times = {
        "breakfast": "08:00",
        "lunch": "12:00",
        "lunchtime": "12:00",
        "dinner": "19:00",
        "dinnertime": "19:00",
        "dinner time": "19:00",
        "brunch": "11:00",
        "evening": "19:00",
        "afternoon": "14:00",
        "noon": "12:00",
        "midnight": "00:00",
    }
    
    for meal, default_time in meal_times.items():
        if meal in time_str:
            return default_time
    
    # Remove common words
    time_str = re.sub(r'\b(around|about|at|approximately)\b', '', time_str).strip()
    
    # Try to match time with AM/PM
    # Pattern: optional hour, optional colon and minutes, optional space, AM/PM
    am_pm_pattern = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)'
    match = re.search(am_pm_pattern, time_str)
    
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        period = match.group(3)
        
        # Validate hour and minute
        if not (1 <= hour <= 12):
            return None
        if not (0 <= minute <= 59):
            return None
        
        # Convert to 24-hour format
        if 'p' in period and hour != 12:
            hour += 12
        elif 'a' in period and hour == 12:
            hour = 0
        
        return f"{hour:02d}:{minute:02d}"
    
    # Try to match 24-hour format or time without AM/PM
    time_pattern = r'(\d{1,2})(?::(\d{2}))?'
    match = re.search(time_pattern, time_str)
    
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        
        # If hour is between 1-11 without AM/PM, assume PM for dinner times (5-11)
        # and AM for breakfast times (7-11)
        if hour <= 12 and ":" not in time_str:
            # Heuristic: if someone says "7" without AM/PM, assume 7 PM (19:00)
            # unless it's clearly morning (before 5)
            if 5 <= hour <= 11:
                hour += 12
        
        # Validate final hour and minute
        if not (0 <= hour <= 23):
            return None
        if not (0 <= minute <= 59):
            return None
        
        return f"{hour:02d}:{minute:02d}"
    
    return None


def extract_party_size(text: str) -> Optional[int]:
    """
    Extract party size from natural language text.
    
    Handles expressions like:
    - "4 people", "four people"
    - "party of 6"
    - "8 guests"
    - "table for 2"
    - "reservation for five"
    
    Args:
        text: Text containing party size information
    
    Returns:
        Party size as integer or None if not found
    """
    if not text:
        return None
    
    text = text.lower().strip()
    
    # Number words to digits
    number_words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12,
        "a": 1, "an": 1,
    }
    
    # Try patterns with "party of", "table for", "reservation for", etc.
    patterns = [
        r'party\s+of\s+(\w+)',
        r'table\s+for\s+(\w+)',
        r'reservation\s+for\s+(\w+)',
        r'(\w+)\s+(?:people|guests|persons|ppl)',
        r'(\d+)',  # Just a plain number as fallback
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            size_str = match.group(1)
            
            # Try to convert to int directly
            try:
                size = int(size_str)
                if 1 <= size <= 20:  # Reasonable party size
                    return size
            except ValueError:
                # Try to convert from word
                if size_str in number_words:
                    size = number_words[size_str]
                    if 1 <= size <= 20:
                        return size
    
    return None


def validate_date_in_booking_window(
    target_date: date,
    booking_window_days: int = 30,
    reference_date: Optional[date] = None
) -> Tuple[bool, str]:
    """
    Validate that a date is within the acceptable booking window.
    
    Args:
        target_date: Date to validate
        booking_window_days: Maximum days in advance to allow bookings
        reference_date: Reference date (defaults to today)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if reference_date is None:
        reference_date = date.today()
    
    # Check if date is in the past
    if target_date < reference_date:
        return False, "Date cannot be in the past"
    
    # Check if date is too far in the future
    max_date = reference_date + timedelta(days=booking_window_days)
    if target_date > max_date:
        return False, f"Bookings can only be made up to {booking_window_days} days in advance"
    
    return True, ""


def validate_time_in_operating_hours(
    target_time: str,
    open_time: str = "11:00",
    close_time: str = "22:00"
) -> Tuple[bool, str]:
    """
    Validate that a time is within operating hours.
    
    Args:
        target_time: Time to validate in HH:MM format
        open_time: Opening time in HH:MM format
        close_time: Closing time in HH:MM format
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        target = datetime.strptime(target_time, "%H:%M").time()
        open_t = datetime.strptime(open_time, "%H:%M").time()
        close_t = datetime.strptime(close_time, "%H:%M").time()
        
        if open_t <= target < close_t:
            return True, ""
        else:
            return False, f"Time must be between {open_time} and {close_time}"
    except ValueError as e:
        return False, f"Invalid time format: {str(e)}"
