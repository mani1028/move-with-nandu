import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..database import (get_db, User, Admin, Driver, Ride, SupportTicket,
                        Coupon, Setting, Broadcast, generate_custom_id, 
                        generate_coupon_code)
from ..auth import get_current_admin
from ..ws.manager import manager
from ..auth import hash_password
from pydantic import EmailStr
from fastapi import Body

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ─── Schemas ─────────────────────────────────────────────────────────────────────

class CouponIn(BaseModel):
    code: Optional[str] = None  # Optional - will be auto-generated if not provided
    discount: int
    min_fare: int = 0
    expiry: Optional[str] = None

class SettingsIn(BaseModel):
    surge_multiplier: Optional[float] = None
    auto_assign: Optional[bool] = None
    accept_bookings: Optional[bool] = None
    maintenance: Optional[bool] = None

class BroadcastIn(BaseModel):
    message: str

class TicketReplyIn(BaseModel):
    admin_reply: str = ""
    status: str = "resolved"

class DriverPatchIn(BaseModel):
    is_verified: Optional[bool] = None
    status: Optional[str] = None
    seats_total: Optional[int] = None
    filled_seats: Optional[int] = None
    doc_status: Optional[str] = None
    license_url: Optional[str] = None
    aadhar_url: Optional[str] = None
    rc_url: Optional[str] = None
    insurance_url: Optional[str] = None

class ForceCancelIn(BaseModel):
    reason: str = "Cancelled by admin"


class UserPatchIn(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    picture: Optional[str] = None


class BookingPatchIn(BaseModel):
    driver_id: Optional[str] = None
    driver_name: Optional[str] = None
    status: Optional[str] = None
    price: Optional[int] = None
    passengers: Optional[int] = None
    travel_date: Optional[str] = None
    cancel_reason: Optional[str] = None
    force: bool = False


# ─── Stats ───────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def stats(
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    pending  = await _count(db, Ride, Ride.status == "pending")
    active   = await _count(db, Ride, Ride.status.in_(["assigned", "started"]))
    total_d  = await _count(db, Driver)
    online_d = await _count(db, Driver, Driver.status == "online")
    total_u  = await _count(db, User, User.role == "user")
    tickets  = await _count(db, SupportTicket, SupportTicket.status == "open")
    return {
        "pending": pending, "active": active,
        "total_drivers": total_d, "online_drivers": online_d,
        "total_users": total_u, "open_tickets": tickets
    }


# ─── Bookings ────────────────────────────────────────────────────────────────────

@router.get("/bookings")
async def all_bookings(
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Ride).order_by(Ride.created_at.desc()))
    return [_ride_dict(r) for r in result.scalars().all()]


@router.patch("/bookings/{ride_id}/cancel")
async def force_cancel(
    ride_id: str,
    body: ForceCancelIn,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalar_one_or_none()
    if not ride:
        raise HTTPException(404, "Ride not found.")
    from ..services.state_machine import assert_transition
    assert_transition(str(ride.status), "cancelled")  # type: ignore
    ride.status = "cancelled"  # type: ignore
    ride.cancel_reason = body.reason  # type: ignore
    await db.commit()
    await manager.broadcast_admin("ride_updated", _ride_dict(ride))
    return {"ok": True}


# ─── Drivers ─────────────────────────────────────────────────────────────────────

@router.get("/drivers")
async def all_drivers(
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Driver).order_by(Driver.created_at.desc()))
    return [_driver_dict(d) for d in result.scalars().all()]


