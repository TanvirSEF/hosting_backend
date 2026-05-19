import time
from collections import defaultdict, deque
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        limit = settings.RATE_LIMIT_PER_MINUTE
        if limit <= 0:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self.requests[client_host]
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()

        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )

        bucket.append(now)
        return await call_next(request)
