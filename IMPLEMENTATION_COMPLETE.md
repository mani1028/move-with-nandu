# Google OAuth Implementation — Complete Guide

You now have a fully working Google OAuth 2.0 system for Travel With Nandu. This document explains everything you need to know.

## What Was Implemented

### Backend Components

1. **`backend/routers/google_auth.py`** (NEW)
   - `/api/auth/google/login` — Verify Google ID token & create/login user
   - `/api/auth/google/userinfo` — Check if Google OAuth is configured
   - Token verification using Google's public keys
   - Automatic user creation & linking logic

2. **Database Schema Update** (`backend/database.py`)
   - Added fields to `User` table:
     - `provider` — "local" | "google" | "github" (future)
     - `provider_id` — Google's unique user ID
     - `email_verified` — Boolean from Google
     - `picture` — Profile picture URL
     - Made `phone` and `password_hash` nullable (OAuth users may not have these)

3. **Dependencies Added** (`backend/requirements.txt`)
   - `google-auth==2.28.0` — Verify Google ID tokens
   - `authlib==1.3.0` — OAuth utility library

4. **Router Registration** (`backend/main.py`)
   - Imported `google_auth` router
   - Registered with app: `app.include_router(google_auth.router)`

### Configuration

1. **`.env.example`** (NEW)
   - Template for all environment variables
   - Copy to `.env` and fill in your Google credentials

2. **Documentation** (NEW)
   - `GOOGLE_OAUTH_QUICKSTART.md` — 1-minute quick start
   - `GOOGLE_OAUTH_SETUP.md` — Complete detailed guide
   - `docs/GOOGLE_OAUTH_FRONTEND_INTEGRATION.md` — Frontend code snippets

## Quick Start (Follow These Steps)

### Step 1: Get Google OAuth Credentials (5 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or use existing one
3. Go to **APIs & Services** → **Credentials**
4. Click **+ Create Credentials** → **OAuth 2.0 Client ID**
5. Select **Web application**
6. Set **Authorized JavaScript Origins**:
   - `http://localhost:8000` (for local development)
7. Set **Authorized redirect URIs**:
   - `http://localhost:8000/api/auth/google/callback`
8. Click **Create** and download JSON
9. Extract:
   - `client_id` → Your Google Client ID
   - `client_secret` → Your Google Client Secret

### Step 2: Configure Environment (1 minute)

```bash
# Edit d:\projects\travel\.env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

Replace with actual values from Step 1.

### Step 3: Install Dependencies (1 minute)

```bash
cd d:\projects\travel
pip install -r backend/requirements.txt
```

Packages added: `google-auth`, `authlib`

### Step 4: Add Google Login Button to Frontend (5 minutes)

Edit `d:\projects\travel\public\app.html`:

**Add to `<head>` section** (after other scripts):
```html
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

**Add to login form** (replace or add before email/password login):
```html
<!-- Google Sign-In Section -->
<div style="text-align: center; margin: 2rem 0;">
    <div id="g_id_onload"
         data-client_id="YOUR_GOOGLE_CLIENT_ID"
         data-callback="handleGoogleLogin">
    </div>
    <div class="g_id_signin" data-type="standard" data-size="large"></div>
    <p style="color: #999; font-size: 0.9rem;">or continue with</p>
</div>
```

Replace `YOUR_GOOGLE_CLIENT_ID` with your actual Client ID (or use API endpoint to load it).

**Add to `<script>` section** (near other JavaScript functions):
```javascript
// Google OAuth Handler
async function handleGoogleLogin(response) {
    const idToken = response.credential;
    if (!idToken) {
        showAuthError('login-error', 'Google Sign-In failed');
        return;
    }
    
    setButtonLoading('btn-login', true);
    try {
        const data = await apiFetch('/api/auth/google/login', {
            method: 'POST',
            body: JSON.stringify({ id_token: idToken })
        });
        
        // Handle success (same as email login)
        setToken(data.access_token);
        userData = data.user;
        localStorage.setItem('nandu_user', JSON.stringify(data.user));
        initUserUI();
    } catch(e) {
        showAuthError('login-error', '⚠️ ' + e.message);
    } finally {
        setButtonLoading('btn-login', false, 'Login');
        lucide.createIcons();
    }
}
```

