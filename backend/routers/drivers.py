import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Any, Optional, cast
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..database import get_db, Driver, Ride, Expense, User, Admin
from ..auth import get_current_driver
from ..config import settings
from ..storage import delete_public_file, read_validated_upload, save_public_file
from ..ws.manager import manager
from ..services.matching_engine import find_best_driver

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
    seats_total: Optional[int] = None
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
    status_changing_to_offline = False

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

    current_seats_total = int(cast(Any, driver).seats_total or 7)
    requested_seats_total: Optional[int] = current_seats_total
    if body.vehicle_type is not None:
        driver.vehicle_type = body.vehicle_type.strip()  # type: ignore

        def _seats_for_type(vt: str) -> int:
            v = vt.lower()
            if any(x in v for x in ('12', 'tempo')): return 12
            if any(x in v for x in ('7', 'innova', 'ertiga', 'suv')): return 7
            if any(x in v for x in ('4', 'mini')): return 4
            if any(x in v for x in ('ambulance',)): return 2
            return 5

        requested_seats_total = _seats_for_type(body.vehicle_type.strip())
    if body.seats_total is not None:
        requested_seats_total = int(body.seats_total)
    if requested_seats_total is not None and (requested_seats_total < 1 or requested_seats_total > 12):
        raise HTTPException(400, "seats_total must be between 1 and 12")

    requested_filled_seats: Optional[int] = None
    if body.filled_seats is not None:
        requested_filled_seats = int(body.filled_seats)
    if body.manual_filled_seats is not None:
        requested_filled_seats = int(body.manual_filled_seats)
    if body.manualFilledSeats is not None:
        requested_filled_seats = int(body.manualFilledSeats)
    if requested_filled_seats is not None and requested_filled_seats < 0:
        raise HTTPException(400, "Filled seats cannot be negative.")

    current_filled_seats = int(cast(Any, driver).filled_seats or 0)
    target_seats_total = int(requested_seats_total if requested_seats_total is not None else current_seats_total)
    target_filled_seats = int(requested_filled_seats if requested_filled_seats is not None else current_filled_seats)
    if target_filled_seats > target_seats_total:
        raise HTTPException(400, "Filled seats cannot exceed total vehicle seats.")

    if requested_filled_seats is not None:
        active_app_passengers = await _get_active_app_passengers(db, str(driver.id))
        if target_filled_seats < active_app_passengers:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Action blocked! You currently have {active_app_passengers} passengers assigned via the app. "
                    f"You cannot set filled seats to {target_filled_seats}."
                )
            )

    driver.seats_total = target_seats_total  # type: ignore
    if requested_filled_seats is not None:
        driver.filled_seats = target_filled_seats  # type: ignore

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
        status_changing_to_offline = (body.status == "offline" and str(driver.status) != "offline")
        driver.status = body.status  # type: ignore
    if body.jobs_done is not None:
        driver.jobs_done = max(0, int(body.jobs_done))  # type: ignore
    if body.route_pref is not None:
        driver.route_pref = body.route_pref.strip()  # type: ignore
    if body.ac_pref is not None:
        driver.ac_pref = bool(body.ac_pref)  # type: ignore
    if docs_updated:
        driver.doc_status = "pending"  # type: ignore
    reassign_summary = {"reassigned": 0, "pending": 0}
    if status_changing_to_offline:
        reassign_summary = await _reassign_assigned_rides_for_offline_driver(driver, db)

    await db.commit()
    await db.refresh(driver)
    payload = _driver_dict(driver)
    payload["reassignment"] = reassign_summary
    return payload


