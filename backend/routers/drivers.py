from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db, Driver, Ride, Expense, User, Admin
from ..auth import get_current_driver
from ..ws.manager import manager

router = APIRouter(prefix="/api/drivers", tags=["Drivers"])


class PrefPatch(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_pic: Optional[str] = None
    vehicle_type: Optional[str] = None
    plate: Optional[str] = None
    route_pref: Optional[str] = None
    ac_pref: Optional[bool] = None
    address: Optional[str] = None
    license_url: Optional[str] = None
    aadhar_url: Optional[str] = None
    rc_url: Optional[str] = None
    insurance_url: Optional[str] = None
    status: Optional[str] = None
    jobs_done: Optional[int] = None
    filled_seats: Optional[int] = None
    manual_filled_seats: Optional[int] = None
    manualFilledSeats: Optional[int] = None


class ExpenseIn(BaseModel):
    description: str
    amount: int


class WalletTxnIn(BaseModel):
    amount: int
    ride_id: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None

class StatusPatch(BaseModel):
    status: str  # "online" | "offline"

class LocationIn(BaseModel):
    lat: float
    lng: float


@router.get("/me")
async def get_me(driver: Driver = Depends(get_current_driver)):
    return _driver_dict(driver)


@router.patch("/me")
async def patch_me(
    body: PrefPatch,
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    docs_updated = False
    if body.route_pref is not None:
        driver.route_pref = body.route_pref  # type: ignore
    if body.ac_pref is not None:
        driver.ac_pref = body.ac_pref  # type: ignore
    if body.address is not None:
        driver.address = body.address  # type: ignore
    if body.name is not None:
        driver.name = body.name.strip()  # type: ignore
    if body.email is not None:
        email = body.email.lower().strip()
        if email != driver.email:
            existing = await db.execute(select(Driver).where(Driver.email == email, Driver.id != driver.id))
            if existing.scalar_one_or_none():
                raise HTTPException(400, "Email already in use by another driver")
            driver.email = email  # type: ignore
    if body.phone is not None:
        phone = body.phone.strip()
        if not phone:
            raise HTTPException(400, "Phone is required")
        if phone != driver.phone:
            existing = await db.execute(
                select(Driver).where(Driver.phone == phone, Driver.id != driver.id).limit(1)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(400, "Phone already in use by another driver")
        driver.phone = phone  # type: ignore
    if body.profile_pic is not None:
        driver.profile_pic = body.profile_pic.strip()  # type: ignore
    if body.vehicle_type is not None:
        driver.vehicle_type = body.vehicle_type.strip()  # type: ignore
    if body.plate is not None:
        plate = body.plate.upper().strip()
        if not plate:
            raise HTTPException(400, "Vehicle plate is required")
        driver.plate = plate  # type: ignore
    if body.license_url is not None:
        driver.license_url = body.license_url.strip()  # type: ignore
        docs_updated = True
    if body.aadhar_url is not None:
        driver.aadhar_url = body.aadhar_url.strip()  # type: ignore
        docs_updated = True
    if body.rc_url is not None:
        driver.rc_url = body.rc_url.strip()  # type: ignore
        docs_updated = True
    if body.insurance_url is not None:
        driver.insurance_url = body.insurance_url.strip()  # type: ignore
        docs_updated = True
    if body.status is not None:
        if body.status not in ("online", "offline"):
            raise HTTPException(400, "status must be 'online' or 'offline'")
        driver.status = body.status  # type: ignore
    if body.jobs_done is not None:
        driver.jobs_done = max(0, int(body.jobs_done))  # type: ignore
    if body.filled_seats is not None:
        driver.filled_seats = max(0, int(body.filled_seats))  # type: ignore
    if body.manual_filled_seats is not None:
        driver.filled_seats = max(0, int(body.manual_filled_seats))  # type: ignore
    if body.manualFilledSeats is not None:
        driver.filled_seats = max(0, int(body.manualFilledSeats))  # type: ignore
    if body.route_pref is not None:
        driver.route_pref = body.route_pref.strip()  # type: ignore
    if body.ac_pref is not None:
        driver.ac_pref = bool(body.ac_pref)  # type: ignore
    if docs_updated:
        driver.doc_status = "pending"  # type: ignore
    await db.commit()
    await db.refresh(driver)
    return _driver_dict(driver)


@router.patch("/status")
async def toggle_status(
    body: StatusPatch,
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    if body.status not in ("online", "offline"):
        raise HTTPException(400, "status must be 'online' or 'offline'")
    driver.status = body.status  # type: ignore
    await db.commit()
    return {"ok": True, "status": driver.status}


@router.get("/trips/active")
async def active_trips(
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    """Trips matching driver preferences that are still pending."""
    result = await db.execute(
        select(Ride).where(Ride.status == "pending").order_by(Ride.created_at.desc())
    )
    rides = result.scalars().all()

    # Filter by driver preferences
    from ..services.matching_engine import _driver_matches_ride
    matching = [r for r in rides if _driver_matches_ride(driver, r)]

    return [_ride_dict(r) for r in matching]


@router.get("/my-trips")
async def my_trips(
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    """All trips assigned to this driver."""
    result = await db.execute(
        select(Ride).where(Ride.driver_id == driver.id)
        .order_by(Ride.created_at.desc())
    )
    rides = result.scalars().all()
    return [_ride_dict(r) for r in rides]


@router.get("/me/expenses")
async def get_my_expenses(
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Expense)
        .where(Expense.driver_id == driver.id)
        .order_by(Expense.created_at.desc())
    )
    expenses = result.scalars().all()
    return [
        {
            "id": e.id,
            "description": e.description,
            "amount": e.amount,
            "date": e.created_at.isoformat() if e.created_at else None,  # type: ignore
        }
        for e in expenses
    ]


@router.post("/me/expenses")
async def create_my_expense(
    body: ExpenseIn,
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    if body.amount <= 0:
        raise HTTPException(400, "Amount must be greater than zero")

    expense = Expense(
        driver_id=driver.id,
        description=body.description.strip() or "Expense",
        amount=body.amount,
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return {
        "id": expense.id,
        "description": expense.description,
        "amount": expense.amount,
        "date": expense.created_at.isoformat() if expense.created_at is not None else None,  # type: ignore
    }


@router.post("/me/wallet")
async def record_wallet_txn(
    body: WalletTxnIn,
    driver: Driver = Depends(get_current_driver),
):
    # Compatibility endpoint for frontend wallet logging.
    return {
        "ok": True,
        "driver_id": driver.id,
        "amount": body.amount,
        "ride_id": body.ride_id,
        "type": body.type or "credit",
        "description": body.description or "",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/me/ping")
async def ping_me(driver: Driver = Depends(get_current_driver)):
    return {
        "ok": True,
        "driver_id": driver.id,
        "status": driver.status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Helpers ────────────────────────────────────────────────────────────────────

def _driver_dict(d: Driver) -> dict:
    return {
        "id": d.id, "name": d.name, "email": d.email, "phone": d.phone,
        "vehicle_type": d.vehicle_type, "plate": d.plate,
        "vehicleType": d.vehicle_type,
        "route_pref": d.route_pref, "ac_pref": d.ac_pref,
        "status": d.status, "is_verified": d.is_verified,
        "rating": d.rating, "rating_count": d.rating_count, "reviews_count": d.rating_count, "jobs_done": d.jobs_done,
        "profile_pic": d.profile_pic, "address": d.address,
        "provider": d.provider,
        "doc_status": d.doc_status,
        "seats_total": d.seats_total,
        "filled_seats": d.filled_seats,
        "manual_filled_seats": d.filled_seats,
        "manualFilledSeats": d.filled_seats,
        "license_url": d.license_url,
        "aadhar_url": d.aadhar_url,
        "rc_url": d.rc_url,
        "insurance_url": d.insurance_url,
        "verification_status": d.doc_status,
        "created_at": d.created_at.isoformat() if d.created_at else None  # type: ignore
    }


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
        "created_at": r.created_at.isoformat() if r.created_at else None,  # type: ignore
        "started_at": r.started_at.isoformat() if r.started_at else None,  # type: ignore
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,  # type: ignore
    }