@router.patch("/drivers/{driver_id}")
async def patch_driver(
    driver_id: str,
    body: DriverPatchIn,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Driver).where(Driver.id == driver_id))
    driver = result.scalar_one_or_none()
    if not driver:
        raise HTTPException(404, "Driver not found.")
    if body.is_verified is not None:
        driver.is_verified = body.is_verified  # type: ignore
    if body.status is not None:
        driver.status = body.status  # type: ignore
    if body.seats_total is not None:
        if body.seats_total < 1 or body.seats_total > 12:
            raise HTTPException(400, "seats_total must be between 1 and 12")
        driver.seats_total = body.seats_total  # type: ignore
        if (driver.filled_seats or 0) > body.seats_total:  # type: ignore
            driver.filled_seats = body.seats_total  # type: ignore
    if body.filled_seats is not None:
        seats_total = body.seats_total if body.seats_total is not None else (driver.seats_total or 7)  # type: ignore
        if body.filled_seats < 0 or body.filled_seats > seats_total:
            raise HTTPException(400, "filled_seats must be within seat capacity")
        driver.filled_seats = body.filled_seats  # type: ignore
    if body.doc_status is not None:
        allowed = {"pending", "approved", "rejected"}
        if body.doc_status not in allowed:
            raise HTTPException(400, "doc_status must be pending, approved, or rejected")
        driver.doc_status = body.doc_status  # type: ignore
    if body.license_url is not None:
        driver.license_url = body.license_url.strip()  # type: ignore
    if body.aadhar_url is not None:
        driver.aadhar_url = body.aadhar_url.strip()  # type: ignore
    if body.rc_url is not None:
        driver.rc_url = body.rc_url.strip()  # type: ignore
    if body.insurance_url is not None:
        driver.insurance_url = body.insurance_url.strip()  # type: ignore
    await db.commit()
    return {"ok": True}


# ─── Users ───────────────────────────────────────────────────────────────────────

