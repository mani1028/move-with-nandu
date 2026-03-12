import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("ENVIRONMENT", "development").strip().lower() != "production"
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=reload_enabled)
