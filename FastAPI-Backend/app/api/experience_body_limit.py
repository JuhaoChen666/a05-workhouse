"""Bound P2 request bodies before multipart files can exhaust spool storage."""
from fastapi import HTTPException
from starlette.responses import JSONResponse

MAX_REQUEST_BYTES = 17 * 1024 * 1024  # 16 MiB PDF plus bounded multipart metadata.


class ExperienceBodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        applies = any(path == prefix or path.startswith(prefix + "/") for prefix in (
            "/api/experiences", "/api/experience-imports"))
        if scope["type"] != "http" or not applies:
            return await self.app(scope, receive, send)
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    length = int(value)
                except ValueError:
                    length = -1
                if length < 0 or length > MAX_REQUEST_BYTES:
                    response = JSONResponse({"detail":{"code":"REQUEST_SIZE", "message":"P2 request body exceeds 17 MiB or has invalid length"}},status_code=413)
                    return await response(scope,receive,send)
        total = 0
        async def limited_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body",b""))
                if total > MAX_REQUEST_BYTES:
                    raise HTTPException(413,{"code":"REQUEST_SIZE", "message":"P2 request body exceeds 17 MiB"})
            return message
        return await self.app(scope,limited_receive,send)
