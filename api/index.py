import json
import traceback

_import_error: Exception | None = None
_import_traceback = ""

try:
	from backend.main import app as app
except Exception as exc:  # pragma: no cover - only used for deployment diagnostics
	_import_error = exc
	_import_traceback = traceback.format_exc()

	async def app(scope, receive, send):  # type: ignore[no-redef]
		if scope.get("type") != "http":
			await send({"type": "http.response.start", "status": 500, "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
			await send({"type": "http.response.body", "body": b"Application startup failed", "more_body": False})
			return

		detail = {
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