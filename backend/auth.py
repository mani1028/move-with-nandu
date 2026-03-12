from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, cast
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .database import get_db, User, Driver, Admin
from .config import settings

SECRET_KEY = cast(str, settings["secret_key"])
ALGORITHM = cast(str, settings["algorithm"])
EXPIRE_MIN = cast(int, settings["access_token_expire_minutes"])

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=EXPIRE_MIN))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return dict(jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]))  # type: ignore
    except JWTError:
        return None


# ─── Dependencies ───────────────────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_exc
    payload = decode_token(token)
    if not payload:
        raise cred_exc
    p: Dict = cast(Dict, payload)
    uid: str = p.get("sub") or ""
    role: str = p.get("role") or "user"
    if not uid:
        raise cred_exc

    if role in ("user", "admin"):  # Admins can also access user-scoped endpoints
        # First try to resolve as a User
        result = await db.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()
        if user:
            return user
        # If not found in users, try admin table (admins created separately)
        result = await db.execute(select(Admin).where(Admin.id == uid))
        admin = result.scalar_one_or_none()
        if admin:
            return admin
        raise cred_exc
    raise cred_exc


async def get_current_driver(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Driver:
    cred_exc = HTTPException(status_code=401, detail="Invalid or expired token")
    if not token:
        raise cred_exc
    payload = decode_token(token)
    if payload is None or payload.get("role") != "driver":
        raise cred_exc
    p: Dict = cast(Dict, payload)
    uid: str = p.get("sub") or ""
    if not uid:
        raise cred_exc
    result = await db.execute(select(Driver).where(Driver.id == uid))
    driver = result.scalar_one_or_none()
    if not driver:
        raise cred_exc
    return driver


async def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> object:
    cred_exc = HTTPException(status_code=403, detail="Admin access required")
    if not token:
        raise cred_exc
    payload = decode_token(token)
    if payload is None or payload.get("role") != "admin":
        raise cred_exc
    p: Dict = cast(Dict, payload)
    uid: str = p.get("sub") or ""
    if not uid:
        raise cred_exc
    # Prefer Admin table entries (new separate admin records)
    result = await db.execute(select(Admin).where(Admin.id == uid))
    admin = result.scalar_one_or_none()
    if admin:
        return admin

    # Fallback to legacy User-based admins
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user or str(user.role) != "admin":  # type: ignore
        raise cred_exc
    return user