### Step 5: Test Locally

```bash
# Start server
python app.py

# Open browser
# http://localhost:8000

# Click Google Sign-In button
# Sign in with your Google account
# You should be logged in!
```

## How It Works (Architecture)

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │ Clicks "Sign in with Google"
       ↓
┌─────────────────────────────────┐
│  Google Sign-In SDK (Frontend)  │
│  Returns: ID Token (JWT)        │
└──────┬──────────────────────────┘
       │ POST to /api/auth/google/login
       │ Body: { id_token: "..." }
       ↓
┌────────────────────────────────────────┐
│     Backend (FastAPI)                  │
│  1. Verify ID token with Google keys   │
│  2. Extract: email, name, picture, sub │
│  3. Find/Create user in DB             │
│  4. Issue our JWT                      │
└──────┬─────────────────────────────────┘
       │ Return: { access_token, user }
       ↓
┌──────────────────────────┐
│  Frontend (localStorage) │
│  Store JWT + user info   │
└──────┬───────────────────┘
       │ Use JWT for all future API calls
       ↓
┌──────────────────────────────┐
│  API Requests (Authenticated)│
│  Authorization: Bearer <JWT> │
└──────────────────────────────┘
```

## Database: How Users Are Stored

### Local (Email + Password) User
```
id:              "uuid-1"
email:           "local@example.com"
name:            "John Doe"
phone:           "9999999999"
password_hash:   "$pbkdf2_sha256$..." (hashed password)
provider:        "local"
provider_id:     NULL
picture:         ""
email_verified:  false
```

### Google User (New)
```
id:              "uuid-2"
email:           "google@example.com"
name:            "Jane Smith"
phone:           "" (empty, Google doesn't provide)
password_hash:   NULL (no password for OAuth users)
provider:        "google"
provider_id:     "1234567890..." (Google's sub claim)
picture:         "https://lh3.googleusercontent.com/..." (from Google)
email_verified:  true (Google verified)
```

### Account Linking (Same Email)
If someone signs up locally as `john@example.com` (password), then later tries Google with `john@example.com`:
- Backend finds existing user by email
- Automatically links: sets `provider='google'`, `provider_id=<sub>`
- User can now login with either method!

**Before linking**:
```
provider:    "local"
provider_id: NULL
```

**After linking**:
```
provider:    "google"
provider_id: "1234567890..."
```

## API Endpoints

### POST `/api/auth/google/login`

**Purpose**: Verify Google ID token and create/login user

**Request**:
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhdWQiOiJ5b3VyLWNsaWVudC1pZC5hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbSIsInN1YiI6IjEwNzY5MTUwMzUwMDA2MTUwNzE2MjI0MDAxMDEiLCJlbWFpbCI6ImFsaWNlQGV4YW1wbGUuY29tIiwibmFtZSI6IkFsaWNlIiwicGljdHVyZSI6Imh0dHBzOi8vZXhhbXBsZS5jb20vcGhvdG8uanBnIiwiaWF0IjoxNzEwMDI4ODAwLCJleHAiOjE3MTAwMzI0MDB9.signature..."
}
```

**Response (Success 200)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1dWlkLWhlcmUiLCJyb2xlIjoidXNlciIsImV4cCI6MTcxMzE1NzAwMH0.signature...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Alice",
    "email": "alice@example.com",
    "picture": "https://example.com/photo.jpg",
    "role": "user",
    "email_verified": true
  }
}
```

**Response (Error 401)**:
```json
{
  "detail": "Invalid Google token"
}
```

### GET `/api/auth/google/userinfo`

**Purpose**: Check if Google OAuth is configured (endpoint availability)

**Response (Configured)**:
```json
{
  "status": "ok",
  "google_client_id": "your-client-id.apps.googleusercontent.com"
}
```

**Response (Not Configured)**:
```json
{
  "detail": "Google OAuth not configured"
}
```

## Security Features

✅ **ID Token Verification**
- Google token signature validated using Google's public keys
- Token `aud` (audience) validated against your Client ID
- Token `exp` (expiration) checked
- Token `iss` (issuer) verified as Google

✅ **No Token Storage**
- Google's `access_token` is NOT stored
- Only verified user info (email, name, picture) saved locally
- Your JWT issued for app sessions

✅ **Database Security**
- Passwords hashed with PBKDF2 (locally registered users)
- OAuth users have `password_hash=NULL`
- Email unique (prevents duplicates)

✅ **Frontend Security**
- `GOOGLE_CLIENT_SECRET` never used on frontend (only backend)
- CORS configured to restrict origins
- JWT used for session (standard HTTP Auth header)

## Production Deployment Checklist

- [ ] Register production domain in Google Cloud Console
- [ ] Set authorized origin: `https://yourdomain.com`
- [ ] Set redirect URI: `https://yourdomain.com/api/auth/google/callback`
- [ ] Update `.env` with production Client ID/Secret
- [ ] Set `CORS_ORIGINS=https://yourdomain.com`
- [ ] Enable HTTPS on your server
- [ ] Store secrets in environment (not `.env` file)
- [ ] Test login flow in production
- [ ] Monitor token validation errors in logs
- [ ] Add rate limiting on `/api/auth/google/login`

