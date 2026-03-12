import os, secrets
import datetime
from typing import cast, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.auth.transport import requests
from google.oauth2 import id_token
from ..database import get_db, User, Driver, Setting, Admin
from ..auth import hash_password, verify_password, create_access_token, decode_token
from ..config import settings
from dotenv import load_dotenv

load_dotenv()
router = APIRouter(prefix="/api/auth", tags=["Auth"])

ADMIN_EMAIL = str(settings["admin_email"])
ADMIN_PASS = str(settings["admin_password"])
GOOGLE_CLIENT_ID = str(settings["google_client_id"])


# ─── Schemas ────────────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    name: str
    email: str
    phone: str
    password: str

class LoginIn(BaseModel):
    email: str
    password: str

class RefreshIn(BaseModel):
    token: str | None = None

class DriverRegisterIn(BaseModel):
    name: str
    email: str
    phone: str
    password: str
    profile_pic: str = ""
    vehicle_type: str = "7 Seater"
    plate: str
    route_pref: str = "Karimnagar"
    ac_pref: bool = True


class DriverGoogleTokenIn(BaseModel):
    id_token: str


# ─── User Register ───────────────────────────────────────────────────────────────

@router.post("/register")
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    # Check duplicate email or phone within users table only
    email_l = body.email.lower().strip()
    phone_s = body.phone.strip()
    r = await db.execute(select(User).where((User.email == email_l) | (User.phone == phone_s)).limit(1))
    if r.scalar_one_or_none():
        raise HTTPException(400, "Email or Phone already registered. Please login.")

    user = User(
        name=body.name.strip(),
        email=body.email.lower().strip(),
        phone=body.phone.strip(),
        password_hash=hash_password(body.password),
        role="user"
    )
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        with open('backend/error.log', 'a', encoding='utf-8') as f:
            f.write('\n=== REGISTER ERROR ===\n')
            f.write(tb)
        raise HTTPException(500, 'Internal server error')

    token = create_access_token({"sub": user.id, "role": "user"})
    created_at_val = cast(Optional[datetime.datetime], user.created_at)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id, 
            "name": user.name, 
            "email": user.email, 
            "phone": user.phone,
            "picture": user.picture,
            "role": user.role or "user",
            "created_at": created_at_val.isoformat() if created_at_val else None
        }
    }


# ─── User Login ─────────────────────────────────────────────────────────────────

@router.post("/login")
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    email = body.email.lower().strip()

    # Admin super-login
    if email == ADMIN_EMAIL.lower() and body.password == ADMIN_PASS:
        r = await db.execute(select(User).where(User.email == email))
        admin_user = r.scalar_one_or_none()
        if admin_user is None:
            # Create admin user on first login
            admin_user = User(
                name="Nandu Admin",
                email=email,
                phone="9999999999",
                password_hash=hash_password(body.password),
                role="admin"
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            # Also ensure an Admin record exists for admin team management
            r2 = await db.execute(select(Admin).where(Admin.email == email).limit(1))
            if not r2.scalar_one_or_none():
                admin_record = Admin(
                    name=admin_user.name,
                    email=admin_user.email,
                    phone=admin_user.phone,
                    password_hash=admin_user.password_hash,
                )
                db.add(admin_record)
                await db.commit()
        
        token = create_access_token({"sub": admin_user.id, "role": "admin"})
        admin_created_at = cast(Optional[datetime.datetime], admin_user.created_at)
        return {
            "access_token": token, 
            "token_type": "bearer",
            "user": {
                "id": admin_user.id, 
                "name": admin_user.name, 
                "email": admin_user.email,
                "phone": admin_user.phone,
                "picture": admin_user.picture,
                "role": "admin",
                "created_at": admin_created_at.isoformat() if admin_created_at else None
            }
        }

    # Search by email or phone
    r = await db.execute(select(User).where((User.email == email) | (User.phone == email)))
    user = r.scalar_one_or_none()
    if user is None:
        raise HTTPException(401, "Invalid credentials (email/phone or password).")
    # user.password_hash is a SQLAlchemy Column typing at module-level; cast for type checker
    hashed = cast(str, user.password_hash or "")
    if not verify_password(body.password, hashed):
        raise HTTPException(401, "Invalid credentials (email/phone or password).")

    role = user.role or "user"
    token = create_access_token({"sub": user.id, "role": role})
    user_created_at = cast(Optional[datetime.datetime], user.created_at)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id, "name": user.name, "email": user.email,
            "phone": user.phone, "picture": user.picture, "role": role,
            "created_at": user_created_at.isoformat() if user_created_at else None
        }
    }


