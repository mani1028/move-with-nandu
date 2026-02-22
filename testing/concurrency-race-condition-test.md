# Concurrency & Race Condition Test

## Objective
Validate that booking logic prevents double-booking and handles simultaneous seat requests.

## Steps
### 1. Last Seat Test
- Two testers log in and attempt to book the last available seat at the same time.
- Observe which user gets the seat and what error/message the other receives.

### 2. Double-Booking Prevention
- Rapidly click "Confirm Booking" multiple times.
- Verify only one booking is created in Firestore.

## Expected Result
- Only one user gets the last seat.
- No duplicate bookings are created.
- User-friendly error/message for failed attempts.

---
Log results in test-cases-driver-portal.xlsx and bug-report-template.md.