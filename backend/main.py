import json
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

# ⚠️  load_dotenv MUST come before any router imports so that module-level
# os.getenv() calls inside the routers (e.g. GOOGLE_CLIENT_ID in google_auth.py)
# pick up values from .env instead of returning empty strings.
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status as ws_status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db, get_db, Setting, AsyncSessionLocal
from .routers import auth, google_auth, users, drivers, rides, locations, coupons, support, admin
from .ws.manager import manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
def _cors_origins() -> list[str]:
    return cast(list[str], settings["cors_origins"])

# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("=" * 80)
    logger.info("🚀 STARTING NANDU TRAVELS API SERVER")
    logger.info("=" * 80)
    
    # Validate Google OAuth Configuration
    google_client_id = str(settings["google_client_id"])
    google_client_secret = str(settings["google_client_secret"])
    google_redirect_uri = str(settings["google_redirect_uri"])
    
    logger.info("\n🔐 Google OAuth Configuration Check:")
    if google_client_id and google_client_secret:
        logger.info(f"  ✅ GOOGLE_CLIENT_ID: {google_client_id[:30]}...")
        logger.info(f"  ✅ GOOGLE_CLIENT_SECRET: {'*' * 20}")
        logger.info(f"  ✅ GOOGLE_REDIRECT_URI: {google_redirect_uri}")
    else:
        logger.warning("  ⚠️  Google OAuth not fully configured!")
        if not google_client_id:
            logger.warning("    - Missing GOOGLE_CLIENT_ID in .env")
        if not google_client_secret:
            logger.warning("    - Missing GOOGLE_CLIENT_SECRET in .env")
            
    # Log CORS configuration
    cors_origins = _cors_origins()
    logger.info(f"\n🔓 CORS Configuration:")
    if cors_origins == ["*"]:
        logger.warning("  ⚠️  CORS_ORIGINS is set to '*' (allowing all origins)")
    else:
        logger.info(f"  ✅ Allowed origins: {', '.join(cors_origins)}")
    
    # Initialize database
    await init_db()
    logger.info("\n💾 Database initialized")
    
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        defaults = {
            "surge_multiplier": "1.0",
            "auto_assign": "true",
            "accept_bookings": "true",
            "maintenance": "false",
        }
        for key, val in defaults.items():
            existing = await db.execute(select(Setting).where(Setting.key == key))
            if not existing.scalar_one_or_none():
                db.add(Setting(key=key, value=val))
        await db.commit()
    
    logger.info("\n✅ All startup checks passed!")
    logger.info("=" * 80)
    logger.info("📡 API Server Ready — %s/docs", settings["app_base_url"])
    logger.info("=" * 80 + "\n")
    
    yield
    
    # Shutdown tasks
    logger.info("🛑 Shutting down Nandu Travels API Server...")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Travel With Nandu — API",
    description="Production-ready ride-booking backend. Firebase → FastAPI migration.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(google_auth.router)
app.include_router(users.router)
app.include_router(drivers.router)
app.include_router(rides.router)
app.include_router(locations.router)
app.include_router(coupons.router)
app.include_router(support.router)
app.include_router(admin.router)

# ─── Health Check ────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "environment": settings["environment"],
        "database": "postgres" if "postgres" in str(settings["database_url"]).lower() else "sqlite",
    }

@app.get("/api/status", tags=["Health"])
async def app_status():
    return {
        "status": "running",
        "app": "Travel With Nandu API",
        "version": "1.0.0",
        "docs": "/docs",
        "environment": settings["environment"],
        "app_base_url": settings["app_base_url"],
    }

# ─── WebSocket — Admin Live Feed ──────────────────────────────────────────────

@app.websocket("/ws/admin")
async def ws_admin(websocket: WebSocket):
    await websocket.accept()
    # First message must be an auth token
    try:
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=10)
    except asyncio.TimeoutError:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return
    from .auth import decode_token
    token = auth_data.get("token", "")
    payload = decode_token(token)
    if not payload or payload.get("role") != "admin":
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_admin(websocket)
    try:
        await websocket.send_text(json.dumps({"event": "connected", "data": {}}))
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_admin(websocket)


# ─── WebSocket — Driver Job Feed ──────────────────────────────────────────────

@app.websocket("/ws/driver/{driver_id}")
async def ws_driver(websocket: WebSocket, driver_id: str):
    await websocket.accept()
    # First message must be an auth token
    try:
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=10)
    except asyncio.TimeoutError:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return
    from .auth import decode_token
    token = auth_data.get("token", "")
    payload = decode_token(token)
    if not payload or payload.get("role") != "driver":
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_driver(driver_id, websocket)
    try:
        await websocket.send_text(json.dumps({"event": "connected", "data": {}}))
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_driver(driver_id, websocket)


# ─── Static Files (must be last to not shadow API routes) ─────────────────────

# Serve frontend from public/ directory
public_dir = Path(__file__).parent.parent / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="static")
else:
    print(f"⚠️  Warning: public directory not found at {public_dir}")
