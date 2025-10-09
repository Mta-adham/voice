#!/usr/bin/env python3
"""
Interactive demo script for restaurant booking system.

This script walks through the happy path conversation example:
1. Greeting
2. Collect date
3. Collect time
4. Collect party size
5. Collect name
6. Collect phone
7. Confirmation
8. Booking created

Usage:
    python scripts/demo.py [--mode MODE]

Options:
    --mode MODE     Demo mode: 'interactive', 'auto', or 'mock' (default: interactive)
                    - interactive: Prompts for user input
                    - auto: Uses predefined responses
                    - mock: Mocks all external services (for testing)
"""
import sys
import argparse
import time
from pathlib import Path
from datetime import date, time as time_obj, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.database import init_db, create_tables, get_db_session
from services.booking_service import BookingService
from conversation.state_manager import ConversationStateManager
from conversation.states import ConversationState
from models.schemas import BookingCreate


class Colors:
    """ANSI color codes for terminal output."""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_assistant(text: str):
    """Print assistant message."""
    print(f"{Colors.GREEN}🤖 Assistant: {Colors.END}{text}")


def print_user(text: str):
    """Print user message."""
    print(f"{Colors.CYAN}👤 You: {Colors.END}{text}")


def print_system(text: str):
    """Print system message."""
    print(f"{Colors.YELLOW}⚙️  System: {Colors.END}{text}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.MAGENTA}ℹ️  {text}{Colors.END}")


def get_user_input(prompt: str, mode: str, auto_value: str = None) -> str:
    """
    Get user input based on mode.
    
    Args:
        prompt: Prompt to display
        mode: Demo mode ('interactive', 'auto', or 'mock')
        auto_value: Value to use in auto mode
    
    Returns:
        User input string
    """
    if mode == "interactive":
        return input(f"{Colors.CYAN}👤 {prompt}: {Colors.END}")
    else:  # auto or mock
        time.sleep(0.5)  # Simulate thinking
        print_user(auto_value)
        return auto_value


def demo_greeting(manager: ConversationStateManager, mode: str):
    """Demonstrate greeting phase."""
    print_header("STEP 1: Greeting")
    
    print_assistant(
        "Hello! Welcome to The Gourmet Table restaurant. "
        "I'm here to help you make a reservation."
    )
    
    time.sleep(1 if mode != "interactive" else 0)
    
    print_assistant(
        "I'll need to collect some information from you. "
        "Let's get started!"
    )
    
    time.sleep(1 if mode != "interactive" else 0)
    
    manager.transition_to(ConversationState.COLLECTING_DATE)


def demo_collect_date(manager: ConversationStateManager, mode: str) -> date:
    """Demonstrate date collection."""
    print_header("STEP 2: Collecting Date")
    
    print_assistant(
        "What date would you like to make a reservation? "
        "(Format: YYYY-MM-DD)"
    )
    
    tomorrow = date.today() + timedelta(days=1)
    auto_date = tomorrow.strftime("%Y-%m-%d")
    
    while True:
        date_str = get_user_input(
            "Enter date",
            mode,
            auto_date
        )
        
        try:
            reservation_date = date.fromisoformat(date_str)
            
            # Validate date
            if reservation_date < date.today():
                print_error("That date is in the past. Please choose a future date.")
                if mode != "interactive":
                    break
                continue
            
            result = manager.update_context(date=reservation_date)
            
            if "date" in result["errors"]:
                print_error(f"Invalid date: {result['errors']['date']}")
                if mode != "interactive":
                    break
                continue
            
            print_success(f"Great! I have you down for {reservation_date.strftime('%A, %B %d, %Y')}")
            return reservation_date
            
        except ValueError:
            print_error("Invalid date format. Please use YYYY-MM-DD")
            if mode != "interactive":
                return tomorrow


def demo_collect_time(manager: ConversationStateManager, mode: str) -> time_obj:
    """Demonstrate time collection."""
    print_header("STEP 3: Collecting Time")
    
    print_assistant(
        "What time would you prefer? "
        "(Format: HH:MM, e.g., 18:30 for 6:30 PM)"
    )
    
    auto_time = "18:30"
    
    while True:
        time_str = get_user_input(
            "Enter time",
            mode,
            auto_time
        )
        
        try:
            hours, minutes = map(int, time_str.split(':'))
            reservation_time = time_obj(hour=hours, minute=minutes)
            
            result = manager.update_context(time=reservation_time)
            
            if "time" in result["errors"]:
                print_error(f"Invalid time: {result['errors']['time']}")
                if mode != "interactive":
                    break
                continue
            
            print_success(f"Perfect! {reservation_time.strftime('%I:%M %p')} it is.")
            return reservation_time
            
        except ValueError:
            print_error("Invalid time format. Please use HH:MM (24-hour format)")
            if mode != "interactive":
                return time_obj(18, 30)


def demo_collect_party_size(manager: ConversationStateManager, mode: str) -> int:
    """Demonstrate party size collection."""
    print_header("STEP 4: Collecting Party Size")
    
    print_assistant("How many people will be dining with us?")
    
    auto_size = "4"
    
    while True:
        size_str = get_user_input(
            "Number of people",
            mode,
            auto_size
        )
        
        try:
            party_size = int(size_str)
            
            result = manager.update_context(party_size=party_size)
            
            if "party_size" in result["errors"]:
                print_error(f"Invalid party size: {result['errors']['party_size']}")
                if mode != "interactive":
                    break
                continue
            
            print_success(f"Excellent! A table for {party_size}.")
            return party_size
            
        except ValueError:
            print_error("Please enter a valid number")
            if mode != "interactive":
                return 4


