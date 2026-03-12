# Move With Nandu

Ride-booking platform with separate passenger, driver, and admin portals.

## Modules
- `backend/`: FastAPI backend (auth, rides, drivers, users, admin, services)
- `public/`: Web frontends (`app.html`, `driver-portal.html`, `admin.html`)
- `tests/`: test scripts and regression checks
- `docs/`: feature notes, integration guides, planning docs

## Core Features
- Passenger booking: shared/full rides, coupons, live rider search
- Driver operations: onboarding, profile photo, document upload, trip lifecycle
- Admin portal: manage users/drivers/bookings, support, settings, analytics
- Verification workflow: driver uploads required docs; admin approves/rejects and verified badge updates accordingly

## Driver Verification Flow
1. Driver registration requires profile photo and 4 documents:
   - Driving License
   - Aadhar Card
   - Vehicle RC
   - Insurance
2. Driver docs are uploaded to backend storage and marked `pending`.
3. Admin reviews documents in admin portal and sets approval.
4. When approved, driver receives verified badge (`is_verified = true`).

## Local Setup
1. Create environment file:
   - Copy `.env.example` to `.env` and update values.
   - Leave `DATABASE_URL` as SQLite for fast local dev, or switch it to your Supabase Postgres URL to test production DB behavior locally.
2. Install backend dependencies:
```bash
pip install -r backend/requirements.txt
```
3. Run server:
```bash
python app.py
```
4. Open portals:
- Passenger: `http://localhost:8000/app.html`
- Driver: `http://localhost:8000/driver-portal.html`
- Admin: `http://localhost:8000/admin.html`

## Notes
- Uploads use `public/uploads/` locally, and switch to Supabase Storage automatically when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set.
- Dev database defaults to SQLite (`nandu.db`) unless `DATABASE_URL` is changed.
- Frontend API calls default to same-origin, so localhost and Vercel do not require code changes.
- For planning a v2 rebuild, see files under `docs/planning/`.
