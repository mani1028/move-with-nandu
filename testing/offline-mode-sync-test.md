# Offline Mode & Sync Test Case

## Objective
Validate that the Driver Portal functions correctly in offline mode and that data syncs properly when connectivity is restored.

## Test Steps

### 1. Offline Order History
- Open the Driver Portal and log in.
- Navigate to "My Rides" or booking history.
- Turn off Wi-Fi and/or mobile data.
- Attempt to view the list of rides/bookings.
- Expected: Cached data is visible; no errors or blank screens.

### 2. Offline Profile Update
- While offline, edit the profile (e.g., change name or phone number).
- Save changes.
- Expected: UI shows update locally; no sync errors.

### 3. Re-connection Sync
- Re-enable Wi-Fi/mobile data.
- Wait for sync or manually refresh.
- Expected: Profile changes and any offline actions are synced to Firestore; data is consistent across devices.

### 4. Error Handling
- Attempt actions that require network (e.g., new booking) while offline.
- Expected: User-friendly error or offline queueing; no app crash.

## Notes
- Test on both desktop and mobile browsers.
- Verify Service Worker is active (check browser dev tools).
- Confirm data consistency after reconnecting.

---
Add results to test-cases-driver-portal.xlsx and report any issues using bug-report-template.md.