import os
import sys
import asyncio
from dotenv import load_dotenv

# FIX: Windows asyncio event loop compatibility for psycopg
# ProactorEventLoop is incompatible with psycopg async mode on Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("ENVIRONMENT", "development").strip().lower() != "production"
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=reload_enabled)
