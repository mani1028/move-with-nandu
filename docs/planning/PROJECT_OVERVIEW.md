# Project Overview (Move With Nandu)

## Purpose
This project is a ride-booking platform with separate passenger, driver, and admin portals.

## High-Level Components
- `backend/`: FastAPI backend with routers, auth, services, and websocket manager.
- `public/`: Static frontend pages (`app.html`, `driver-portal.html`, `admin.html`).
- `docs/`: Existing feature and integration notes.
- `tests/`: API/auth behavior and regression tests.

## Main Roles
- User (passenger): books rides, tracks trips, updates profile.
- Driver: accepts trips, manages availability/profile, updates ride progress.
- Admin: monitors system, manages drivers/users/bookings, support, settings.

## Core Technology
- Backend: FastAPI + SQLAlchemy async + SQLite (dev).
- Frontend: HTML + Tailwind + plain JavaScript.
- Auth: JWT token flow for user/driver/admin.
- Static hosting: `public/` mounted by backend.

## Current Strengths
- Full flow from booking to completion.
- Admin management UI with broad controls.
- Driver and user profile image upload and persistence.
- Multiple operational modules (coupons, support, analytics, settings).

## Current Constraints
- Large single-file frontends can become harder to maintain.
- Tight coupling between UI and API payload shapes.
- Limited modular separation in frontend scripts.

## Recommended Direction For New Project
- Split frontend by modules/components.
- Introduce typed API contracts and centralized state management.
- Keep role-based portals but share a common design and utilities layer.
