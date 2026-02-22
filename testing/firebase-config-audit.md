# Firebase Configuration Audit

## Objective
Ensure the app is connected to the correct Firebase project and no test keys remain.

## Steps
1. Open public/firebase-config.js.
2. Verify projectId is 'travelwithnandu-25a27'.
3. Confirm apiKey, authDomain, and other keys match production values.
4. Search for any test or staging keys in the codebase.
5. Attempt login and registration; confirm data appears in production Firestore.

## Expected Result
- All keys are production values.
- No test keys present.
- Data is written to the correct Firestore project.

---
Add results to bug-report-template.md if issues found.