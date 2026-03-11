# 🧪 Google Sign-In Testing & Debugging Guide

## ✅ Quick Start - Testing Google Sign-In

### Step 1: Start the Backend Server
```bash
cd d:\projects\travel
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
==========================================
🚀 STARTING NANDU TRAVELS API SERVER
==========================================

🔐 Google OAuth Configuration Check:
  ✅ GOOGLE_CLIENT_ID: 299504205018-2il56arfnldacvu1...
  ✅ GOOGLE_CLIENT_SECRET: ********************
  ✅ GOOGLE_REDIRECT_URI: http://localhost:8000/api/auth/google/callback

🔓 CORS Configuration:
  ✅ Allowed origins: http://localhost:5000, http://127.0.0.1:5500, http://localhost:8000

💾 Database initialized
✅ All startup checks passed!
==========================================
📡 API Server Ready — http://localhost:8000/docs
==========================================
```

### Step 2: Test Backend Google OAuth Endpoint
```bash
# Test the configuration endpoint
curl http://localhost:8000/api/auth/google/userinfo

# Expected response:
# {"status":"ok","google_client_id":"299504205018-2il56arfnldacvu1fss7pg8vu28d3apj.apps.googleusercontent.com"}
```

### Step 3: Test Frontend
1. Open the app: `http://localhost:5500/public/app.html` or wherever frontend is served
2. Open Developer Tools (F12)
3. Go to Console tab
4. Click "Continue with Google" button
5. Check console for logs like:
   - ✅ Google Client ID loaded
   - 📨 Received Google credential
   - ✅ Login successful

---

## 🐛 Debugging Checklist

### Check Console Logs
Open browser DevTools (F12) → Console tab:

| Log Pattern | Meaning | Action |
|---|---|---|
| ❌ "Google Sign-In library failed to load" | Google script didn't load | Check network tab, refresh page |
| "One Tap unavailable, using button fallback" | Normal behavior | Click Google button when prompted |
| 📨 "Received Google credential" | User completed Google login | Good sign, check backend response |
| ✅ "Login successful!" | Everything worked | Should redirect to main app |
| ❌ "Backend Error (401)" | Invalid token | Check Client ID in .env |
| ❌ "CORS error" in Network tab | Frontend URL not whitelisted | Add to .env CORS_ORIGINS |

### Check Backend Logs
Backend should show logs like:
```
INFO: GET /api/auth/google/userinfo - Checking Google OAuth configuration
INFO: ✅ Google OAuth is configured

INFO: 🔐 POST /api/auth/google/login - Processing Google login
INFO: Verifying Google ID token
INFO: ✅ Token verified for: user@gmail.com (sub: 123456789...)
INFO: 👤 Existing Google user found: user@gmail.com
INFO: 🎫 JWT token issued for user: abc-def-ghi-jkl
```

---

## 🔍 Network Debugging

### Check Network Requests (DevTools → Network tab)

1. **Request to `/api/auth/google/userinfo`**
   - Should return: `200 OK` with JSON
   - Should have `google_client_id` field

2. **Request to `/api/auth/google/login`**
   - Method: `POST`
   - Body: `{"id_token": "eyJhbGc..."}`
   - Response should be `200 OK` with:
     ```json
     {
       "access_token": "eyJhbGc...",
       "token_type": "bearer",
       "user": {
         "id": "abc-123",
         "name": "User Name",
         "email": "user@gmail.com",
         "picture": "https://...",
         "role": "user",
         "email_verified": true
       }
     }
     ```

### Check CORS Headers
In Network tab, click on `/api/auth/google/login` response:
- Look for header: `Access-Control-Allow-Origin: *` or your frontend URL

---

## 🔧 Common Issues & Solutions

### Issue: "Google Sign-In library not loaded"
**Cause**: Google Script failed to load  
**Solution**:
1. Check network connectivity
2. Try refreshing page
3. Check if browser blocks google.com scripts
4. Try in Incognito mode
5. Check if CSP headers block external scripts

