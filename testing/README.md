# Travel With Nandu - Testing Instructions

## Overview
This document provides instructions and templates for the QA/testing team to validate the Driver Portal and related features.

## Files Included
- test-plan.md: High-level test plan and scenarios
- test-cases-driver-portal.xlsx: Detailed test cases for the driver portal (Excel format)
- bug-report-template.md: Template for reporting issues
- test-instructions.md: Step-by-step instructions for testers

## How to Use
1. Review the test plan and scenarios in test-plan.md.
2. Use test-cases-driver-portal.xlsx to track and execute test cases.
3. Report any issues using bug-report-template.md.
4. Follow test-instructions.md for environment setup and login details.

---

For any questions, contact the development team.
To ensure your tester understands exactly what to perform, you should explain that this project focuses on **End-to-End (E2E) Functional Testing** and **Database Integrity Testing** rather than traditional API testing.

Since you are using a "Free-Tier" Firebase architecture, your app does not have a custom backend API (like Node.js or Python) to test. Instead, the "API" is Firebase itself, and the testing focuses on how the frontend handles data directly.

### 1. Does it have API Testing?

**No, there is no traditional API testing.** * Because your app communicates directly with Google Firebase, you do not need to test API endpoints like `GET /rides`.

* Instead, your tester performs **Database Transaction Testing**, which checks if the data (like a new booking) appears correctly in the Firestore database after a button is clicked in the UI.

### 2. What types of testing should the tester do?

You should tell your tester to perform these **four specific types of testing** found in your files:

* **Functional Testing (The "Happy Path")**:
* The tester acts as a customer to book a seat and verifies the price is calculated correctly.
* They verify the "Handshake" works: the driver must enter the customer's OTP to successfully start a ride.


* **Concurrency & Race Condition Testing**:
* This is critical for your app. The tester should try to "break" the seat count by having two people book the last seat at the same time.
* They should also test "Double-Clicking" the confirm button to see if the app accidentally creates two identical bookings.


* **Offline & Synchronization Testing**:
* The tester must simulate a "highway with no signal" by turning on Airplane Mode.
* They verify the app still shows "My Rides" using the cache and check if new data syncs perfectly once the internet returns.


* **Security & Access Testing**:
* The tester acts as a "hacker" by trying to access the `admin.html` page without an admin account to ensure they are blocked.
* They verify that one customer cannot see the phone number or ride details of a different customer.



### 3. Summary for your Tester

You can give them this simple instruction:

> "We don't have a standard API to test. Your task is to use the **Test Plan** and **Test Instructions** to make sure the Customer App and Driver Portal work together perfectly, even when the internet is bad or two people book at once."