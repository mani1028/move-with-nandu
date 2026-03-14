"""
Google OAuth 2.0 authentication endpoints.
Handles both Authorization Code flow and ID token verification flow.
"""
import os
import uuid
import secrets
import logging
import asyncio
from typing import Optional, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.auth.transport import requests
from google.oauth2 import id_token

from ..database import get_db, User, Driver, generate_custom_id
from ..auth import create_access_token, hash_password
from ..config import settings

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/google", tags=["Google OAuth"])

GOOGLE_CLIENT_ID = str(settings["google_client_id"])
GOOGLE_CLIENT_SECRET = str(settings["google_client_secret"])

# ─── UTILITIES ──────────────────────────────────────────────────────────────

def mask_email(email: str) -> str:
    """Mask email for safe logging. e.g., john@example.com → j***@example.com"""
    if '@' not in email:
        return "***"
    local, domain = email.split('@', 1)
    if len(local) <= 1:
        masked_local = "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 1)
    return f"{masked_local}@{domain}"

# Log configuration status on startup
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    logger.info(f"✅ Google OAuth configured: {GOOGLE_CLIENT_ID[:20]}...")
else:
    logger.warning("⚠️  Google OAuth not fully configured. Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET")


# ─── Schemas ────────────────────────────────────────────────────────────────────

class GoogleTokenIn(BaseModel):
    """Frontend sends Google ID token from Google Sign-In button."""
    id_token: str
    role: str = "user"  # Allow frontend to specify if this is a driver or user login


class GoogleAuthResponse(BaseModel):
    """Response with access token and user info."""
    access_token: str
    token_type: str = "bearer"
    user: dict


# ─── Google ID Token Verification ──────────────────────────────────────────────