### Issue: "Invalid Google token" Error
**Cause**: GOOGLE_CLIENT_ID in .env doesn't match frontend  
**Solution**:
1. Verify GOOGLE_CLIENT_ID in `.env` is correct
2. Check it matches the one in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
3. Make sure you copied the full ID (not just first part)
4. Restart backend server after changing .env

### Issue: CORS Error in Console
**Error**: `Access to XMLHttpRequest at 'http://localhost:8000/api/auth/google/login' from origin 'http://localhost:5500' has been blocked by CORS policy`

**Solution**:
1. Edit `.env` file
2. Add your frontend URL to CORS_ORIGINS:
   ```
   CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:5500,http://localhost:8000,http://localhost:3000
   ```
3. Restart backend server

### Issue: Backend Returns 500 Error
**Cause**: Database error or invalid token payload  
**Solution**:
1. Check backend logs for specific error
2. Verify database is working: `curl http://localhost:8000/api/status`
3. Try with a fresh Google login (clear cache on accounts.google.com)
4. Verify .env GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are both set

---

## 📊 Testing Different Scenarios

### Scenario 1: New User (Never signed up before)
1. Click "Continue with Google"
2. Complete Google sign-in
3. Fill out profile (name, phone)
4. Should be logged in with new account

**What to check**:
- Backend logs should show: "✨ Creating new Google user"
- User should appear in database

### Scenario 2: Existing Google User
1. Click "Continue with Google"
2. Complete Google sign-in
3. Should directly go to main app

**What to check**:
- Backend logs should show: "👤 Existing Google user found"
- User should go directly to booking screen

### Scenario 3: Local User → Google Link
1. Register with email/password (if implemented)
2. Log out
3. Try "Continue with Google" with same email
4. Should auto-link accounts

**What to check**:
- Backend logs should show: "🔗 Linking local user to Google account"
- User can now log in with either method

---

## 🧮 Manual Token Verification (Advanced)

To manually verify a Google token:

### Step 1: Get a valid token from Google
(You would get this from the Google Sign-In button click)

### Step 2: Decode and verify
```bash
# Install python google-auth library
pip install google-auth

# In Python:
from google.auth.transport import requests
from google.oauth2 import id_token

token = "eyJhbGc..."  # Token from frontend
client_id = "299504205018-2il56arfnldacvu1fss7pg8vu28d3apj.apps.googleusercontent.com"

try:
    payload = id_token.verify_oauth2_token(token, requests.Request(), client_id)
    print("✅ Token valid!")
    print(f"User: {payload.get('email')}")
    print(f"Sub: {payload.get('sub')}")
except Exception as e:
    print(f"❌ Token invalid: {e}")
```

---

## 📝 Test Cases

### Test Case 1: Google Sign-In Flow
**Steps**:
1. Start backend server
2. Open app in browser
3. Click "Continue with Google" button
4. Complete Google authentication
5. Fill profile if needed

**Expected**: User logs in successfully  
**Actual**: [Document result here]

### Test Case 2: Error Handling
**Steps**:
1. Stop backend server
2. Click "Continue with Google"

**Expected**: Error message about backend not running  
**Actual**: [Document result here]

### Test Case 3: CORS Test
**Steps**:
1. Change CORS_ORIGINS in .env to exclude current frontend URL
2. Restart backend
3. Try Google Sign-In

**Expected**: CORS error in console    
**Actual**: [Document result here]

---

## 📞 Support

If Google Sign-In is still not working after these steps:

1. **Collect Information**:
   - Browser console logs (screenshot)
   - Backend console logs (screenshot)
   - Network tab showing the exact request/response
   - Your frontend URL and port

2. **Check Configuration**:
   - Is backend running? (`curl http://localhost:8000/api/status`)
   - Is .env correctly formatted?
   - Are GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET set?

3. **Test Isolation**:
   - Test with curl: `curl http://localhost:8000/api/auth/google/userinfo`
   - Manually verify token with Python script above
   - Test from different browser/incognito mode

---

**Last Updated**: 2026-03-11  
**Version**: 2.0 (Enhanced Error Handling)
