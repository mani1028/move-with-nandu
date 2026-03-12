import os
import random
import string
from datetime import datetime, timezone
from sqlalchemy import (Column, String, Integer, Float, Boolean,
                        DateTime, Text, ForeignKey, create_engine, text)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from .config import settings

load_dotenv()

# ─── DATABASE CONFIGURATION ────────────────────────────────────────────────────

_ENVIRONMENT = str(settings["environment"])
DATABASE_URL = str(settings["database_url"])

# Vercel may use newer Python runtimes where asyncpg wheels can be unavailable.
# Use psycopg async driver for PostgreSQL URLs to keep startup compatible.
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)

engine_kwargs: dict[str, object] = {"echo": False}

if DATABASE_URL.startswith("postgresql"):
    engine_kwargs["pool_pre_ping"] = True

    # Supabase transaction pooler (port 6543 / pooler hostname) benefits from
    # NullPool in serverless-style workloads to avoid stale pooled connections.
    if "pooler.supabase.com" in DATABASE_URL or ":6543/" in DATABASE_URL:
        engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(DATABASE_URL, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


# ─── UTILS ─────────────────────────────────────────────────────────────────────

def generate_custom_id(prefix: str) -> str:
    """Generates an ID in the format: PREFIXYYYYMMXXXX (year + month + 4-digit sequence)
    
    ID Format Explanation:
    - PREFIX: e.g., USR, RIDE, etc. (3-4 chars)
    - YYYY: Year (4 digits)
    - MM: Month (2 digits, 01-12)
    - XXXX: 4-digit random sequence (0000-9999)
    
    Example: USR202603ABCD, RIDE202603EFGH
    
    This format is useful for:
    - Rate limiting: Can track per year-month period
    - Sorting: Chronologically sortable by prefix
    - Human readable: Easy to identify when resource was created
    
    4-digit sequence provides 10,000 unique IDs per month per resource type.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m")  # YYYYMM format
    seq = str(random.randint(0, 9999)).zfill(4)  # 4-digit zero-padded sequence
    return f"{prefix}{date_str}{seq}"


def generate_driver_id() -> str:
    """Generates driver ID in the format: DIVYYYYMMxxxx
    
    Format: DIV + Year (4 digits) + Month (2 digits) + Sequence (4 digits from 0000-9999)
    Example: DIV202603ABCD, DIV202603EFGH
    
    Benefits:
    - Year-month indexed for rate limiting
    - Easy to recognize drivers (DIV prefix)
    - 10,000 unique drivers per month
    """
    now = datetime.now(timezone.utc)
    year_month = now.strftime("%Y%m")
    seq = str(random.randint(0, 9999)).zfill(4)  # 4-digit zero-padded number
    return f"DIV{year_month}{seq}"


def generate_ride_id() -> str:
    """Generates ride ID in the format: RIDEYYYYMMDDxxxx
    
    Format: RIDE + Year (4 digits) + Month (2 digits) + Day (2 digits) + Sequence (4 digits)
    Example: RIDE20260315ABCD, RIDE20260315EFGH
    
    Benefits:
    - Full date included for easy activity identification
    - Can quickly identify rides by date
    - Easy to filter by day
    - 10,000 unique rides per day
    """
    now = datetime.now(timezone.utc)
    full_date = now.strftime("%Y%m%d")  # YYYYMMDD format
    seq = str(random.randint(0, 9999)).zfill(4)
    return f"RIDE{full_date}{seq}"


def generate_payment_id() -> str:
    """Generates payment ID in the format: PAYYYYMMDDxxxx
    
    Format: PAY + Year (4 digits) + Month (2 digits) + Day (2 digits) + Sequence (4 digits)
    Example: PAY20260315ABCD, PAY20260315EFGH
    
    Benefits:
    - Full date included for easy activity identification
    - Can quickly identify payments by date
    - Daily transaction tracking
    - 10,000 unique payments per day
    """
    now = datetime.now(timezone.utc)
    full_date = now.strftime("%Y%m%d")  # YYYYMMDD format
    seq = str(random.randint(0, 9999)).zfill(4)
    return f"PAY{full_date}{seq}"


def generate_coupon_code() -> str:
    """Generates customer-friendly coupon code in the format: CPNYYYYMMxxxx
    
    Format: CPN + Year (4 digits) + Month (2 digits) + Sequence (4 digits, uppercase letters/digits)
    Example: CPN202603TRAVEL, CPN202603SAVE50
    
    Benefits:
    - Easy to remember and share
    - Year-month tracked for promotions
    - 10,000 unique codes per month
    - Clean format for marketing materials
    """
    now = datetime.now(timezone.utc)
    year_month = now.strftime("%Y%m")
    # Use uppercase alphanumeric for easier reading
    chars = string.ascii_uppercase + string.digits
    seq = "".join(random.choices(chars, k=4))  # 4 random alphanumeric characters
    return f"CPN{year_month}{seq}"



# ─── MODELS ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id           = Column(String, primary_key=True, default=lambda: generate_custom_id("USR"))
    name         = Column(String, nullable=False)
    email        = Column(String, unique=True, nullable=False)
    phone        = Column(String, nullable=True)  # nullable for OAuth-only users
    password_hash = Column(String, nullable=True)  # null for OAuth-only users
    role         = Column(String, default="user")     # "user" | "admin"
    # OAuth/Provider fields
    provider     = Column(String, default="local")    # "local" | "google" | "github" etc
    provider_id  = Column(String, nullable=True)      # OAuth subject ID (e.g., Google sub)
    email_verified = Column(Boolean, default=False)
    picture      = Column(String, default="")         # Profile picture URL
    referred_by  = Column(String, ForeignKey("users.id"), nullable=True)  # Referral program
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Driver(Base):
    __tablename__ = "drivers"
    id            = Column(String, primary_key=True, default=generate_driver_id)
    name          = Column(String, nullable=False)
    email         = Column(String, unique=True, nullable=False)
    phone         = Column(String, nullable=False)
    password_hash = Column(String, nullable=True)
    vehicle_type  = Column(String, default="7 Seater")  # "5 Seater"|"7 Seater"|"Ambulance"
    plate         = Column(String, nullable=False)
    route_pref    = Column(String, default="Karimnagar")
    ac_pref       = Column(Boolean, default=True)
    status        = Column(String, default="offline")   # "online"|"offline"
    is_verified   = Column(Boolean, default=False)
    rating        = Column(Float, default=5.0)
    rating_count  = Column(Integer, default=0)
    jobs_done     = Column(Integer, default=0)
    profile_pic   = Column(String, default="")
    address       = Column(String, default="")
    provider      = Column(String, default="local")
    provider_id   = Column(String, nullable=True)
    email_verified = Column(Boolean, default=False)
    seats_total   = Column(Integer, default=7)
    filled_seats  = Column(Integer, default=0)
    doc_status    = Column(String, default="pending")
    license_url   = Column(String, default="")
    aadhar_url    = Column(String, default="")
    rc_url        = Column(String, default="")
    insurance_url = Column(String, default="")
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Admin(Base):
    __tablename__ = "admins"
    id            = Column(String, primary_key=True, default=lambda: generate_custom_id("ADM"))
    name          = Column(String, nullable=False)
    email         = Column(String, unique=True, nullable=False)
    phone         = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    provider      = Column(String, default="local")
    provider_id   = Column(String, nullable=True)
    email_verified = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Ride(Base):
    __tablename__ = "rides"
    id            = Column(String, primary_key=True, default=generate_ride_id)
    user_id       = Column(String, ForeignKey("users.id"), nullable=False)
    driver_id     = Column(String, nullable=True)
    driver_name   = Column(String, nullable=True)
    user_name     = Column(String, nullable=True)
    user_phone    = Column(String, nullable=True)
    from_loc      = Column(String, nullable=False)
    to_loc        = Column(String, nullable=False)
    booking_type  = Column(String, default="shared")    # "shared"|"full"
    service_type  = Column(String, default="cab")       # "cab"|"ambulance"
    vehicle_size  = Column(String, default="7 Seater")
    ac            = Column(Boolean, default=True)
    passengers    = Column(Integer, default=1)
    price         = Column(Integer, default=0)
    coupon_code   = Column(String, default="")
    discount      = Column(Integer, default=0)
    status        = Column(String, default="pending")
    # pending|assigned|started|completed|cancelled
    otp           = Column(String, nullable=True)
    pickup_addr   = Column(String, default="")
    drop_addr     = Column(String, default="")
    travel_date   = Column(String, nullable=True)
    cancel_reason = Column(String, default="")
    user_rating   = Column(Integer, nullable=True)
    driver_rating = Column(Integer, nullable=True)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at    = Column(DateTime, nullable=True)
    completed_at  = Column(DateTime, nullable=True)


class Waitlist(Base):
    """Waitlist for users when a shared ride is full"""
    __tablename__ = "waitlists"
    id            = Column(String, primary_key=True, default=lambda: generate_custom_id("WL"))
    ride_id       = Column(String, ForeignKey("rides.id"), nullable=False)
    user_id       = Column(String, ForeignKey("users.id"), nullable=False)
    status        = Column(String, default="waiting")  # "waiting"|"offered"|"accepted"|"declined"|"expired"
    position      = Column(Integer, nullable=False)  # Queue position (1st, 2nd, etc.)
    joined_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    offered_at    = Column(DateTime, nullable=True)  # When offered to join
    accepted_at   = Column(DateTime, nullable=True)  # When user accepted


class DriverLocation(Base):
    __tablename__ = "driver_locations"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    driver_id = Column(String, ForeignKey("drivers.id"))
    lat       = Column(Float, nullable=False)
    lng       = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Payment(Base):
    __tablename__ = "payments"
    id      = Column(String, primary_key=True, default=generate_payment_id)
    ride_id = Column(String, ForeignKey("rides.id"))
    amount  = Column(Integer, nullable=False)
    method  = Column(String, default="cash")   # "cash"|"online"
    status  = Column(String, default="pending") # "pending"|"collected"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Rating(Base):
    __tablename__ = "ratings"
    id        = Column(String, primary_key=True, default=lambda: generate_custom_id("RTG"))
    ride_id   = Column(String, ForeignKey("rides.id"))
    rater_id  = Column(String, nullable=False)
    rated_id  = Column(String, nullable=False)
    rating    = Column(Integer, nullable=False)  # 1–5
    comment   = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Coupon(Base):
    __tablename__ = "coupons"
    id        = Column(String, primary_key=True, default=lambda: generate_custom_id("CPN"))
    code      = Column(String, unique=True, nullable=False, default=generate_coupon_code)
    discount  = Column(Integer, nullable=False)  # amount in ₹
    min_fare  = Column(Integer, default=0)
    expiry    = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id          = Column(String, primary_key=True, default=lambda: generate_custom_id("TKT"))
    user_id     = Column(String, nullable=False)
    user_name   = Column(String, default="")
    ride_id     = Column(String, nullable=True)
    issue_type  = Column(String, nullable=False)
    description = Column(Text, default="")
    status      = Column(String, default="open")  # "open"|"resolved"
    admin_reply = Column(Text, default="")
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Setting(Base):
    __tablename__ = "settings"
    key   = Column(String, primary_key=True)
    value = Column(String, nullable=False)


class Broadcast(Base):
    __tablename__ = "broadcasts"
    id         = Column(String, primary_key=True, default=lambda: generate_custom_id("BDC"))
    message    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Expense(Base):
    __tablename__ = "expenses"
    id          = Column(String, primary_key=True, default=lambda: generate_custom_id("EXP"))
    driver_id   = Column(String, ForeignKey("drivers.id"))
    description = Column(String, nullable=False)
    amount      = Column(Integer, nullable=False)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CancelLog(Base):
    __tablename__ = "cancel_log"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    driver_id = Column(String, ForeignKey("drivers.id"))
    ride_id   = Column(String)
    reason    = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ─── DB INIT ───────────────────────────────────────────────────────────────────

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_user_columns_sync)
        await conn.run_sync(_ensure_driver_columns_sync)
        await conn.run_sync(_ensure_phone_unique_indexes_sync)


def _ensure_user_columns_sync(sync_conn):
    """
    Backfill newly introduced OAuth columns on existing users table.
    """
    if sync_conn.dialect.name != "sqlite":
        return

    rows = sync_conn.execute(text("PRAGMA table_info(users)")).fetchall()
    existing = {r[1] for r in rows}

    wanted = {
        "provider": "TEXT DEFAULT 'local'",
        "provider_id": "TEXT",
        "email_verified": "INTEGER DEFAULT 0",
        "picture": "TEXT DEFAULT ''",
    }

    for col, definition in wanted.items():
        if col in existing:
            continue
        sync_conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {definition}"))


def _ensure_driver_columns_sync(sync_conn):
    """
    Lightweight column backfill for existing SQLite databases.
    SQLAlchemy create_all does not alter existing tables, so we ensure newly
    introduced Driver columns are present.
    """
    if sync_conn.dialect.name != "sqlite":
        return

    rows = sync_conn.execute(text("PRAGMA table_info(drivers)")).fetchall()
    existing = {r[1] for r in rows}

    wanted = {
        "provider": "TEXT DEFAULT 'local'",
        "provider_id": "TEXT",
        "email_verified": "INTEGER DEFAULT 0",
        "seats_total": "INTEGER DEFAULT 7",
        "filled_seats": "INTEGER DEFAULT 0",
        "doc_status": "TEXT DEFAULT 'pending'",
        "license_url": "TEXT DEFAULT ''",
        "aadhar_url": "TEXT DEFAULT ''",
        "rc_url": "TEXT DEFAULT ''",
        "insurance_url": "TEXT DEFAULT ''",
    }

    for col, definition in wanted.items():
        if col in existing:
            continue
        sync_conn.execute(text(f"ALTER TABLE drivers ADD COLUMN {col} {definition}"))


def _ensure_phone_unique_indexes_sync(sync_conn):
    """
    Enforce DB-level phone uniqueness via partial unique indexes.
    For users we ignore NULL/empty because OAuth users can be phone-less.
    """
    if sync_conn.dialect.name != "sqlite":
        return

    # Normalize blank user phones to NULL before applying uniqueness.
    sync_conn.execute(text("UPDATE users SET phone = NULL WHERE TRIM(IFNULL(phone, '')) = ''"))

    # Driver phones must be unique when present/non-empty.
    sync_conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_drivers_phone_non_empty "
        "ON drivers(phone) WHERE phone IS NOT NULL AND TRIM(phone) != ''"
    ))

    # User phones must be unique only for non-empty phones.
    sync_conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_phone_non_empty "
        "ON users(phone) WHERE phone IS NOT NULL AND TRIM(phone) != ''"
    ))


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