@router.post("/me/profile-pic")
async def upload_driver_profile_pic(
    file: UploadFile = File(...),
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    allowed_types = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    content, extension = await read_validated_upload(
        file,
        allowed_types=allowed_types,
        label="Driver profile image",
    )

    previous_picture = (driver.profile_pic or "").strip()
    filename = f"{driver.id}_{uuid.uuid4().hex[:10]}{extension}"
    cast(Any, driver).profile_pic = await save_public_file(
        content=content,
        content_type=(file.content_type or "application/octet-stream").lower(),
        bucket=str(settings["profile_upload_bucket"]),
        object_path=f"drivers/{filename}",
        local_dir="drivers",
    )
    await db.commit()
    await db.refresh(driver)

    await delete_public_file(
        current_url=previous_picture,
        bucket=str(settings["profile_upload_bucket"]),
        local_dir="drivers",
    )

    return {"ok": True, "profile_pic": driver.profile_pic}


@router.post("/me/documents")
async def upload_driver_documents(
    license_file: Optional[UploadFile] = File(None),
    aadhar_file: Optional[UploadFile] = File(None),
    rc_file: Optional[UploadFile] = File(None),
    insurance_file: Optional[UploadFile] = File(None),
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db),
):
    files = {
        "license": license_file,
        "aadhar": aadhar_file,
        "rc": rc_file,
        "insurance": insurance_file,
    }
    if not any(files.values()):
        raise HTTPException(400, "Upload at least one document")

    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    # Capture previous files so we can clean up replaced documents.
    previous = {
        "license": (driver.license_url or "").strip(),
        "aadhar": (driver.aadhar_url or "").strip(),
        "rc": (driver.rc_url or "").strip(),
        "insurance": (driver.insurance_url or "").strip(),
    }

    saved = {}
    for key, up in files.items():
        if not up:
            continue
        content, ext = await read_validated_upload(up, allowed_types=allowed_types, label=f"{key} document")
        filename = f"{driver.id}_{key}_{uuid.uuid4().hex[:10]}{ext}"
        saved[key] = await save_public_file(
            content=content,
            content_type=(up.content_type or "application/octet-stream").lower(),
            bucket=str(settings["driver_docs_bucket"]),
            object_path=f"driver-docs/{filename}",
            local_dir="driver-docs",
        )

    if "license" in saved:
        driver.license_url = saved["license"]  # type: ignore
    if "aadhar" in saved:
        driver.aadhar_url = saved["aadhar"]  # type: ignore
    if "rc" in saved:
        driver.rc_url = saved["rc"]  # type: ignore
    if "insurance" in saved:
        driver.insurance_url = saved["insurance"]  # type: ignore

    # Any document refresh requires re-verification by admin.
    driver.doc_status = "pending"  # type: ignore
    driver.is_verified = False  # type: ignore

    await db.commit()
    await db.refresh(driver)

    for key, old_url in previous.items():
        new_url = saved.get(key)
        if not new_url:
            continue
        await delete_public_file(
            current_url=old_url,
            bucket=str(settings["driver_docs_bucket"]),
            local_dir="driver-docs",
        )

    return {
        "ok": True,
        "doc_status": driver.doc_status,
        "is_verified": driver.is_verified,
        "license_url": driver.license_url,
        "aadhar_url": driver.aadhar_url,
        "rc_url": driver.rc_url,
        "insurance_url": driver.insurance_url,
    }


@router.patch("/status")
async def toggle_status(
    body: StatusPatch,
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    if body.status not in ("online", "offline"):
        raise HTTPException(400, "status must be 'online' or 'offline'")
    status_changing_to_offline = (body.status == "offline" and str(driver.status) != "offline")
    driver.status = body.status  # type: ignore

    reassign_summary = {"reassigned": 0, "pending": 0}
    if status_changing_to_offline:
        reassign_summary = await _reassign_assigned_rides_for_offline_driver(driver, db)

    await db.commit()
    return {"ok": True, "status": driver.status, "reassignment": reassign_summary}


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


async def _reassign_assigned_rides_for_offline_driver(driver: Driver, db: AsyncSession) -> dict[str, int]:
    """Move driver's assigned rides back to pending and try to auto-reassign."""
    result = await db.execute(
        select(Ride).where(
            Ride.driver_id == driver.id,
            Ride.status == "assigned",
        )
    )
    rides = result.scalars().all()

    reassigned_count = 0
    pending_count = 0

    for ride in rides:
        # Clear current assignment and return to pending pool.
        ride.driver_id = None  # type: ignore
        ride.driver_name = None  # type: ignore
        ride.status = "pending"  # type: ignore

        next_driver = await find_best_driver(ride, db)
        if next_driver and str(next_driver.id) != str(driver.id):
            ride.driver_id = next_driver.id  # type: ignore
            ride.driver_name = next_driver.name  # type: ignore
            ride.status = "assigned"  # type: ignore
            reassigned_count += 1
            await manager.notify_driver(str(next_driver.id), "new_job", _ride_dict(ride))
        else:
            pending_count += 1

        await manager.broadcast_admin("ride_updated", _ride_dict(ride))

    return {"reassigned": reassigned_count, "pending": pending_count}


async def _get_active_app_passengers(db: AsyncSession, driver_id: str) -> int:
    result = await db.execute(
        select(func.sum(Ride.passengers)).where(
            Ride.driver_id == driver_id,
            Ride.status.in_(["assigned", "verified", "started"]),
        )
    )
    return int(result.scalar() or 0)
