from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.services.memory import memory_service
from app.schemas.session import (
    ConversationRead,
    ConversationDetail,
    CreateConversationRequest,
    MessageRead
)

router = APIRouter()


@router.get("", response_model=List[ConversationRead], summary="List all conversations")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """Returns a list of conversations ordered by most recently updated."""
    conversations_with_counts = await memory_service.list_conversations(db)
    return [
        ConversationRead(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=count
        )
        for conv, count in conversations_with_counts
    ]


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED, summary="Create a new conversation session")
async def create_session(
    payload: CreateConversationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Creates a new conversation session."""
    conv = await memory_service.get_or_create_conversation(db, title=payload.title)
    return ConversationRead(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=0
    )


@router.get("/{session_id}", response_model=ConversationDetail, summary="Get conversation history")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves full conversation details including chronological message history."""
    conv = await memory_service.get_conversation(db, session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation session not found")

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[MessageRead.model_validate(m) for m in conv.messages]
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete conversation")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Deletes conversation from database and flushes Redis cache."""
    deleted = await memory_service.delete_conversation(db, redis, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation session not found")
    return None
