from __future__ import annotations

from fastapi import Header, HTTPException, Request, Response, status

from ..core.cache import check_rate_limit
from ..core.config import settings


async def require_ai_route_access(
    request: Request,
    response: Response,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> None:
    if settings.API_ACCESS_KEY and x_api_key != settings.API_ACCESS_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    client_host = request.client.host if request.client else "unknown"
    allowed, remaining = await check_rate_limit(
        f"rate_limit:ai_chat:{client_host}",
        limit=settings.AI_ROUTE_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AI_ROUTE_RATE_LIMIT_WINDOW_SECONDS,
    )
    response.headers["X-RateLimit-Limit"] = str(settings.AI_ROUTE_RATE_LIMIT_MAX_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Window"] = str(settings.AI_ROUTE_RATE_LIMIT_WINDOW_SECONDS)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
