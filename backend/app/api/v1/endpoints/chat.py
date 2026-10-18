import uuid
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, status, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.schemas.chat import ChatRequest, ChatResponse, ChatMessage, StreamChunk
from app.services.orchestrator import orchestrator
from app.services.llm_provider import LLMError
from app.services.memory import memory_service
from app.core.rate_limiter import rate_limiter
from app.core.database import get_db, AsyncSessionLocal
from app.core.redis import get_redis, redis_manager
from app.core.logging import logger

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Synchronous single-turn or multi-turn chat completion with persistence"
)
async def chat_endpoint(
    request: ChatRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
) -> ChatResponse:
    """
    Handles standard request-response chat interactions with dual-tier persistence:
    1. Checks session/IP rate limiting
    2. Loads recent context from Redis / Postgres
    3. Saves incoming user message
    4. Calls orchestrator
    5. Saves generated assistant response
    """
    await rate_limiter.check_rate_limit(req, session_id=request.session_id)
    conv = await memory_service.get_or_create_conversation(db, session_id=request.session_id)
    session_id = conv.id

    try:
        # Load conversation history for prompt assembly
        history = await memory_service.get_recent_messages(db, redis, session_id)

        # Save user message
        await memory_service.save_message(
            db, redis, session_id, role="user", content=request.message
        )

        # Execute generation
        content, tokens, latency_ms = await orchestrator.generate_response(
            history=history,
            user_message=request.message,
            provider_name=request.provider
        )

        # Save assistant message
        await memory_service.save_message(
            db, redis, session_id, role="assistant", content=content, tokens_used=tokens
        )
        await db.commit()

        return ChatResponse(
            session_id=session_id,
            message=ChatMessage(role="assistant", content=content),
            tokens_used=tokens,
            latency_ms=latency_ms
        )

    except LLMError as err:
        logger.warning(f"Degraded response for session {session_id}: {err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err)
        )
    except Exception as exc:
        logger.error(f"Unexpected chat endpoint error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your chat request."
        )


@router.post(
    "/chat/stream",
    summary="Stream chat response token-by-token via Server-Sent Events (SSE) with persistence"
)
async def chat_stream_endpoint(
    request: ChatRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
) -> EventSourceResponse:
    """
    Server-Sent Events endpoint streaming response tokens as they arrive from the LLM adapter.
    Persists user message and completed assistant reply to database and cache.
    """
    await rate_limiter.check_rate_limit(req, session_id=request.session_id)
    conv = await memory_service.get_or_create_conversation(db, session_id=request.session_id)
    session_id = conv.id

    # Retrieve history and save user message prior to stream kickoff
    history = await memory_service.get_recent_messages(db, redis, session_id)
    await memory_service.save_message(
        db, redis, session_id, role="user", content=request.message
    )
    await db.commit()

    async def event_generator() -> AsyncGenerator[dict, None]:
        accumulated_chunks = []
        collected_tokens = 0

        try:
            async for token in orchestrator.stream_response(
                history=history,
                user_message=request.message,
                provider_name=request.provider
            ):
                if await req.is_disconnected():
                    logger.info(f"Client disconnected during stream for session {session_id}")
                    break

                collected_tokens += 1
                accumulated_chunks.append(token)
                chunk = StreamChunk(
                    session_id=session_id,
                    delta=token,
                    done=False
                )
                yield {
                    "event": "message",
                    "data": chunk.model_dump_json()
                }

            # Persist accumulated assistant response
            full_assistant_reply = "".join(accumulated_chunks)
            if full_assistant_reply:
                try:
                    async with AsyncSessionLocal() as post_stream_db:
                        active_redis = redis_manager.get_client()
                        await memory_service.save_message(
                            post_stream_db,
                            active_redis,
                            session_id,
                            role="assistant",
                            content=full_assistant_reply,
                            tokens_used=collected_tokens
                        )
                        await post_stream_db.commit()
                except Exception as save_err:
                    logger.error(f"Failed to persist streamed assistant reply: {save_err}")

            # Final completion chunk
            final_chunk = StreamChunk(
                session_id=session_id,
                delta="",
                done=True,
                tokens_used=collected_tokens
            )
            yield {
                "event": "message",
                "data": final_chunk.model_dump_json()
            }

        except LLMError as err:
            logger.warning(f"Stream error for session {session_id}: {err}")
            err_chunk = StreamChunk(
                session_id=session_id,
                delta="",
                done=True,
                error=str(err)
            )
            yield {
                "event": "error",
                "data": err_chunk.model_dump_json()
            }
        except Exception as exc:
            logger.error(f"Unexpected streaming exception: {exc}", exc_info=True)
            err_chunk = StreamChunk(
                session_id=session_id,
                delta="",
                done=True,
                error="An unexpected error occurred during streaming."
            )
            yield {
                "event": "error",
                "data": err_chunk.model_dump_json()
            }

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )
