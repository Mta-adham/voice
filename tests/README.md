# BookingService Tests

This directory contains comprehensive unit and integration tests for the BookingService.

## Test Coverage

### Unit Tests for Validation Rules (`TestValidationRules`)
- Past date validation
- Future date beyond booking window validation
- Party size validation (too small/too large)
- Operating hours validation (before/after hours)
- Valid booking request scenarios

### Availability Query Tests (`TestAvailableSlots`)
- Empty slot lists
- Capacity filtering
- Past time slot filtering
- Operating hours filtering
- Remaining capacity calculations

### Integration Tests for Booking Creation (`TestBookingCreation`)
- Successful booking creation
- Insufficient capacity handling
- Validation failure handling
- Duplicate booking constraint enforcement
- Automatic time slot creation
- Atomic transaction handling

### Time Slot Generation Tests (`TestTimeSlotGeneration`)
- Successful slot generation
- Skip generation for existing slots
- Slot duration configuration respect

### Error Handling Tests (`TestErrorHandling`)
- Missing configuration handling
- Database connection error handling

## Running Tests

### Run all tests:
```bash
pytest tests/
```

### Run with verbose output:
```bash
pytest tests/ -v
```

### Run specific test class:
```bash
pytest tests/test_booking_service.py::TestValidationRules -v
```

### Run specific test:
```bash
pytest tests/test_booking_service.py::TestValidationRules::test_validate_past_date -v
```

### Run with coverage:
```bash
pytest tests/ --cov=src/services --cov-report=html
```

## Test Database

Tests use an in-memory SQLite database that is created fresh for each test session. This ensures:
- Fast test execution
- No side effects between tests
- No need for database cleanup
- Easy CI/CD integration

## Success Criteria

All tests must pass to verify:
- ✅ Availability queries correctly calculate remaining capacity per slot
- ✅ Cannot create booking for past dates or dates beyond 30-day window
- ✅ Cannot create booking for party size > 8 or < 1
- ✅ Cannot create booking outside operating hours
- ✅ Cannot create booking if insufficient capacity in time slot
- ✅ Booking creation is atomic (either booking + capacity update both succeed, or both fail)
- ✅ Concurrent bookings don't create overbooking (via database-level locking)
- ✅ Generated time slots respect operating hours and slot duration configuration
