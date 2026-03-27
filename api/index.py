import sys
import asyncio
import json
import traceback

_DEPLOY_VERSION = "v20260327-1"  # bump to verify new deployment is live

# FIX: Windows asyncio event loop compatibility for psycopg
if sys.platform == 'win32':
	asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_import_error: Exception | None = None
_import_traceback = ""

try:
	from backend.main import app
except Exception as exc:  # pragma: no cover - only used for deployment diagnostics
	_import_error = exc
	_import_traceback = traceback.format_exc()

	async def _fallback_app(scope, receive, send):  # type: ignore
		if scope.get("type") != "http":
			await send({"type": "http.response.start", "status": 500, "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
			await send({"type": "http.response.body", "body": b"Application startup failed", "more_body": False})
			return

		detail = {
			"deploy_version": _DEPLOY_VERSION,
			"error": "Application import/startup failed",
			"exception": str(_import_error),
			"traceback": _import_traceback.splitlines()[-25:],
		}
		body = json.dumps(detail).encode("utf-8")
		headers = [
			(b"content-type", b"application/json; charset=utf-8"),
			(b"cache-control", b"no-store"),
		]
		await send({"type": "http.response.start", "status": 500, "headers": headers})
		await send({"type": "http.response.body", "body": body, "more_body": False})

	app = _fallback_app

# ✅ Ensure app is always exported for Vercel to detect
__all__ = ['app']