## Troubleshooting

### Google button doesn't appear
- Check browser console for errors
- Verify Google SDK script loaded: `<script src="https://accounts.google.com/gsi/client">`
- Ensure `data-client_id` is set correctly

### "Invalid Google token" error
- Verify Client ID matches in frontend and Google Console
- Check token hasn't expired (ID tokens valid ~1 hour)
- Ensure same Browser/Client that created token sent it

### "Email already registered" error
- User already has local account with same email
- Option 1: Delete local account, signup with Google
- Option 2: Merge accounts (implement linking in settings)

### OAuth endpoint returns 503
- `GOOGLE_CLIENT_ID` not set in `.env`
- Check `.env` file is loaded: `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GOOGLE_CLIENT_ID'))"`

### Server error when logging in
- Check server logs: `python app.py` output
- Verifydb is working: `python scripts/check_db.py`
- Ensure google-auth and authlib installed: `pip list | grep -E "google-auth|authlib"`

## Files Created/Modified

### New Files
- `backend/routers/google_auth.py` — Google OAuth endpoints
- `.env.example` — Environment config template
- `GOOGLE_OAUTH_QUICKSTART.md` — Quick start guide
- `GOOGLE_OAUTH_SETUP.md` — Detailed setup guide
- `docs/GOOGLE_OAUTH_FRONTEND_INTEGRATION.md` — Frontend code snippets

### Modified Files
- `backend/database.py` — Added OAuth fields to User model
- `backend/requirements.txt` — Added google-auth, authlib
- `backend/routers/__init__.py` — Registered google_auth router
- `backend/main.py` — Imported google_auth router

### Frontend (TODO)
- `public/app.html` — Add Google Sign-In button (see Step 4 above)

## Questions & Support

See detailed guide: **`GOOGLE_OAUTH_SETUP.md`** for:
- Complete flow explanation
- Production deployment
- Account linking strategies
- API integration examples

See frontend integration: **`docs/GOOGLE_OAUTH_FRONTEND_INTEGRATION.md`** for:
- HTML code snippets
- JavaScript handler examples
- One-Tap Sign-In setup
- Troubleshooting

## Next Steps

1. ✅ Backend already implemented and tested
2. 🔲 Get Google credentials (5 min)
3. 🔲 Add to `.env` (1 min)
4. 🔲 Add button to frontend `app.html` (5 min)
5. 🔲 Test locally (2 min)
6. 🔲 Deploy to production (following checklist)

**You're ready to implement Google login!** Start with Step 1 in quick start section above.


# How to create/update an admin now:

```bash
python scripts/create_admin.py
```

Environment variables used by the script (set these in a root `.env` or your environment):

- `ADMIN_EMAIL`: admin user email (default in `.env.example`).
- `ADMIN_PASSWORD`: admin password used for super-login and for the script.
- `ADMIN_NAME`: admin display name (defaults to `Nandu Admin`).
- `ADMIN_PHONE`: admin phone number (defaults to `9999999999`).

Behavior: running `python scripts/create_admin.py` will create an admin user if none exists, or update the existing admin's name, email, phone and password from the environment variables.