async def verify_google_id_token(token: str) -> Optional[dict[str, Any]]:
    """
    Verify Google ID token signature and claims using ThreadPoolExecutor.
    The verify_oauth2_token function is synchronous, so we run it in a thread pool
    to avoid blocking the async event loop.
    Returns decoded token claims or None if invalid.
    """
    try:
        logger.debug(f"Verifying Google ID token (length: {len(token)})")
        
        if not GOOGLE_CLIENT_ID:
            logger.error("❌ GOOGLE_CLIENT_ID not set in environment")
            return None
        
        # Run synchronous token verification in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=1)
        payload = await loop.run_in_executor(
            executor,
            id_token.verify_oauth2_token,
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # Verify token hasn't been tampered with
        if payload.get('aud') != GOOGLE_CLIENT_ID:
            logger.warning(f"❌ Token audience mismatch. Expected: {GOOGLE_CLIENT_ID}, Got: {payload.get('aud')}")
            return None
        
        logger.info(f"✅ Token verified for: {mask_email(payload.get('email', ''))} (sub: {str(payload.get('sub'))[:10]}...)")
        return dict(payload)
        
    except Exception as e:
        logger.error(f"❌ Token verification failed: {str(e)}", exc_info=True)
        return None


# ─── Google Login (ID Token Flow) ──────────────────────────────────────────────

@router.post("/login")
async def google_login(body: GoogleTokenIn, db: AsyncSession = Depends(get_db)):
    """
    Verify Google ID token and create/login user.
    Frontend obtains id_token from Google Sign-In button and sends it here.
    """
    logger.info("🔐 POST /api/auth/google/login - Processing Google login")
    
    payload = await verify_google_id_token(body.id_token)
    if not payload:
        logger.warning("❌ Invalid Google token received")
        raise HTTPException(401, "Invalid Google token")
    
    # Extract Google user info
    google_sub = payload.get('sub')  # unique Google user ID
    email = payload.get('email', '').lower().strip()
    name = payload.get('name', 'User')
    picture = payload.get('picture', '')
    email_verified = payload.get('email_verified', False)
    
    if not email or not google_sub:
        safe_sub = str(google_sub)[:10] if google_sub else "<missing>"
        logger.error(f"❌ Incomplete Google token payload: email={mask_email(email)}, sub={safe_sub}")
        raise HTTPException(400, "Invalid Google token payload")
    
    logger.info(f"📧 Google user: {mask_email(email)}")
    
    # Select correct model based on role
    requested_role = "driver" if body.role == "driver" else "user"
    Model = Driver if requested_role == "driver" else User
    id_prefix = "DRV" if requested_role == "driver" else "USR"
    
    # Find existing user by provider ID (most reliable)
    r = await db.execute(
        select(Model).where(
            (Model.provider == 'google') & (Model.provider_id == google_sub)
        )
    )
    user = r.scalar_one_or_none()
    
    if user:
        logger.info(f"👤 Existing Google user found: {mask_email(str(user.email))} (ID: {str(user.id)})")
    
    # If not found by provider ID, check by email (allow merging/linking)
    if user is None:
        logger.info(f"🔍 Checking for existing user with email: {mask_email(email)}")
        r = await db.execute(select(Model).where(Model.email == email))
        existing_user = r.scalar_one_or_none()
        
        if existing_user and existing_user.provider == 'local':
            # Local user with same email exists
            logger.info(f"🔗 Linking local user {mask_email(email)} to Google account")
            existing_user.provider = 'google'  # type: ignore
            existing_user.provider_id = google_sub
            existing_user.email_verified = email_verified
            if picture:
                if requested_role == "driver":
                    existing_user.profile_pic = picture
                else:
                    existing_user.picture = picture
            user = existing_user
        elif existing_user:
            # User already has provider set; just use them
            logger.info(f"👤 Using existing user: {mask_email(str(existing_user.email))}")
            user = existing_user
        else:
            # Create new user or driver based on role specified in request
            logger.info(f"✨ Creating new Google account: {mask_email(email)} as {body.role}")
            # Generate a placeholder hash for OAuth-only users (passwords not supported)
            oauth_placeholder = hash_password(f"oauth_google_{secrets.token_urlsafe(32)}")
            
            create_kwargs = {
                "id": generate_custom_id(id_prefix),
                "name": name,
                "email": email,
                "phone": "",  # Google doesn't provide phone by default
                "password_hash": oauth_placeholder,  # OAuth placeholder - passwords not supported
                "provider": "google",
                "provider_id": google_sub,
                "email_verified": email_verified,
            }
            if requested_role == "driver":
                create_kwargs["profile_pic"] = picture
            else:
                create_kwargs["picture"] = picture
                create_kwargs["role"] = "user"

            user = Model(**create_kwargs)
            db.add(user)
    
    # Commit changes
    try:
        await db.commit()
        await db.refresh(user)
        logger.info(f"✅ User saved to database: {str(user.id)}")
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Database error during user creation: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Database error: {str(e)}")
    
    # Issue JWT token for app
    user_id_str = str(user.id)
    user_role_str = "driver" if requested_role == "driver" else str(getattr(user, "role", "user") or "user")
    token = create_access_token({"sub": user_id_str, "role": user_role_str})
    logger.info(f"🎫 JWT token issued for user: {user_id_str}")
    
    return GoogleAuthResponse(
        access_token=token,
        token_type="bearer",
        user={
            "id": user_id_str,
            "name": str(user.name),
            "email": str(user.email),
            "phone": str(user.phone or ""),
            "picture": str(getattr(user, "picture", "") or getattr(user, "profile_pic", "")),
            "role": user_role_str,
            "email_verified": bool(user.email_verified),
        }
    )


@router.get("/userinfo")
async def google_userinfo(db: AsyncSession = Depends(get_db)):
    """
    Public endpoint to check Google OAuth setup (returns empty success).
    Frontend can call this to verify OAuth is available.
    """
    logger.info("GET /api/auth/google/userinfo - Checking Google OAuth configuration")
    
    if not GOOGLE_CLIENT_ID:
        logger.error("❌ GOOGLE_CLIENT_ID not configured")
        raise HTTPException(503, "Google OAuth not configured")
    
    logger.info("✅ Google OAuth is configured")
    return {"status": "ok", "google_client_id": GOOGLE_CLIENT_ID}
