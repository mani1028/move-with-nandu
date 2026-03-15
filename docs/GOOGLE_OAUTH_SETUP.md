# Google OAuth Setup Guide for Move With Nandu

This guide walks you through setting up Google OAuth login/signup from scratch.

## Architecture Overview

- **Frontend**: User clicks "Sign in with Google" → gets ID token from Google
- **Backend**: Receives ID token → verifies signature → creates/finds user in DB → issues JWT
- **Database**: Stores user with `provider='google'` and `provider_id` (Google's unique ID)
- **Session**: App uses your JWT, not Google's token (clean separation)

## Step 1: Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Go to **APIs & Services** → **Credentials**
4. Click **+ Create Credentials** → **OAuth 2.0 Client ID**
5. Choose **Web application**
6. Set **Authorized JavaScript origins**:
   - Development: `http://localhost:8000`
   - Production: `https://yourdomain.com`
7. Set **Authorized redirect URIs**:
   - Development: `http://localhost:8000/api/auth/google/callback`
   - Production: `https://yourdomain.com/api/auth/google/callback`
8. Click **Create** and copy your credentials

8a. **Enable Google+ API**:
   - Go to **APIs & Services** → **Library**
   - Search for "Google+ API"
   - Click **Enable**

## Step 2: Configure Environment Variables

Copy `.env.example` to `.env` and fill in your Google credentials:

```bash
# Copy the template
cp .env.example .env

# Edit .env and add:
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
```

For development, use `http://localhost:8000` as the URI.  
For production, use your actual domain.

## Step 3: Install Dependencies

The required packages are already in `backend/requirements.txt`:

```bash
pip install -r backend/requirements.txt
```

Packages added:
- `google-auth` — Verify Google ID tokens
- `authlib` — OAuth utility library

## Step 4: Database Schema

The `User` table now has OAuth fields:
- `provider` — "local" | "google" | "github" (future)
- `provider_id` — Google's unique subject ID (`sub`)
- `email_verified` — Whether Google verified the email
- `picture` — Profile picture URL from Google
- `phone` — Now nullable (OAuth users may not provide phone)
- `password_hash` — Now nullable (OAuth-only users have no password)

### Migration: Delete Old DB (Development Only)

```bash
# Development: just delete the old DB and restart (schema auto-creates)
rm nandu.db
python app.py
```

The app auto-runs `init_db()` on startup and creates all tables with new schema.

## Step 5: Backend Endpoints

### POST `/api/auth/google/login`

**What it does**: Verify Google ID token and create/login user

**Frontend sends**:
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQifQ..."
}
```

**Backend returns**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid-here",
    "name": "John Doe",
    "email": "john@example.com",
    "picture": "https://example.com/photo.jpg",
    "role": "user",
    "email_verified": true
  }
}
```

**Use your JWT in subsequent requests**:
```
Authorization: Bearer <access_token>
```

### GET `/api/auth/google/userinfo`

**What it does**: Check if Google OAuth is configured

**Returns**:
```json
{
  "status": "ok",
  "google_client_id": "your-client-id.apps.googleusercontent.com"
}
```

## Step 6: Frontend Integration

### Load Google Sign-In SDK

Add to `public/app.html` in the `<head>`:

```html
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

### Add Google Login Button

Add to login form in `public/app.html`:

```html
<!-- Google Sign-In Button -->
<div id="g_id_onload"
     data-client_id="YOUR_GOOGLE_CLIENT_ID"
     data-callback="handleGoogleLogin">
