import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.config import settings

router = APIRouter()
START_TIME = time.time()


@router.get("/health", summary="Application health check")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    db_status = "unhealthy"
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    redis_status = "unhealthy"
    try:
        pong = await redis.ping()
        if pong:
            redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"

    uptime_seconds = round(time.time() - START_TIME, 2)

    return {
        "status": "online",
        "environment": settings.ENV,
        "uptime_seconds": uptime_seconds,
        "database": db_status,
        "redis": redis_status,
        "default_llm_provider": settings.DEFAULT_LLM_PROVIDER
    }
