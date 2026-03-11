from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db, Coupon
from ..auth import get_current_user
import uuid

router = APIRouter(prefix="/api/coupons", tags=["Coupons"])


@router.get("/validate")
async def validate_coupon(
    code: str,
    fare: int = 0,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Coupon).where(Coupon.code == code.strip().upper(), Coupon.is_active == True)
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(404, "Invalid or expired coupon code.")

    # Check expiry
    if coupon.expiry:
        try:
            exp_date = date.fromisoformat(coupon.expiry)
            if date.today() > exp_date:
                raise HTTPException(400, "This coupon has expired.")
        except ValueError:
            pass

    # Check minimum fare
    if fare > 0 and fare < coupon.min_fare:
        raise HTTPException(400, f"Minimum fare ₹{coupon.min_fare} required for this coupon.")

    return {
        "code": coupon.code,
        "discount": coupon.discount,
        "min_fare": coupon.min_fare,
        "expiry": coupon.expiry
    }
