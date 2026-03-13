# Vercel Deployment Guide

## Prerequisites

1. ✅ Code pushed to GitHub (`main` branch)
2. ✅ Vercel project connected to GitHub repository
3. ✅ Environment variables configured in Vercel dashboard

## Required Environment Variables (Set in Vercel Dashboard)

Go to **Settings → Environment Variables** and add:

```env
# JWT & Security
SECRET_KEY=change-me-in-production-to-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Database (PostgreSQL/Supabase)
DATABASE_URL=postgresql+psycopg://user:pass@host:port/database

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_PROFILE_BUCKET=user-profiles
SUPABASE_DRIVER_DOCS_BUCKET=driver-docs
SUPABASE_DRIVER_BUCKET=drivers

# Admin Credentials
ADMIN_EMAIL=admin@nandutravels.com
ADMIN_PASSWORD=your-secure-password

# CORS Configuration
CORS_ORIGINS=https://movewithnandu.vercel.app

# App URL / Deployment
APP_BASE_URL=https://movewithnandu.vercel.app

# Google OAuth 2.0
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://movewithnandu.vercel.app/api/auth/google/callback

# Environment
ENVIRONMENT=production
```

## Deployment Steps

1. **Push code to GitHub**:
   ```bash
   git add -A
   git commit -m "Your message"
   git push origin main
   ```

2. **Vercel auto-deploys** when you push to main (if connected)

3. **Monitor deployment**:
   - Go to Vercel Dashboard
   - Check "Deployments" tab
   - Click latest deployment to see build logs

## Troubleshooting

### Build Logs
Check the Vercel dashboard → Deployments → [latest] → Build Logs for:
- Python dependency installation errors
- Import errors from `api/index.py`
- Environment variable issues

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'asyncpg'`
- **Fix**: Ensure `asyncpg==0.29.0` is in `api/requirements.txt` ✅ (already done)

**Issue**: Database connection fails with "audience mismatch"
- **Fix**: Verify `DATABASE_URL` format is correct in Vercel env vars

**Issue**: `SECRET_KEY` or `ADMIN_PASSWORD` errors
- **Fix**: Ensure these are set in Vercel, not just in local `.env`

**Issue**: CORS errors from frontend
- **Fix**: Verify `CORS_ORIGINS` matches your Vercel domain (or set to `*` temporarily for testing)

### Health Check Endpoints

After deployment, test:
```bash
https://movewithnandu.vercel.app/api/health
https://movewithnandu.vercel.app/api/status
```

Should return JSON with status information.

## Recent Fixes (March 14, 2026)

✅ Added `asyncpg==0.29.0` for async PostgreSQL support  
✅ Added `aiosqlite==3.1.1` for local SQLite fallback  
✅ Fixed Google Sign-In backend integration  
✅ Added explicit buildCommand in vercel.json  

## Notes

- Frontend files in `public/` are automatically served as static assets
- Python API functions in `api/index.py` are serverless functions
- Database pooling is configured for Supabase's transaction pooler (port 6543)
- NullPool is used in serverless to prevent stale connections