# ─── Driver Register ─────────────────────────────────────────────────────────────

@router.post("/drivers/register")
async def driver_register(body: DriverRegisterIn, db: AsyncSession = Depends(get_db)):
    # Duplicate check for drivers
    email = body.email.lower().strip()
    phone = body.phone.strip()
    plate = body.plate.upper().strip()
    if not phone:
        raise HTTPException(400, "Phone is required for driver registration.")
    if not plate:
        raise HTTPException(400, "Vehicle plate is required for driver registration.")

    # Ensure email/phone uniqueness across drivers, users, and admins
    by_email = await db.execute(select(Driver).where(Driver.email == email).limit(1))
    if by_email.scalar_one_or_none():
        raise HTTPException(400, "Driver with this email already exists.")
    by_phone = await db.execute(select(Driver).where(Driver.phone == phone).limit(1))
    if by_phone.scalar_one_or_none():
        raise HTTPException(400, "Driver with this phone already exists.")

    def _seats_for_type(vt: str) -> int:
        v = vt.lower()
        if any(x in v for x in ('12', 'tempo')): return 12
        if any(x in v for x in ('7', 'innova', 'ertiga', 'suv')): return 7
        if any(x in v for x in ('4', 'mini')): return 4
        if any(x in v for x in ('ambulance',)): return 2
        return 5  # sedan/5-seater default

    driver = Driver(
        name=body.name.strip(),
        email=email,
        phone=phone,
        password_hash=hash_password(body.password),
        profile_pic=body.profile_pic.strip(),
        vehicle_type=body.vehicle_type,
        plate=plate,
        route_pref=body.route_pref,
        ac_pref=body.ac_pref,
        seats_total=_seats_for_type(body.vehicle_type or ''),
    )
    try:
        db.add(driver)
        await db.commit()
        await db.refresh(driver)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        with open('backend/error.log', 'a', encoding='utf-8') as f:
            f.write('\n=== DRIVER REGISTER ERROR ===\n')
            f.write(tb)
        raise HTTPException(500, 'Internal server error')

    token = create_access_token({"sub": driver.id, "role": "driver"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "driver": {
            "id": driver.id, "name": driver.name, "email": driver.email,
            "phone": driver.phone, "vehicle_type": driver.vehicle_type,
            "plate": driver.plate, "route_pref": driver.route_pref,
            "ac_pref": driver.ac_pref, "is_verified": driver.is_verified,
            "status": driver.status, "profile_pic": driver.profile_pic,
            "address": driver.address
        }
    }


# ─── Driver Login ────────────────────────────────────────────────────────────────

@router.post("/drivers/login")
async def driver_login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    email = body.email.lower().strip()
    # Search by email or phone
    r = await db.execute(select(Driver).where((Driver.email == email) | (Driver.phone == email)))
    driver = r.scalar_one_or_none()
    if driver is None or not verify_password(body.password, str(driver.password_hash or "")):
        raise HTTPException(401, "Invalid credentials (email/phone or password).")

    token = create_access_token({"sub": driver.id, "role": "driver"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "driver": {
            "id": driver.id, "name": driver.name, "email": driver.email,
            "phone": driver.phone, "vehicle_type": driver.vehicle_type,
            "plate": driver.plate, "route_pref": driver.route_pref,
            "ac_pref": driver.ac_pref, "is_verified": driver.is_verified,
            "status": driver.status, "rating": driver.rating,
            "jobs_done": driver.jobs_done, "profile_pic": driver.profile_pic,
            "address": driver.address
        }
    }


@router.get("/drivers/google/userinfo")
async def driver_google_userinfo():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured")
    return {"status": "ok", "google_client_id": GOOGLE_CLIENT_ID}


@router.post("/drivers/google/login")
async def driver_google_login(body: DriverGoogleTokenIn, db: AsyncSession = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured")

    try:
        payload = id_token.verify_oauth2_token(
            body.id_token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(401, "Invalid Google token")

    google_sub = payload.get("sub")
    email = (payload.get("email") or "").lower().strip()
    name = payload.get("name") or "Driver"
    picture = payload.get("picture") or ""
    email_verified = bool(payload.get("email_verified", False))
    if not google_sub or not email:
        raise HTTPException(400, "Invalid Google token payload")

    r = await db.execute(select(Driver).where(Driver.provider == "google", Driver.provider_id == google_sub))
    driver = r.scalar_one_or_none()

    if not driver:
        r = await db.execute(select(Driver).where(Driver.email == email))
        existing = r.scalar_one_or_none()
        if existing:
            existing.provider = "google"  # type: ignore
            existing.provider_id = google_sub
            existing.email_verified = email_verified  # type: ignore
            if picture:
                existing.profile_pic = picture
            driver = existing
        else:
            # Generate a placeholder hash for OAuth-only drivers (passwords not supported)
            oauth_placeholder = hash_password(f"oauth_google_{secrets.token_urlsafe(32)}")
            
            driver = Driver(
                name=name,
                email=email,
                phone="",
                password_hash=oauth_placeholder,
                vehicle_type="7 Seater",
                plate="",
                route_pref="Karimnagar",
                ac_pref=True,
                provider="google",
                provider_id=google_sub,
                email_verified=email_verified,
                profile_pic=picture,
            )
            db.add(driver)

    await db.commit()
    await db.refresh(driver)

    token = create_access_token({"sub": driver.id, "role": "driver"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "driver": {
            "id": driver.id,
            "name": driver.name,
            "email": driver.email,
            "phone": driver.phone,
            "vehicle_type": driver.vehicle_type,
            "plate": driver.plate,
            "route_pref": driver.route_pref,
            "ac_pref": driver.ac_pref,
            "is_verified": driver.is_verified,
            "status": driver.status,
            "rating": driver.rating,
            "jobs_done": driver.jobs_done,
            "profile_pic": driver.profile_pic,
            "address": driver.address,
            "provider": driver.provider,
            "doc_status": driver.doc_status,
            "seats_total": driver.seats_total,
            "filled_seats": driver.filled_seats,
            "license_url": driver.license_url,
            "aadhar_url": driver.aadhar_url,
            "rc_url": driver.rc_url,
            "insurance_url": driver.insurance_url,
        },
    }


_oauth_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@router.get("/me")
async def auth_me(
    token: str = Depends(_oauth_optional),
    db: AsyncSession = Depends(get_db)
):
    """Resolve token subject and role for frontend bootstrapping."""
    payload = decode_token(token) if token else None
    if not payload:
        raise HTTPException(401, "Invalid or expired token.")

    uid = payload.get("sub")
    role = payload.get("role")
    if role == "driver":
        r = await db.execute(select(Driver).where(Driver.id == uid))
        driver = r.scalar_one_or_none()
        if not driver:
            raise HTTPException(401, "Driver not found.")
        return {
            "id": driver.id,
            "role": "driver",
            "name": driver.name,
            "email": driver.email,
            "phone": driver.phone,
        }

    r = await db.execute(select(User).where(User.id == uid))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(401, "User not found.")
    user_created_at = cast(Optional[datetime.datetime], user.created_at)
    return {
        "id": user.id,
        "role": user.role or "user",
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "picture": user.picture,
        "created_at": user_created_at.isoformat() if user_created_at else None,
    }


@router.post("/refresh")
async def refresh_token(
    body: RefreshIn,
    bearer_token: str = Depends(_oauth_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Issue a new JWT from an existing valid token.
    Supports either Authorization header or body.token for easier migration.
    """
    token = bearer_token or body.token
    payload = decode_token(token) if token else None
    if not payload:
        raise HTTPException(401, "Invalid or expired token.")

    uid = payload.get("sub")
    role = payload.get("role", "user")
    if not uid:
        raise HTTPException(401, "Invalid token payload.")

    if role == "driver":
        r = await db.execute(select(Driver).where(Driver.id == uid))
        if not r.scalar_one_or_none():
            raise HTTPException(401, "Driver no longer exists.")
    else:
        r = await db.execute(select(User).where(User.id == uid))
        user = r.scalar_one_or_none()
        if not user:
            raise HTTPException(401, "User no longer exists.")
        role = user.role or "user"

    new_token = create_access_token({"sub": uid, "role": role})
    return {"access_token": new_token, "token_type": "bearer"}


@router.post("/logout")
async def logout():
    """JWT logout is handled client-side by deleting the token."""
    return {"ok": True}
