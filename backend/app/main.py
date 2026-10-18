import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger, request_id_ctx
from app.core.database import init_db, engine
from app.core.redis import redis_manager
from app.api.v1.router import api_router
from app.services.llm_provider import LLMError


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Study Assistant AI Chatbot Backend...")
    await init_db()
    await redis_manager.connect()
    yield
    # Shutdown
    logger.info("Shutting down backend services...")
    await redis_manager.close()
    if engine:
        await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handler for LLM Provider Errors (graceful degradation)
@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    req_id = request_id_ctx.get() or "N/A"
    logger.warning(
        f"LLM provider error on {request.method} {request.url.path}: {str(exc)}",
        extra={"request_id": req_id}
    )
    return JSONResponse(
        status_code=502,
        content={
            "detail": str(exc) or "The AI service is temporarily unavailable. Please retry shortly.",
            "error_type": "llm_provider_error"
        },
        headers={"X-Request-ID": req_id}
    )


# Request ID and Structured Logging Middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(req_id)
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id

        # Log structured request summary (without logging private message bodies at INFO level)
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code}",
            extra={
                "latency_ms": latency_ms,
                "status_code": response.status_code,
                "request_id": req_id
            }
        )
        return response
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.error(
            f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}",
            exc_info=True,
            extra={"latency_ms": latency_ms, "request_id": req_id}
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please try again later."},
            headers={"X-Request-ID": req_id}
        )
    finally:
        request_id_ctx.reset(token)


# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/", summary="Root endpoint")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs"
    }