@router.get("/users")
async def all_users(
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.role == "user").order_by(User.created_at.desc())
    )
    return [_user_dict(u) for u in result.scalars().all()]


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: str,
    body: UserPatchIn,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id, User.role == "user"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if body.email is not None:
        email = body.email.lower().strip()
        if email != (user.email or ""):
            r = await db.execute(select(User).where(User.email == email, User.id != user_id).limit(1))
            if r.scalar_one_or_none():
                raise HTTPException(400, "Email already in use by another user")
            user.email = email  # type: ignore

    if body.phone is not None:
        phone = body.phone.strip()
        if phone and phone != (user.phone or ""):
            r = await db.execute(select(User).where(User.phone == phone, User.id != user_id).limit(1))
            if r.scalar_one_or_none():
                raise HTTPException(400, "Phone already in use by another user")
        user.phone = phone  # type: ignore

    if body.name is not None:
        user.name = body.name.strip()  # type: ignore
    if body.picture is not None:
        user.picture = body.picture.strip()  # type: ignore

    await db.commit()
    await db.refresh(user)
    return _user_dict(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id, User.role == "user"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    await db.execute(Ride.__table__.delete().where(Ride.user_id == user_id))
    await db.delete(user)
    await db.commit()
    return {"ok": True}


@router.patch("/bookings/{ride_id}")
async def patch_booking(
    ride_id: str,
    body: BookingPatchIn,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalar_one_or_none()
    if not ride:
        raise HTTPException(404, "Ride not found")

    if body.driver_id is not None:
        ride.driver_id = body.driver_id.strip() or None  # type: ignore
    if body.driver_name is not None:
        ride.driver_name = body.driver_name.strip() or None  # type: ignore

    if body.price is not None:
        if body.price < 0:
            raise HTTPException(400, "price cannot be negative")
        ride.price = body.price  # type: ignore

    if body.passengers is not None:
        if body.passengers < 1 or body.passengers > 12:
            raise HTTPException(400, "passengers must be between 1 and 12")
        ride.passengers = body.passengers  # type: ignore

    if body.travel_date is not None:
        ride.travel_date = body.travel_date.strip()  # type: ignore

    if body.cancel_reason is not None:
        ride.cancel_reason = body.cancel_reason.strip()  # type: ignore

    if body.status is not None:
        next_status = body.status.strip().lower()
        allowed = {"pending", "assigned", "started", "completed", "cancelled"}
        if next_status not in allowed:
            raise HTTPException(400, "Invalid booking status")
        current = str(ride.status or "pending")
        if not body.force and current != next_status:
            from ..services.state_machine import assert_transition
            assert_transition(current, next_status)
        ride.status = next_status  # type: ignore
        if next_status == "cancelled" and not (ride.cancel_reason or "").strip():
            ride.cancel_reason = "Cancelled by admin"  # type: ignore

    await db.commit()
    await db.refresh(ride)
    await manager.broadcast_admin("ride_updated", _ride_dict(ride))
    return _ride_dict(ride)


# ─── Coupons ─────────────────────────────────────────────────────────────────────

@router.get("/coupons")
async def list_coupons(
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Coupon).order_by(Coupon.created_at.desc()))
    return [_coupon_dict(c) for c in result.scalars().all()]


@router.post("/coupons")
async def create_coupon(
    body: CouponIn,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    # Use provided code or auto-generate customer-friendly code
    coupon_code = body.code.upper() if body.code else generate_coupon_code()
    
    # Check if code already exists (only if user provided a code)
    if body.code:
        existing = await db.execute(
            select(Coupon).where(Coupon.code == coupon_code)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(400, "Coupon code already exists.")
    
    coupon = Coupon(
        id=generate_custom_id("CPN"),
        code=coupon_code,
        discount=body.discount,
        min_fare=body.min_fare,
        expiry=body.expiry,
        is_active=True
    )
    db.add(coupon)
    await db.commit()
    return _coupon_dict(coupon)


@router.delete("/coupons/{coupon_id}")
async def delete_coupon(
    coupon_id: str,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Coupon).where(Coupon.id == coupon_id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(404, "Coupon not found.")
    await db.delete(coupon)
    await db.commit()
    return {"ok": True}


# ─── Support ─────────────────────────────────────────────────────────────────────

@router.get("/support")
async def list_tickets(
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SupportTicket).order_by(SupportTicket.created_at.desc())
    )
    return [_ticket_dict(t) for t in result.scalars().all()]


@router.patch("/support/{ticket_id}")
async def resolve_ticket(
    ticket_id: str,
    body: TicketReplyIn,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(404, "Ticket not found.")
    ticket.status = body.status  # type: ignore
    ticket.admin_reply = body.admin_reply  # type: ignore
    await db.commit()
    return {"ok": True}


# ─── Settings ────────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Setting))
    settings = {s.key: s.value for s in result.scalars().all()}
    return settings


@router.patch("/settings")
async def update_settings(
    body: SettingsIn,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    updates = {}
    if body.surge_multiplier is not None:
        updates["surge_multiplier"] = str(body.surge_multiplier)
    if body.auto_assign is not None:
        updates["auto_assign"] = str(body.auto_assign).lower()
    if body.accept_bookings is not None:
        updates["accept_bookings"] = str(body.accept_bookings).lower()
    if body.maintenance is not None:
        updates["maintenance"] = str(body.maintenance).lower()

    for key, val in updates.items():
        result = await db.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = val
        else:
            db.add(Setting(key=key, value=val))
    await db.commit()
    return {"ok": True}


# ─── Broadcasts ──────────────────────────────────────────────────────────────────

@router.post("/broadcasts")
async def send_broadcast(
    body: BroadcastIn,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    bc = Broadcast(id=generate_custom_id("BDC"), message=body.message)
    db.add(bc)
    await db.commit()
    await manager.broadcast_all_drivers("broadcast", {"message": body.message})
    return {"ok": True}


@router.get("/broadcasts")
async def list_broadcasts(
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Broadcast).order_by(Broadcast.created_at.desc())
    )
    return [{"id": b.id, "message": b.message,
             "created_at": b.created_at.isoformat() if b.created_at is not None else None}  # type: ignore
            for b in result.scalars().all()]


# ─── Helpers ─────────────────────────────────────────────────────────────────────

async def _count(db, model, *conditions):
    q = select(func.count()).select_from(model)
    for cond in conditions:
        q = q.where(cond)
    result = await db.execute(q)
    return result.scalar()


def _ride_dict(r: Ride) -> dict:
    return {
        "id": r.id, "user_id": r.user_id, "user_name": r.user_name,
        "user_phone": r.user_phone, "driver_id": r.driver_id,
        "driver_name": r.driver_name,
        "from_loc": r.from_loc, "to_loc": r.to_loc,
        "booking_type": r.booking_type, "service_type": r.service_type,
        "vehicle_size": r.vehicle_size, "ac": r.ac,
        "passengers": r.passengers, "price": r.price,
        "status": r.status, "cancel_reason": r.cancel_reason,
        "created_at": r.created_at.isoformat() if r.created_at is not None else None,  # type: ignore
        "completed_at": r.completed_at.isoformat() if r.completed_at is not None else None,  # type: ignore
    }


def _driver_dict(d: Driver) -> dict:
    return {
        "id": d.id, "name": d.name, "email": d.email, "phone": d.phone,
        "vehicle_type": d.vehicle_type, "plate": d.plate,
        "route_pref": d.route_pref, "ac_pref": d.ac_pref,
        "status": d.status, "is_verified": d.is_verified,
        "rating": d.rating, "jobs_done": d.jobs_done,
        "seats_total": d.seats_total,
        "filled_seats": d.filled_seats,
        "doc_status": d.doc_status,
        "profile_pic": d.profile_pic,
        "license_url": d.license_url,
        "aadhar_url": d.aadhar_url,
        "rc_url": d.rc_url,
        "insurance_url": d.insurance_url,
        "created_at": d.created_at.isoformat() if d.created_at is not None else None  # type: ignore
    }


def _coupon_dict(c: Coupon) -> dict:
    return {
        "id": c.id, "code": c.code, "discount": c.discount,
        "min_fare": c.min_fare, "expiry": c.expiry, "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at is not None else None  # type: ignore
    }


def _ticket_dict(t: SupportTicket) -> dict:
    return {
        "id": t.id, "user_id": t.user_id, "user_name": t.user_name,
        "ride_id": t.ride_id, "issue_type": t.issue_type,
        "description": t.description, "status": t.status,
        "admin_reply": t.admin_reply,
        "created_at": t.created_at.isoformat() if t.created_at is not None else None  # type: ignore
    }


def _user_dict(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "phone": u.phone,
        "role": u.role,
        "provider": u.provider,
        "provider_id": u.provider_id,
        "email_verified": u.email_verified,
        "picture": u.picture,
        "created_at": u.created_at.isoformat() if u.created_at is not None else None,  # type: ignore
    }


# ─── Admin Management ─────────────────────────────────────────────────────────


class AdminCreateIn(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    password: str


class AdminPatchIn(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None


@router.get("/admins")
async def list_admins(
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Admin).order_by(Admin.created_at.desc()))
    return [{"id": a.id, "name": a.name, "email": a.email, "phone": a.phone,
             "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in result.scalars().all()]


@router.post("/admins")
async def create_admin(
    body: AdminCreateIn,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    email = body.email.lower().strip()
    phone = (body.phone or "").strip()
    # Uniqueness checks within admins table only
    r = await db.execute(select(Admin).where((Admin.email == email) | (Admin.phone == phone)).limit(1))
    if r.scalar_one_or_none():
        raise HTTPException(400, "Email or phone already in use by an admin")

    # Create Admin record
    adm = Admin(
        name=body.name.strip(),
        email=email,
        phone=phone or None,
        password_hash=hash_password(body.password),
    )
    db.add(adm)

    # Also create legacy User admin for compatibility
    legacy = User(
        name=body.name.strip(),
        email=email,
        phone=phone or "",
        password_hash=adm.password_hash,
        role="admin",
    )
    db.add(legacy)
    await db.commit()
    await db.refresh(adm)
    return {"id": adm.id, "name": adm.name, "email": adm.email, "phone": adm.phone,
            "created_at": adm.created_at.isoformat() if adm.created_at else None}


@router.patch("/admins/{admin_id}")
async def patch_admin(
    admin_id: str,
    body: AdminPatchIn,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Admin not found")
    if body.email is not None:
        email = body.email.lower().strip()
        if email != a.email:
            r = await db.execute(select(Admin).where(Admin.email == email, Admin.id != admin_id).limit(1))
            if r.scalar_one_or_none():
                raise HTTPException(400, "Email already in use by another admin")
            a.email = email  # type: ignore
    if body.phone is not None:
        phone = body.phone.strip()
        if phone != (a.phone or ""):
            r = await db.execute(select(Admin).where(Admin.phone == phone, Admin.id != admin_id).limit(1))
            if r.scalar_one_or_none():
                raise HTTPException(400, "Phone already in use by another admin")
            a.phone = phone  # type: ignore
    if body.name is not None:
        a.name = body.name.strip()  # type: ignore
    if body.password is not None:
        a.password_hash = hash_password(body.password)  # type: ignore
    await db.commit()
    return {"ok": True}


@router.delete("/admins/{admin_id}")
async def delete_admin(
    admin_id: str,
    admin: object = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Admin not found")
    # delete legacy user admin if present
    r = await db.execute(select(User).where(User.email == a.email, User.role == "admin").limit(1))
    legacy = r.scalar_one_or_none()
    if legacy:
        await db.delete(legacy)
    await db.delete(a)
    await db.commit()
    return {"ok": True}