def demo_collect_name(manager: ConversationStateManager, mode: str) -> str:
    """Demonstrate name collection."""
    print_header("STEP 5: Collecting Name")
    
    print_assistant("May I have your name for the reservation?")
    
    auto_name = "John Doe"
    
    while True:
        name = get_user_input(
            "Your name",
            mode,
            auto_name
        )
        
        result = manager.update_context(name=name)
        
        if "name" in result["errors"]:
            print_error(f"Invalid name: {result['errors']['name']}")
            if mode != "interactive":
                break
            continue
        
        print_success(f"Thank you, {name}!")
        return name


def demo_collect_phone(manager: ConversationStateManager, mode: str) -> str:
    """Demonstrate phone collection."""
    print_header("STEP 6: Collecting Phone Number")
    
    print_assistant(
        "And finally, what's the best phone number to reach you at? "
        "(Format: +1234567890 or any standard format)"
    )
    
    auto_phone = "+1234567890"
    
    while True:
        phone = get_user_input(
            "Phone number",
            mode,
            auto_phone
        )
        
        result = manager.update_context(phone=phone)
        
        if "phone" in result["errors"]:
            print_error(f"Invalid phone: {result['errors']['phone']}")
            if mode != "interactive":
                break
            continue
        
        print_success("Got it!")
        return phone


def demo_confirmation(manager: ConversationStateManager):
    """Demonstrate confirmation phase."""
    print_header("STEP 7: Confirmation")
    
    context = manager.context
    
    print_assistant("Let me confirm your reservation details:")
    print()
    print_info(f"  📅 Date: {context.date.strftime('%A, %B %d, %Y')}")
    print_info(f"  🕐 Time: {context.time.strftime('%I:%M %p')}")
    print_info(f"  👥 Party Size: {context.party_size} people")
    print_info(f"  👤 Name: {context.name}")
    print_info(f"  📞 Phone: {context.phone}")
    print()
    
    manager.transition_to(ConversationState.CONFIRMING)


def demo_create_booking(manager: ConversationStateManager, booking_service: BookingService):
    """Demonstrate booking creation."""
    print_header("STEP 8: Creating Booking")
    
    print_system("Creating your reservation in our system...")
    time.sleep(1)
    
    try:
        # Generate time slots if needed
        booking_service.generate_time_slots(manager.context.date)
        
        # Create booking
        booking_data = BookingCreate(
            date=manager.context.date,
            time_slot=manager.context.time,
            party_size=manager.context.party_size,
            customer_name=manager.context.name,
            customer_phone=manager.context.phone
        )
        
        booking = booking_service.create_booking(booking_data)
        
        print_success("Reservation created successfully!")
        print()
        print_info(f"  Confirmation ID: #{booking.id}")
        print_info(f"  Status: {booking.status.upper()}")
        print()
        
        print_assistant(
            f"Your reservation is confirmed! We look forward to seeing you, "
            f"{manager.context.name}, on {manager.context.date.strftime('%B %d')} "
            f"at {manager.context.time.strftime('%I:%M %p')}."
        )
        
        print_assistant(
            "You'll receive a confirmation message shortly. "
            "If you need to make any changes, please call us. Thank you!"
        )
        
        manager.transition_to(ConversationState.COMPLETED)
        
        return booking
        
    except Exception as e:
        print_error(f"Failed to create booking: {e}")
        return None


def run_demo(mode: str):
    """
    Run the complete demo.
    
    Args:
        mode: Demo mode ('interactive', 'auto', or 'mock')
    """
    print_header("Restaurant Booking System - Interactive Demo")
    
    try:
        # Initialize database
        print_system("Initializing database connection...")
        engine = init_db()
        create_tables()
        print_success("Database initialized")
        print()
        
        with get_db_session() as session:
            # Create booking service
            booking_service = BookingService(session)
            
            # Initialize conversation manager
            manager = ConversationStateManager(
                initial_state=ConversationState.GREETING
            )
            
            # Run conversation flow
            demo_greeting(manager, mode)
            demo_collect_date(manager, mode)
            manager.transition_to(ConversationState.COLLECTING_TIME)
            demo_collect_time(manager, mode)
            manager.transition_to(ConversationState.COLLECTING_PARTY_SIZE)
            demo_collect_party_size(manager, mode)
            manager.transition_to(ConversationState.COLLECTING_NAME)
            demo_collect_name(manager, mode)
            manager.transition_to(ConversationState.COLLECTING_PHONE)
            demo_collect_phone(manager, mode)
            demo_confirmation(manager)
            booking = demo_create_booking(manager, booking_service)
            
            if booking:
                print_header("Demo Completed Successfully!")
                print_success(
                    f"Booking #{booking.id} has been created and saved to the database."
                )
            else:
                print_header("Demo Completed with Errors")
                print_error("Booking could not be created.")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n")
        print_info("Demo interrupted by user.")
        return 130
    except Exception as e:
        print_error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive demo of restaurant booking system"
    )
    parser.add_argument(
        "--mode",
        choices=["interactive", "auto", "mock"],
        default="interactive",
        help="Demo mode: interactive (user input), auto (predefined), or mock (no external calls)"
    )
    
    args = parser.parse_args()
    
    sys.exit(run_demo(args.mode))


if __name__ == "__main__":
    main()
