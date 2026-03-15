# Deployment Guide – Vercel + Supabase

## Overview

This app is production-ready with:
- **Database**: Supabase PostgreSQL (async SQLAlchemy)
- **Storage**: Supabase Storage buckets for persistent uploads on Vercel
- **Frontend**: Vercel static hosting
- **Backend**: Vercel serverless functions

---

## Supabase Setup

### 1. Create Project & Get Credentials

1. Go to [Supabase Console](https://app.supabase.com)
2. Create a new project
3. Copy credentials from **Settings > Database**:
   - **Connection String (Transaction Pooler)**: Format `postgresql+asyncpg://postgres.PROJECT_ID:PASSWORD@aws-X.pooler.supabase.com:6543/postgres`
   - **Service Role Secret**: From **Settings > API**
4. Set your public app URL for each environment:
   - Local: `APP_BASE_URL=http://localhost:8000`
   - Vercel: `APP_BASE_URL=https://your-project.vercel.app`

### 2. Create Storage Buckets

In Supabase **Storage**, create and set to **Public**:
- `user-profiles` — driver & user profile pictures
- `driver-docs` — driver verification documents (license, aadhar, RC, insurance)

### 3. Run Initial Migration (Local)

```bash
# Set environment variables locally
export DATABASE_URL="postgresql+asyncpg://postgres.YOUR_ID:PASSWORD@aws-X.pooler.supabase.com:6543/postgres"
export SUPABASE_URL="https://YOUR_ID.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="YOUR_SERVICE_ROLE_KEY"
export APP_BASE_URL="http://localhost:8000"
export ENVIRONMENT=development

# Initialize database tables
python scripts/init_db.py
```

Expected output:
```
🗄️  DATABASE INITIALIZATION
Environment: production
Database: postgresql+asyncpg://...

📋 Creating tables...
✅ Tables created successfully

⚙️  Initializing default settings...
  + Setting: surge_multiplier = 1.0
  + Setting: auto_assign = true
  ...

✅ Database initialization complete!
```

---

## Vercel Deployment

### 1. Push Code to GitHub

```bash
git add .
git commit -m "Production-ready with Supabase"
git push origin main
```

### 2. Connect to Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **Add New > Project**
3. Import your GitHub repository
4. Set **Root Directory** to `travel` (or leave blank if repo root is the project)

### 3. Environment Variables

In Vercel **Project Settings > Environment Variables**, add:

```
DATABASE_URL=postgresql+asyncpg://postgres.YOUR_ID:PASSWORD@aws-X.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://YOUR_ID.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci... (full Service Role key)
ENVIRONMENT=production
MAX_FILE_SIZE_BYTES=5242880
APP_BASE_URL=https://movewithnandu.vercel.app
CORS_ORIGINS=https://movewithnandu.vercel.app
SECRET_KEY=your-long-random-secret-here
ADMIN_PASSWORD=replace-the-default-admin-password
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI=https://movewithnandu.vercel.app/api/auth/google/callback
SUPABASE_PROFILE_BUCKET=user-profiles
SUPABASE_DRIVER_DOCS_BUCKET=driver-docs
```

**⚠️ Important**: Copy the exact values from:
- Supabase **Settings > Database** for `DATABASE_URL`
- Supabase **Settings > API** for `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- Google Cloud Console for `GOOGLE_CLIENT_*`

### 4. Deploy

Click **Deploy** in Vercel. The build will:

1. Install Python dependencies → `pip install -r backend/requirements.txt`
2. Run `scripts/init_db.py` → creates all tables
3. Route all requests through `api/index.py`, which serves both `/api/*` and static frontend files via FastAPI

Expected log output in Vercel:
```
🗄️  DATABASE INITIALIZATION
✅ Tables created successfully
⚙️  Initializing default settings...
✅ Database initialization complete!

🚀 STARTING NANDU TRAVELS API SERVER
💾 Database initialized
✅ All startup checks passed!
📡 API Server Ready
```

---

## Testing Deployment

After Vercel finishes deploying:

### 1. Test API Health
```bash
curl https://movewithnandu.vercel.app/api/health
# Output: {"status":"ok"}
```

### 2. Test Database Connection
```bash
curl https://movewithnandu.vercel.app/api/status
# Output: {"status":"running", "app":"Move With Nandu API", ...}
```

### 2b. Test Upload Storage Path
Upload a user or driver image locally and in Vercel:
- Local should return `/uploads/...`
- Vercel should return `https://<project>.supabase.co/storage/v1/object/public/...`

### 3. Test Google OAuth
Visit your frontend at `https://movewithnandu.vercel.app` and try Google login. Check **browser Console** for any errors.

---

## Troubleshooting

### Table Creation Failed

**Symptom**: Database initialization fails with "relation does not exist"

**Fix**:
1. Verify `DATABASE_URL` is set correctly (ask: Is it async format `postgresql+asyncpg://...`?)
2. Check Supabase console → **Tables** tab to see if tables exist
3. If tables are missing, re-run locally:
   ```bash
   python scripts/init_db.py
   ```

### Google OAuth Returns 404

**Symptom**: "Failed to load resource: /api/auth/google/userinfo returned 404"

**Fix**:
1. Check that `CORS_ORIGINS` includes your frontend domain
2. Verify `GOOGLE_REDIRECT_URI` in `.env` matches the one in Google Cloud Console
3. Test API directly: `curl https://movewithnandu.vercel.app/api/auth/google/userinfo`

### File Uploads Fail

**Symptom**: "File upload failed" or image doesn't appear in frontend

**Fix**:
1. Verify Supabase buckets exist and are **Public**:
   - `user-profiles` (public)
   - `driver-docs` (public)
2. Check `SUPABASE_SERVICE_ROLE_KEY` is correct (not the publishable key)
3. Check file size < 5MB (or adjust `MAX_FILE_SIZE_BYTES`)

---

## Local Development

To test locally with Supabase:

```bash
# 1. Set environment
export ENVIRONMENT=development
export DATABASE_URL="postgresql+asyncpg://postgres.YOUR_ID:PASSWORD@..."
export SUPABASE_URL="https://YOUR_ID.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="eyJhbGci..."
export APP_BASE_URL="http://localhost:8000"

# 2. Initialize DB
python scripts/init_db.py

# 3. Run app
python -m uvicorn backend.main:app --reload
```

Or use SQLite locally (default):
```bash
# No environment setup needed; will use SQLite + local /uploads folder
python -m uvicorn backend.main:app --reload
```

---

## Monitoring

### Real-time Logs in Vercel
```
Project > Deployments > (click latest) > Logs (tab)
```

### Database Monitoring
In Supabase **Database > Monitoring**:
- Check query performance
- View active connections
- Monitor storage usage

### Storage Quotas
In Supabase **Home**, check:
- Database size (free tier: 500MB)
- Storage size (free tier: 1GB)

---

## Next Steps

- [ ] Custom domain (update `CORS_ORIGINS`, `GOOGLE_REDIRECT_URI`, frontend API URL)
- [ ] Set up admin user via dashboard
- [ ] Configure analytics/monitoring
- [ ] Enable Row-Level Security (RLS) for sensitive tables
- [ ] Set up automated backups
