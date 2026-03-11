# API Surface Summary

## Auth (`/api/auth`)
- User register/login.
- Driver register/login.
- Google login routes (user and driver paths, where configured).
- Token bootstrap routes (`/me`, `/refresh`, `/logout`).

## User (`/api/users`)
- `GET /me`: user profile.
- `PATCH /me`: update profile data.
- `POST /me/picture`: upload user photo.

## Driver (`/api/drivers`)
- `GET /me`: driver profile.
- `PATCH /me`: update driver profile.
- `POST /me/profile-pic`: upload driver profile photo.
- Status and trip endpoints (`/status`, `/trips/active`, `/my-trips`, etc.).

## Rides (`/api/rides`)
- Create/list rides.
- Lifecycle actions: accept/start/complete/cancel.
- Rating and OTP verification endpoints.
- `GET /live-search`: shared-ride discovery for passenger UI.

## Admin (`/api/admin`)
- Stats: `GET /stats`.
- Bookings: list, force cancel, and patch management.
- Drivers: list and patch management.
- Users: list, patch, delete.
- Coupons: list/create/delete.
- Support: list/respond/resolve.
- Settings: get/update.
- Broadcasts: create/list.
- Admin team CRUD.

## Data Entities (Primary)
- `User`, `Driver`, `Admin`, `Ride`, `SupportTicket`, `Coupon`, `Setting`, `Broadcast`.

## Rebuild Advice
- Define explicit request/response schemas per endpoint in shared docs.
- Introduce versioned APIs (`/api/v1/...`) in next iteration.
- Add centralized error format and validation contract.
