"""
Natural Language Understanding (NLU) module for restaurant booking system.

This module provides information extraction capabilities for converting
natural language utterances into structured booking data.
"""
from .extractor import extract_booking_info, BookingExtractionResult

__all__ = ["extract_booking_info", "BookingExtractionResult"]
