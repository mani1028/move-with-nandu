# Feature Inventory

## Passenger Features
- Login/register (email + Google where configured).
- Shared and full ride booking.
- Fare estimate and coupon application.
- Live rider discovery/search.
- Ride history and status tracking.
- Profile management (name, phone, photo).

## Driver Features
- Login/register (email + Google where configured).
- Onboarding with required profile photo.
- Online/offline status control.
- Active trip handling (accept/start/complete).
- Profile and vehicle details management.
- Document metadata and verification status.

## Admin Features
- Live booking feed and monitor table.
- Force cancel booking.
- Driver fleet management (verify/block/docs/seats).
- Customer management (view/edit/delete).
- Booking management (edit status, fare, passengers, driver assignment).
- Coupon create/list/delete.
- Support ticket response and resolve.
- Settings (surge, maintenance, feature toggles).
- Broadcast messaging.
- Analytics (revenue/trips/service split/top drivers).
- Admin team CRUD.

## Platform/Operational Features
- JWT auth and role checks.
- Basic state machine for ride status transitions.
- Realtime admin notification hooks via websocket manager.
- Upload storage under `public/uploads/` for profile images.

## Optional/Partial Features Not Fully Mature
- Advanced audit logs for admin actions.
- Granular admin role permissions.
- Bulk operations in admin UI.
- Deep observability/telemetry.
