import random
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db, Ride, Driver, User, Payment
from ..auth import get_current_user, get_current_driver
from ..services.state_machine import assert_transition
from ..services.matching_engine import find_best_driver, get_auto_assign_setting, get_surge_multiplier
from ..services.fraud import check_duplicate_booking, check_booking_rate_limit, log_driver_cancel
from ..services.pricing import calculate_fare, apply_coupon
from ..ws.manager import manager

router = APIRouter(prefix="/api/rides", tags=["Rides"])


# ─── Schemas ────────────────────────────────────────────────────────────────────

class CreateRideIn(BaseModel):
    from_loc: str
    to_loc: str
    booking_type: str = "shared"
    service_type: str = "cab"
    vehicle_size: str = "7 Seater"
    ac: bool = True
    passengers: int = 1
    coupon_code: str = ""
    discount: int = 0
    pickup_addr: str = ""
    drop_addr: str = ""
    travel_date: str = ""
    amb_type: str = "non-ac"

class RateRideIn(BaseModel):
    rating: int
    comment: str = ""

class CancelRideIn(BaseModel):
    reason: str = ""


# ─── Create Booking ──────────────────────────────────────────────────────────────

@router.post("/")
async def create_ride(
    body: CreateRideIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fraud checks
    await check_booking_rate_limit(str(user.id), db)  # type: ignore
    has_active = await check_duplicate_booking(str(user.id), db)  # type: ignore

    surge = await get_surge_multiplier(db)
    price = calculate_fare(
        booking_type=body.booking_type,
        vehicle_size=body.vehicle_size,
        ac=body.ac,
        service_type=body.service_type,
        amb_type=body.amb_type,
        surge_multiplier=surge,
    )
    if body.discount > 0:
        price = apply_coupon(price, body.discount, 0)

    otp = str(random.randint(1000, 9999))

    ride = Ride(
        user_id=user.id,
        user_name=user.name,
        user_phone=user.phone,
        from_loc=body.from_loc,
        to_loc=body.to_loc,
        booking_type=body.booking_type,
        service_type=body.service_type,
        vehicle_size=body.vehicle_size,
        ac=body.ac,
        passengers=body.passengers,
        price=price,
        coupon_code=body.coupon_code,
        discount=body.discount,
        pickup_addr=body.pickup_addr,
        drop_addr=body.drop_addr,
        travel_date=body.travel_date,
        otp=otp,
        status="pending",
    )
    db.add(ride)

    # Payment record
    payment = Payment(
        ride_id=ride.id,
        amount=price,
        method="cash",
        status="pending"
    )
    db.add(payment)
    await db.commit()
    await db.refresh(ride)

    # Auto-assign matching driver
    auto_assign = await get_auto_assign_setting(db)
    assigned_driver = None
    if auto_assign:
        assigned_driver = await find_best_driver(ride, db)
        if assigned_driver:
            ride.driver_id = assigned_driver.id  # type: ignore
            ride.driver_name = assigned_driver.name  # type: ignore
            ride.status = "assigned"  # type: ignore
            await db.commit()
            await db.refresh(ride)
            # Push to driver via WebSocket
            await manager.notify_driver(str(assigned_driver.id), "new_job", _ride_dict(ride))

    # Notify admin
    await manager.broadcast_admin("new_booking", _ride_dict(ride))

    result = _ride_dict(ride)
    result["duplicate_warning"] = has_active
    return result


# ─── List My Rides ────────────────────────────────────────────────────────────────

@router.get("/")
async def my_rides(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Ride).where(Ride.user_id == user.id).order_by(Ride.created_at.desc())
    )
    return [_ride_dict(r) for r in result.scalars().all()]


# ─── Driver: Accept Ride ──────────────────────────────────────────────────────────
# NOTE: Uses SELECT FOR UPDATE to prevent race conditions where two drivers
# could accept the same ride simultaneously. Lock is held until transaction commits.

