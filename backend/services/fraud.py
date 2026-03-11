"""
Fraud protection service.
Checks: duplicate bookings, cancel abuse, booking rate limiting.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..database import Ride, CancelLog
from fastapi import HTTPException


MAX_CANCELS_PER_DAY = 3
MAX_BOOKINGS_PER_HOUR = 5


async def check_duplicate_booking(user_id: str, db: AsyncSession) -> bool:
    """Returns True if user already has an active (pending/assigned) booking."""
    result = await db.execute(
        select(Ride).where(
            Ride.user_id == user_id,
            Ride.status.in_(["pending", "assigned", "started"])
        )
    )
    return result.scalar_one_or_none() is not None


async def check_booking_rate_limit(user_id: str, db: AsyncSession):
    """Raises 429 if user has booked more than 5 times in the last hour."""
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    result = await db.execute(
        select(func.count()).where(
            Ride.user_id == user_id,
            Ride.created_at >= since
        )
    )
    count = result.scalar()
    if count >= MAX_BOOKINGS_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail="Too many bookings. Please wait before booking again."
        )


async def log_driver_cancel(driver_id: str, ride_id: str, reason: str, db: AsyncSession):
    """Logs a driver cancellation. Raises 400 if driver exceeded daily limit."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count()).where(
            CancelLog.driver_id == driver_id,
            CancelLog.created_at >= today_start
        )
    )
    count = result.scalar()
    if count >= MAX_CANCELS_PER_DAY:
        raise HTTPException(
            status_code=400,
            detail=f"You have cancelled {MAX_CANCELS_PER_DAY} rides today. "
                   f"Contact support if you have an issue."
        )
    entry = CancelLog(driver_id=driver_id, ride_id=ride_id, reason=reason)
    db.add(entry)
    await db.commit()
