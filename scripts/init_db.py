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
from backend.database import init_db, AsyncSessionLocal, Setting
from sqlalchemy import select


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
