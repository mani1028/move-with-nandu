import asyncio
from pathlib import Path
from typing import cast

import requests
from fastapi import HTTPException, UploadFile

from .config import settings


PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public" / "uploads"
SUPABASE_URL = str(settings["supabase_url"])
SUPABASE_SERVICE_ROLE_KEY = str(settings["supabase_service_role_key"])
MAX_FILE_SIZE_BYTES = cast(int, settings["max_file_size_bytes"])


def _is_supabase_storage_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


async def read_validated_upload(
    file: UploadFile,
    *,
    allowed_types: dict[str, str],
    label: str,
) -> tuple[bytes, str]:
    content_type = (file.content_type or "").lower()
    extension = allowed_types.get(content_type)
    if not extension:
        raise HTTPException(400, f"{label} must be one of: {', '.join(sorted(allowed_types))}")

    payload = await file.read()
    await file.seek(0)
    if not payload:
        raise HTTPException(400, f"{label} is empty")
    if len(payload) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(400, f"{label} exceeds max size of {MAX_FILE_SIZE_BYTES} bytes")
    return payload, extension


async def save_public_file(
    *,
    content: bytes,
    content_type: str,
    bucket: str,
    object_path: str,
    local_dir: str,
) -> str:
    if _is_supabase_storage_enabled():
        return await _upload_to_supabase(
            content=content,
            content_type=content_type,
            bucket=bucket,
            object_path=object_path,
        )
    return await _save_locally(content=content, local_dir=local_dir, filename=Path(object_path).name)


async def delete_public_file(*, current_url: str, bucket: str, local_dir: str) -> None:
    if not current_url:
        return
    if current_url.startswith("/uploads/"):
        await _delete_local_file(current_url=current_url, local_dir=local_dir)
        return
    if _is_supabase_storage_enabled():
        await _delete_supabase_file(current_url=current_url, bucket=bucket)


async def _upload_to_supabase(*, content: bytes, content_type: str, bucket: str, object_path: str) -> str:
    endpoint = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{object_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    def _send() -> requests.Response:
        return requests.post(endpoint, headers=headers, data=content, timeout=30)

    response = cast(requests.Response, await asyncio.to_thread(_send))
    status_code = cast(int, response.status_code)
    if status_code >= 300:
        raise HTTPException(500, f"Supabase upload failed: {response.text}")
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{object_path}"


async def _delete_supabase_file(*, current_url: str, bucket: str) -> None:
    marker = f"/storage/v1/object/public/{bucket}/"
    if marker not in current_url:
        return
    object_path = current_url.split(marker, 1)[1]
    endpoint = f"{SUPABASE_URL}/storage/v1/object/remove"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "application/json",
    }

    def _send() -> requests.Response:
        return requests.post(endpoint, headers=headers, json={"bucketId": bucket, "prefixes": [object_path]}, timeout=30)

    try:
        await asyncio.to_thread(_send)
    except requests.RequestException:
        return


async def _save_locally(*, content: bytes, local_dir: str, filename: str) -> str:
    target_dir = PUBLIC_DIR / local_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    await asyncio.to_thread(target.write_bytes, content)
    return f"/uploads/{local_dir}/{filename}"


async def _delete_local_file(*, current_url: str, local_dir: str) -> None:
    prefix = f"/uploads/{local_dir}/"
    if not current_url.startswith(prefix):
        return
    target = PUBLIC_DIR / local_dir / current_url.replace(prefix, "", 1)
    try:
        if target.exists() and target.is_file():
            await asyncio.to_thread(target.unlink)
    except OSError:
        return