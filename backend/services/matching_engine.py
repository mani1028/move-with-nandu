"""
Ride Matching Engine.
When a booking is created, find the best available driver and
optionally auto-assign them. Notifies driver via WebSocket.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import Driver, Ride, Setting


ROUTE_MAP = {
    "Karimnagar":    "Karimnagar",
    "JBS-Hyderabad": "JBS",
    "Hyderabad-City": "Hyderabad",
    "Airport-RGI":   "RGI Airport",
}


def _driver_matches_ride(driver: Driver, ride: Ride) -> bool:
    """Check if driver preferences match the ride requirements."""
    # AC matching
    ac_required = bool(ride.ac)
    if ac_required and not bool(driver.ac_pref):
        return False

    # Route matching (driver's hub should match ride's from_loc or to_loc)
    driver_hub = str(driver.route_pref or "")  # e.g. "Karimnagar"
    from_loc = str(ride.from_loc or "")
    to_loc = str(ride.to_loc or "")
    from_std = ROUTE_MAP.get(from_loc, from_loc)
    to_std = ROUTE_MAP.get(to_loc, to_loc)

    hub_matches = (driver_hub in from_std or driver_hub in to_std or
                   from_std in driver_hub or to_std in driver_hub)
    if not hub_matches:
        return False

    # Shared rides must respect vehicle seat capacity.
    if ride.booking_type == "shared":
        filled_seats = int(driver.filled_seats or 0)  # type: ignore[arg-type]
        seats_total = int(driver.seats_total or 7)  # type: ignore[arg-type]
        passengers = int(ride.passengers or 1)  # type: ignore[arg-type]
        if (filled_seats + passengers) > seats_total:
            return False

    # Vehicle type matching for shared rides
    if ride.booking_type == "shared":
        needed_size = str(ride.vehicle_size or "")  # "7 Seater" or "5 Seater"
        vehicle_type = str(driver.vehicle_type or "")
        if "7" in needed_size and "7" not in vehicle_type:
            return False
        if "5" in needed_size and "5" not in vehicle_type:
            return False

    # Ambulance matching
    if str(ride.service_type or "") == "ambulance" and str(driver.vehicle_type or "") != "Ambulance":
        return False

    return True


async def find_best_driver(ride: Ride, db: AsyncSession):
    """
    Find the best available online driver for this ride.
    Returns Driver or None.
    """
    result = await db.execute(
        select(Driver).where(
            Driver.status == "online",
            Driver.is_verified == True
        )
    )
    all_online = result.scalars().all()

    candidates = [d for d in all_online if _driver_matches_ride(d, ride)]
    if not candidates:
        return None

    # Sort by: highest rating first, then most jobs done
    candidates.sort(key=lambda d: (d.rating, d.jobs_done), reverse=True)
    return candidates[0]


async def get_auto_assign_setting(db: AsyncSession) -> bool:
    result = await db.execute(
        select(Setting).where(Setting.key == "auto_assign")
    )
    setting = result.scalar_one_or_none()
    return str(setting.value).lower() == "true" if setting else True


async def get_surge_multiplier(db: AsyncSession) -> float:
    result = await db.execute(
        select(Setting).where(Setting.key == "surge_multiplier")
    )
    setting = result.scalar_one_or_none()
    try:
        return float(str(setting.value)) if setting else 1.0
    except Exception:
        return 1.0