@router.patch("/{ride_id}/accept")
async def accept_ride(
    ride_id: str,
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    # Lock the ride row to prevent concurrent accepts (SELECT FOR UPDATE)
    result = await db.execute(
        select(Ride).where(Ride.id == ride_id).with_for_update()
    )
    ride = result.scalar_one_or_none()
    if not ride:
        raise HTTPException(404, "Ride not found.")
    
    assert_transition(str(ride.status), "assigned")  # type: ignore
    if ride.driver_id and str(ride.driver_id) != driver.id:  # type: ignore
        raise HTTPException(409, "Ride already taken by another driver.")
    ride.driver_id = driver.id  # type: ignore
    ride.driver_name = driver.name  # type: ignore
    ride.status = "assigned"  # type: ignore
    await db.commit()
    await db.refresh(ride)

    await manager.broadcast_admin("ride_updated", _ride_dict(ride))
    return _ride_dict(ride)


# ─── Driver: Start Ride (OTP verified) ──────────────────────────────────────────

@router.patch("/{ride_id}/start")
async def start_ride(
    ride_id: str,
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    ride = await _get_ride(ride_id, db)
    assert_transition(str(ride.status), "started")  # type: ignore
    if ride.driver_id != driver.id:
        raise HTTPException(403, "Not your ride.")
    ride.status = "started"  # type: ignore
    ride.started_at = datetime.now(timezone.utc)  # type: ignore
    await db.commit()
    await db.refresh(ride)
    await manager.broadcast_admin("ride_updated", _ride_dict(ride))
    return _ride_dict(ride)


# ─── Driver: Complete Ride ────────────────────────────────────────────────────────

@router.patch("/{ride_id}/complete")
async def complete_ride(
    ride_id: str,
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    ride = await _get_ride(ride_id, db)
    assert_transition(str(ride.status), "completed")  # type: ignore
    if ride.driver_id != driver.id:
        raise HTTPException(403, "Not your ride.")
    ride.status = "completed"  # type: ignore
    ride.completed_at = datetime.now(timezone.utc)  # type: ignore

    # Update driver stats
    driver.jobs_done = (driver.jobs_done or 0) + 1  # type: ignore

    # Mark payment collected
    pay_result = await db.execute(select(Payment).where(Payment.ride_id == ride_id))
    pay = pay_result.scalar_one_or_none()
    if pay:
        pay.status = "collected"  # type: ignore

    await db.commit()
    await db.refresh(ride)
    await manager.broadcast_admin("ride_updated", _ride_dict(ride))
    return _ride_dict(ride)


# ─── Cancel Ride (User or Driver) ────────────────────────────────────────────────

_cancel_oauth = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

@router.patch("/{ride_id}/cancel")
async def cancel_ride(
    ride_id: str,
    body: CancelRideIn,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(_cancel_oauth)
):
    from ..auth import decode_token  # local import keeps router thin
    payload = decode_token(token) if token else None
    if not payload:
        raise HTTPException(401, "Not authenticated.")

    ride = await _get_ride(ride_id, db)
    assert_transition(str(ride.status), "cancelled")  # type: ignore

    role = payload.get("role")
    uid  = payload.get("sub")

    if role == "user" and ride.user_id != uid:
        raise HTTPException(403, "Not your ride.")
    if role == "driver":
        if ride.driver_id != uid:
            raise HTTPException(403, "Not your ride.")
        if uid:
            await log_driver_cancel(str(uid), ride_id, body.reason, db)  # type: ignore

    ride.status = "cancelled"  # type: ignore
    ride.cancel_reason = body.reason  # type: ignore
    await db.commit()
    await db.refresh(ride)
    await manager.broadcast_admin("ride_updated", _ride_dict(ride))
    return _ride_dict(ride)


# ─── Rate a Ride ─────────────────────────────────────────────────────────────────

@router.post("/{ride_id}/rate")
async def rate_ride(
    ride_id: str,
    body: RateRideIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ride = await _get_ride(ride_id, db)
    if ride.user_id != user.id:
        raise HTTPException(403, "Not your ride.")
    if ride.status != "completed":
        raise HTTPException(400, "Can only rate completed rides.")
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(400, "Rating must be 1–5.")

    ride.user_rating = body.rating  # type: ignore

    # Update driver average rating
    if ride.driver_id:
        dr = await db.execute(select(Driver).where(Driver.id == ride.driver_id))
        driver = dr.scalar_one_or_none()
        if driver:
            total = driver.rating * driver.rating_count + body.rating
            driver.rating_count = (driver.rating_count or 0) + 1  # type: ignore
            driver.rating = float(round(float(total) / float(driver.rating_count or 1), 1))  # type: ignore

    from ..database import Rating
    rating_rec = Rating(
        ride_id=ride_id,
        rater_id=user.id,
        rated_id=ride.driver_id or "",
        rating=body.rating,
        comment=body.comment
    )
    db.add(rating_rec)
    await db.commit()
    return {"ok": True}


# ─── Verify OTP (Driver verifies passenger PIN) ───────────────────────────────────

@router.post("/{ride_id}/verify-otp")
async def verify_otp(
    ride_id: str,
    otp: str,
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    ride = await _get_ride(ride_id, db)
    if ride.driver_id != driver.id:
        raise HTTPException(403, "Not your ride.")
    if ride.otp != otp:
        raise HTTPException(400, "Invalid OTP.")
    return {"ok": True, "message": "OTP verified. You may start the ride."}


# ─── helpers ─────────────────────────────────────────────────────────────────────

async def _get_ride(ride_id: str, db: AsyncSession) -> Ride:
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalar_one_or_none()
    if not ride:
        raise HTTPException(404, "Ride not found.")
    return ride


def _ride_dict(r: Ride) -> dict:
    return {
        "id": r.id, "user_id": r.user_id, "driver_id": r.driver_id,
        "user_name": r.user_name, "user_phone": r.user_phone,
        "driver_name": r.driver_name,
        "from_loc": r.from_loc, "to_loc": r.to_loc,
        "booking_type": r.booking_type, "service_type": r.service_type,
        "vehicle_size": r.vehicle_size, "ac": r.ac,
        "passengers": r.passengers, "price": r.price,
        "coupon_code": r.coupon_code, "discount": r.discount,
        "status": r.status, "otp": r.otp,
        "pickup_addr": r.pickup_addr, "drop_addr": r.drop_addr,
        "travel_date": r.travel_date,
        "cancel_reason": r.cancel_reason,
        "user_rating": r.user_rating,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }
