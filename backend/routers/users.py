import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Optional, cast
from ..database import get_db, User, Driver, Admin
from ..auth import get_current_user
from ..config import settings
from ..storage import delete_public_file, read_validated_upload, save_public_file

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
    allowed_types = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    content, extension = await read_validated_upload(
        file,
        allowed_types=allowed_types,
        label="Profile image",
    )

    previous_picture = (user.picture or "").strip()
    filename = f"{user.id}_{uuid.uuid4().hex[:10]}{extension}"
    cast(Any, user).picture = await save_public_file(
        content=content,
        content_type=(file.content_type or "application/octet-stream").lower(),
        bucket=str(settings["profile_upload_bucket"]),
        object_path=f"users/{filename}",
        local_dir="users",
    )
    await db.commit()

    await delete_public_file(
        current_url=previous_picture,
        bucket=str(settings["profile_upload_bucket"]),
        local_dir="users",
    )

    return {"ok": True, "picture": user.picture}
