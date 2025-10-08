"""
Example usage of the Response Generation System.

This script demonstrates how to use the response generation system for
different conversation states in the restaurant booking flow.
"""
import sys
from pathlib import Path
from datetime import date, time

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from response import (
    generate_response,
    generate_response_sync,
    get_fallback_response,
    get_available_states,
)


def main():
    """Run examples of response generation."""
    
    print("=" * 70)
    print("Restaurant Booking Voice Agent - Response Generation Examples")
    print("=" * 70)
    print()
    
    # Example 1: Initial Greeting
    print("1. Initial Greeting")
    print("-" * 70)
    try:
        response = generate_response("greeting")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Fallback: {get_fallback_response('greeting')}")
    print()
    
    # Example 2: Collecting Date
    print("2. Collecting Date")
    print("-" * 70)
    try:
        response = generate_response("collecting_date")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Fallback: {get_fallback_response('collecting_date')}")
    print()
    
    # Example 3: Collecting Time with Date Context
    print("3. Collecting Time (with date context)")
    print("-" * 70)
    context = {
        "date": date(2024, 12, 25),
        "party_size": 4
    }
    print(f"Context: {context}")
    try:
        response = generate_response("collecting_time", context=context)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Fallback: {get_fallback_response('collecting_time')}")
    print()
    
    # Example 4: Presenting Available Slots
    print("4. Presenting Available Time Slots")
    print("-" * 70)
    context = {
        "date": date(2024, 12, 25),
        "party_size": 4
    }
    data = {
        "available_slots": [
            time(18, 0),
            time(18, 30),
            time(19, 0),
            time(19, 30),
            time(20, 0)
        ]
    }
    print(f"Context: {context}")
    print(f"Data: {data}")
    try:
        response = generate_response("presenting_availability", context=context, data=data)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Fallback: {get_fallback_response('presenting_availability')}")
    print()
    
    # Example 5: No Availability
    print("5. No Availability Error")
    print("-" * 70)
    context = {
        "date": date(2024, 12, 25),
        "time": time(19, 0),
        "party_size": 4
    }
    data = {
        "alternatives": "We have tables available at 6:00 PM or 8:30 PM, or we could check December 26th"
    }
    print(f"Context: {context}")
    print(f"Data: {data}")
    try:
        response = generate_response("no_availability", context=context, data=data)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Fallback: {get_fallback_response('no_availability')}")
    print()
    
    # Example 6: Confirming Booking
    print("6. Confirming Booking Details")
    print("-" * 70)
    data = {
        "booking_details": {
            "date": date(2024, 12, 25),
            "time": time(19, 0),
            "party_size": 4,
            "name": "John Doe",
            "phone": "+1234567890"
        }
    }
    print(f"Data: {data}")
    try:
        response = generate_response("confirming", data=data)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Fallback: {get_fallback_response('confirming')}")
    print()
    
    # Example 7: Completed Booking
    print("7. Booking Completed")
    print("-" * 70)
    try:
        response = generate_response("completed", data=data)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Fallback: {get_fallback_response('completed')}")
    print()
    
    # Example 8: Goodbye
    print("8. Goodbye Message")
    print("-" * 70)
    try:
        response = generate_response("goodbye")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Fallback: {get_fallback_response('goodbye')}")
    print()
    
    # Example 9: Using generate_response_sync (with metadata)
    print("9. Using generate_response_sync (with metadata)")
    print("-" * 70)
    result = generate_response_sync("greeting")
    if result["success"]:
        print(f"Success: {result['success']}")
        print(f"State: {result['state']}")
        print(f"Response: {result['response']}")
    else:
        print(f"Success: {result['success']}")
        print(f"Error: {result['error']}")
    print()
    
    # Example 10: List Available States
    print("10. Available Conversation States")
    print("-" * 70)
    states = get_available_states()
    print(f"Total states: {len(states)}")
    for i, state in enumerate(states, 1):
        print(f"  {i:2d}. {state}")
    print()
    
    print("=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
