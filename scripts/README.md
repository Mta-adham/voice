# Scripts Directory

This directory contains utility scripts for the restaurant booking system.

## Available Scripts

### seed_database.py

Seeds the database with initial data including:
- Restaurant configuration (operating hours, capacity, etc.)
- Time slots for the next 30 days
- Sample bookings for testing

**Usage:**
```bash
# Basic seeding
python scripts/seed_database.py

# Reset database before seeding
python scripts/seed_database.py --reset

# Generate slots for specific number of days
python scripts/seed_database.py --days 60
```

**Options:**
- `--reset`: Clear all existing data before seeding
- `--days N`: Generate time slots for N days (default: 30)

### demo.py

Interactive demonstration of the complete booking conversation flow.

**Usage:**
```bash
# Interactive mode (user provides input)
python scripts/demo.py

# Auto mode (uses predefined responses)
python scripts/demo.py --mode auto

# Mock mode (for testing without external services)
python scripts/demo.py --mode mock
```

**Modes:**
- `interactive`: Prompts for user input at each step (default)
- `auto`: Uses predefined responses to demonstrate the flow
- `mock`: Mocks all external services for testing

**Demo Flow:**
1. Greeting
2. Collect booking date
3. Collect booking time
4. Collect party size
5. Collect customer name
6. Collect phone number
7. Confirmation
8. Create booking in database

## Requirements

Before running these scripts, ensure:

1. Database is configured (set `DATABASE_URL` environment variable)
2. Python dependencies are installed: `pip install -r requirements.txt`
3. `.env` file is configured with necessary API keys (for full functionality)

## Examples

### First-time Setup
```bash
# 1. Seed the database
python scripts/seed_database.py

# 2. Run the demo
python scripts/demo.py --mode auto
```

### Reset and Re-seed
```bash
# Clear all data and re-seed
python scripts/seed_database.py --reset

# Generate slots for 60 days
python scripts/seed_database.py --reset --days 60
```

### Test the Booking Flow
```bash
# Interactive test
python scripts/demo.py

# Automated test
python scripts/demo.py --mode auto
```

## Notes

- `seed_database.py` is idempotent - it won't duplicate data if run multiple times
- `demo.py` creates actual bookings in the database
- Both scripts require a properly configured database connection
- The demo script uses colored terminal output for better readability
