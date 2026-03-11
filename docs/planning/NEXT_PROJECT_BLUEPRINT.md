# Next Project Blueprint

## Goal
Build a cleaner, scalable v2 based on current production behavior while reducing maintenance overhead.

## Phase 1: Foundation
- Choose architecture:
  - Backend API service (FastAPI or similar) with clear module boundaries.
  - Frontend framework split by role-based apps (passenger/driver/admin).
- Define shared domain model and API contracts first.
- Establish environment strategy for dev/staging/prod.

## Phase 2: Data and Auth
- Migrate from ad-hoc updates to strict schemas and migrations.
- Add audit logging tables for admin actions.
- Add permission layers for admin roles (super admin, ops admin, support admin).

## Phase 3: Feature Porting Order
1. Auth and profile flows.
2. Ride lifecycle and state machine.
3. Driver operations.
4. Admin core operations.
5. Coupons, support, analytics, broadcasts.

## Phase 4: UX and Reliability
- Componentize UI and remove very large single-script pages.
- Add reusable data table + modal patterns.
- Add loading/error/empty states consistently.
- Add background jobs and retry policy for notifications.

## Phase 5: Testing and Observability
- Unit tests for pricing, transitions, auth guards.
- API integration tests for major role flows.
- Add structured logs and request tracing.
- Add dashboard metrics (errors, latency, booking funnel).

## Suggested Directory Structure (New)
- `apps/passenger-web`
- `apps/driver-web`
- `apps/admin-web`
- `services/api`
- `packages/shared-types`
- `packages/ui-kit`
- `infra/`

## Migration Checklist
- Preserve existing IDs and critical tables.
- Keep compatibility layer for legacy clients during rollout.
- Roll out by role in stages (admin first, then driver, then passenger).

## Immediate Next Step
Create a detailed PRD from `FEATURE_INVENTORY.md`, then map each feature to v2 modules and milestones.
