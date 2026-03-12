#!/usr/bin/env python3
"""
Standalone database initialization script for Vercel deployment.
Explicitly creates all tables and initial settings before the app starts.

Run this during Vercel build phase to ensure database schema is ready.
"""

import asyncio
import os
import sys
import logging
from datetime import UTC, datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from backend.config import settings
from backend.database import init_db, AsyncSessionLocal, Setting, User, Admin
from backend.auth import hash_password
from sqlalchemy import select

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def main():
    """Initialize database schema and settings."""
    env = str(settings["environment"])
    db_url = str(settings["database_url"])
    
    logger.info("=" * 80)
    logger.info("🗄️  DATABASE INITIALIZATION")
    logger.info("=" * 80)
    logger.info(f"Environment: {env}")
    logger.info(f"Database: {db_url[:50]}..." if db_url else "No DATABASE_URL set")
    
    try:
        # Create all tables
        logger.info("\n📋 Creating tables...")
        await init_db()
        logger.info("✅ Tables created successfully")
        
        # Initialize default settings
        logger.info("\n⚙️  Initializing default settings...")
        async with AsyncSessionLocal() as db:
            defaults = {
                "surge_multiplier": "1.0",
                "auto_assign": "true",
                "accept_bookings": "true",
                "maintenance": "false",
            }
            for key, val in defaults.items():
                existing = await db.execute(select(Setting).where(Setting.key == key))
                if not existing.scalar_one_or_none():
                    db.add(Setting(key=key, value=val))
                    logger.info(f"  + Setting: {key} = {val}")

            # Seed or update bootstrap admin credentials for first login.
            admin_email = str(settings["admin_email"]).lower().strip()
            admin_password = str(settings["admin_password"])
            admin_name = os.getenv("ADMIN_NAME", "Nandu Admin").strip() or "Nandu Admin"
            admin_phone = os.getenv("ADMIN_PHONE", "9999999999").strip() or "9999999999"
            admin_hash = hash_password(admin_password)

            user_result = await db.execute(select(User).where(User.email == admin_email).limit(1))
            admin_user = user_result.scalar_one_or_none()
            if admin_user is None:
                admin_user = User(
                    name=admin_name,
                    email=admin_email,
                    phone=admin_phone,
                    password_hash=admin_hash,
                    role="admin",
                    provider="local",
                    provider_id=None,
                    email_verified=True,
                    picture="",
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                )
                db.add(admin_user)
                await db.flush()
                logger.info(f"  + Admin user seeded: {admin_email}")
            else:
                for field, value in {
                    "name": admin_name,
                    "phone": admin_phone,
                    "password_hash": admin_hash,
                    "role": "admin",
                    "provider": "local",
                    "provider_id": None,
                    "email_verified": True,
                }.items():
                    setattr(admin_user, field, value)
                logger.info(f"  ~ Admin user updated: {admin_email}")

            admin_result = await db.execute(select(Admin).where(Admin.email == admin_email).limit(1))
            admin_row = admin_result.scalar_one_or_none()
            if admin_row is None:
                admin_row = Admin(
                    id=admin_user.id,
                    name=admin_name,
                    email=admin_email,
                    phone=admin_phone,
                    password_hash=admin_hash,
                    provider="local",
                    provider_id=None,
                    email_verified=True,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                )
                db.add(admin_row)
                logger.info(f"  + Admin profile seeded: {admin_email}")
            else:
                for field, value in {
                    "name": admin_name,
                    "phone": admin_phone,
                    "password_hash": admin_hash,
                    "provider": "local",
                    "provider_id": None,
                    "email_verified": True,
                }.items():
                    setattr(admin_row, field, value)
                logger.info(f"  ~ Admin profile updated: {admin_email}")

            await db.commit()
        
        logger.info("\n✅ Database initialization complete!")
        logger.info("=" * 80)
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"\n❌ Database initialization failed: {e}")
        logger.exception(e)
        if env == "production":
            sys.exit(1)
        else:
            logger.warning("⚠️  Continuing in development mode despite DB error")
            sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏸️  Interrupted by user")
        sys.exit(0)
