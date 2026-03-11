import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from ..database import get_db, User, Driver, Admin
from ..auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["Users"])


class PatchUserIn(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    picture: Optional[str] = None


@router.post("/me")
async def create_or_update_me(
    body: PatchUserIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Compatibility endpoint for profile create flows from legacy frontend."""
    if body.name:
        user.name = body.name.strip()  # type: ignore
    if body.phone:
        user.phone = body.phone.strip()  # type: ignore
    await db.commit()
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "picture": user.picture,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at is not None else None,
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "picture": user.picture,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at is not None else None
    }


@router.patch("/me")
async def patch_me(
    body: PatchUserIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if body.name:
        user.name = body.name.strip()  # type: ignore
    if body.phone:
        phone = body.phone.strip()
        if phone != user.phone:
            existing = await db.execute(
                select(User).where(User.phone == phone, User.id != user.id).limit(1)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(400, "Phone already in use by another user")
        user.phone = phone  # type: ignore
    if body.picture is not None:
        user.picture = body.picture.strip()  # type: ignore
    await db.commit()
    return {"ok": True, "name": user.name, "phone": user.phone, "picture": user.picture}


@router.post("/me/picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content_type = (file.content_type or "").lower()
    allowed_types = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    if content_type not in allowed_types:
        raise HTTPException(400, "Only JPG, PNG, or WEBP images are allowed")

    upload_dir = Path(__file__).resolve().parent.parent.parent / "public" / "uploads" / "users"
    upload_dir.mkdir(parents=True, exist_ok=True)

    previous_picture = (user.picture or "").strip()

    filename = f"{user.id}_{uuid.uuid4().hex[:10]}{allowed_types[content_type]}"
    target = upload_dir / filename

    with target.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    user.picture = f"/uploads/users/{filename}"  # type: ignore
    await db.commit()

    if previous_picture.startswith("/uploads/users/"):
        old_file = upload_dir / previous_picture.replace("/uploads/users/", "", 1)
        try:
            if old_file.exists() and old_file.is_file() and old_file != target:
                old_file.unlink()
        except OSError:
            pass

    return {"ok": True, "picture": user.picture}