</div>
<div class="g_id_signin" data-type="standard" data-size="large" data-theme="outline"></div>
```

Replace `YOUR_GOOGLE_CLIENT_ID` with your actual client ID (or read from `/api/auth/google/userinfo`).

### Add JavaScript Handler

Add to `<script>` section in `public/app.html`:

```javascript
// Google Sign-In Callback
async function handleGoogleLogin(response) {
    const idToken = response.credential;  // JWT from Google
    
    try {
        // Send to backend
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
        showAuthError('login-error', '⚠️ Google login failed: ' + e.message);
    }
}
```

### One-Tap Sign-In (Optional)

For automatic pop-up on page load:

```javascript
google.accounts.id.initialize({
    client_id: 'YOUR_GOOGLE_CLIENT_ID',
    callback: handleGoogleLogin
});
google.accounts.id.prompt();  // Shows One-Tap UI
```

## Step 7: Test the Flow

### Test Case 1: New User Signs Up with Google

1. Open `http://localhost:8000`
2. Click Google Sign-In button
3. Google popup appears; sign in with your Google account
4. Backend receives ID token
5. Backend creates new user with `provider='google'`
6. You're logged in; redirect to app home

**DB Check**:
```sql
SELECT id, name, email, provider, provider_id FROM users;
-- Should show: provider='google', provider_id='123456789...' (Google's sub)
```

### Test Case 2: Existing Local User Switches to Google

1. You have a local account (email + password)
2. Delete that local account from DB (dev only)
3. Sign up with Google using same email
4. Backend finds existing user by email
5. Backend links them: sets `provider='google'`, `provider_id=<sub>`

### Test Case 3: Logging After Google Signup

1. Go to login page
2. Click Google Sign-In
3. Google recognizes you, auto-logs in
4. Backend finds user by `provider='google'` + `provider_id`
5. You're logged in

## Step 8: Security Checklist

- ✅ ID token verified using Google's public keys (done in `verify_google_id_token()`)
- ✅ Token `aud` claim validated against `GOOGLE_CLIENT_ID` (in verification)
- ✅ `exp` checked (in `id_token.verify_oauth2_token()`)
- ✅ `iss` verified to be Google (in `id_token.verify_oauth2_token()`)
- ✅ HTTPS in production (you enforce this)
- ✅ `GOOGLE_CLIENT_SECRET` never sent to frontend (only backend uses it)
- ⚠️ CORS: adjust `CORS_ORIGINS` for production domain

## Step 9: Production Deployment

1. Update `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` with production credentials
2. Set `GOOGLE_REDIRECT_URI=https://yourdomain.com/api/auth/google/callback`
3. Update Google Cloud Console allowed origins/redirect URIs
4. Update frontend to use production domain
5. Set `CORS_ORIGINS` to production domain
6. Use HTTPS everywhere
7. Store secrets in environment (not `.env` file)
8. Add rate limiting on `/api/auth/google/login` endpoint

## Step 10: Account Linking (Optional Future Feature)

Current behavior: If local user email == Google email, auto-link.

To add explicit linking in settings:

1. Add endpoint: `POST /api/auth/link-provider` (requires JWT)
2. Verify user's  password OR current provider
3. Set new `provider` + `provider_id`
4. Allow unlinking in settings page

## Troubleshooting

### "Invalid Google token"
- Check `GOOGLE_CLIENT_ID` matches in Google Cloud Console
- Verify ID token hasn't expired (typically 1 hour)
- Ensure token sent from same client that created it

### "Email already registered"
- Local user exists with same email but different provider
- Option: Delete local user and re-signup with Google
- Option: Implement account merging flow

### "HTTP 500 on /api/auth/google/login"
- Check server logs: `python app.py` or `backend/error.log`
- Verify database is initialized
- Ensure Google credentials are in `.env`

### Google button doesn't appear
- Verify Google SDK loaded: `<script src="https://accounts.google.com/gsi/client">`
- Check browser console for errors
- Verify `data-client_id` is valid

### Frontend says "apiFetch is not defined"
- Ensure `apiFetch()` function exists in app.html
- Verify global scope (defined outside function)

## References

- [Google Sign-In Docs](https://developers.google.com/identity/gsi/web)
- [ID Token Verification](https://developers.google.com/identity/protocols/oauth2/openid-connect#validatinganidtoken)
- [FastAPI OAuth2](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
