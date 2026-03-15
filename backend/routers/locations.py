import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db, Driver, DriverLocation
from ..auth import get_current_driver

router = APIRouter(prefix="/api/driver", tags=["Driver Location"])


class LocationIn(BaseModel):
    lat: float
    lng: float


@router.get("/location")
async def get_own_location(
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    """Get the authenticated driver's own last known location."""
    result = await db.execute(
        select(DriverLocation)
        .where(DriverLocation.driver_id == driver.id)
        .order_by(DriverLocation.timestamp.desc())
    )
    loc = result.scalars().first()
    if not loc:
        raise HTTPException(404, "No location data found.")
    return {"driver_id": driver.id, "lat": loc.lat, "lng": loc.lng,
            "timestamp": loc.timestamp.isoformat()}


@router.post("/location")
async def update_location(
    body: LocationIn,
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DriverLocation)
        .where(DriverLocation.driver_id == driver.id)
        .order_by(DriverLocation.timestamp.desc())
    )
    loc = result.scalars().first()

    if loc:
        loc.lat = body.lat  # type: ignore
        loc.lng = body.lng  # type: ignore
        loc.timestamp = datetime.now(timezone.utc)  # type: ignore
    else:
        loc = DriverLocation(
            driver_id=driver.id,
            lat=body.lat,
            lng=body.lng,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(loc)

    await db.commit()
    return {"ok": True}


@router.get("/{driver_id}/location")
async def get_location(driver_id: str, db: AsyncSession = Depends(get_db)):
    """Get last known location of a driver."""
    result = await db.execute(
        select(DriverLocation)
        .where(DriverLocation.driver_id == driver_id)
        .order_by(DriverLocation.timestamp.desc())
    )
    loc = result.scalars().first()
    if not loc:
        raise HTTPException(404, "No location data for this driver.")
    return {"driver_id": driver_id, "lat": loc.lat, "lng": loc.lng,
            "timestamp": loc.timestamp.isoformat()}
