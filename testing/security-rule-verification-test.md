# Security Rule Verification Test

## Objective
Ensure Firestore security rules and app logic prevent unauthorized access.

## Steps
1. Log in as a standard user.
2. Attempt to access admin.html directly via URL.
3. Try to view or modify another user's booking by changing Firestore document IDs in the client.
4. Attempt to read/write to drivers collection as a non-driver.

## Expected Result
- Access to admin.html is denied or redirected.
- Cannot view or modify other users' bookings.
- Firestore rules block unauthorized reads/writes.

---
Document any issues in bug-report-template.md.