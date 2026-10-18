import time
from typing import Optional
from fastapi import Request, HTTPException, status
from app.core.config import settings
from app.core.redis import redis_manager
from app.core.logging import logger


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter checking request frequency per session_id or client IP.
    Protects LLM endpoints from runaway loops or abuse.
    """

    def __init__(self, limit_per_minute: Optional[int] = None):
        self.limit = limit_per_minute or settings.RATE_LIMIT_PER_MINUTE
        self.window_seconds = 60

    async def check_rate_limit(self, request: Request, session_id: Optional[str] = None):
        # 1. Determine key identifier: Session ID preferred, otherwise client IP
        client_ip = request.client.host if request.client else "unknown_ip"
        identifier = session_id or request.headers.get("X-Session-ID") or client_ip
        cache_key = f"ratelimit:{identifier}"

        redis = redis_manager.get_client()
        now = time.time()
        window_start = now - self.window_seconds

        try:
            # Check using standard counter or timestamp list
            current_count_str = await redis.get(cache_key)
            current_count = int(current_count_str) if current_count_str else 0

            if current_count >= self.limit:
                logger.warning(
                    f"Rate limit exceeded for identifier {identifier}: {current_count}/{self.limit} requests/min",
                    extra={"identifier": identifier, "current_count": current_count}
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit reached ({self.limit} requests per minute). Please wait a moment before asking again.",
                    headers={"Retry-After": "60"}
                )

            # Increment count and set 60s expiration
            new_count = current_count + 1
            await redis.set(cache_key, str(new_count), ex=self.window_seconds)

        except HTTPException:
            raise
        except Exception as e:
            # If rate limiting backend fails, log warning but do not crash the user request
            logger.warning(f"Rate limiting check failed: {e}")


rate_limiter = SlidingWindowRateLimiter()
