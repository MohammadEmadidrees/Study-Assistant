import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message
from app.core.config import settings
from app.core.logging import logger


class MemoryService:
    """
    Dual-layer conversation memory service:
    1. PostgreSQL: authoritative, persistent archival of complete conversation history.
    2. Redis: low-latency caching of active session's recent N messages for high-speed prompt assembly.
    """

    def _redis_key(self, session_id: str) -> str:
        return f"session:{session_id}:messages"

    async def get_or_create_conversation(
        self,
        db: AsyncSession,
        session_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Conversation:
        """Finds existing conversation or creates a new one."""
        if session_id:
            query = select(Conversation).where(Conversation.id == session_id).options(selectinload(Conversation.messages))
            result = await db.execute(query)
            conversation = result.scalar_one_or_none()
            if conversation:
                return conversation

        # Create new conversation
        new_id = session_id or str(uuid.uuid4())
        conversation = Conversation(
            id=new_id,
            title=title or "New Conversation",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(conversation)
        await db.flush()
        logger.info(f"Created new conversation session: {new_id}")
        return conversation

    async def get_recent_messages(
        self,
        db: AsyncSession,
        redis_client,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Retrieves recent messages for prompt assembly.
        Checks Redis cache first. On miss, loads from PostgreSQL and hydrates Redis.
        """
        max_msgs = limit or settings.MAX_HISTORY_MESSAGES
        cache_key = self._redis_key(session_id)

        # 1. Try Redis cache
        try:
            cached_raw = await redis_client.lrange(cache_key, -max_msgs, -1)
            if cached_raw:
                messages = [json.loads(m) for m in cached_raw]
                logger.debug(f"Redis cache HIT for session {session_id} ({len(messages)} messages)")
                return messages
        except Exception as e:
            logger.warning(f"Redis read error for session {session_id}: {e}")

        # 2. On cache miss or empty, query PostgreSQL
        logger.debug(f"Redis cache MISS for session {session_id}. Querying database...")
        query = (
            select(Message)
            .where(Message.conversation_id == session_id)
            .order_by(desc(Message.created_at))
            .limit(max_msgs)
        )
        result = await db.execute(query)
        db_messages = list(reversed(result.scalars().all()))

        formatted = [{"role": m.role, "content": m.content} for m in db_messages]

        # 3. Hydrate Redis cache
        if formatted:
            try:
                # Clear and re-populate
                await redis_client.delete(cache_key)
                for item in formatted:
                    await redis_client.rpush(cache_key, json.dumps(item))
                await redis_client.ltrim(cache_key, -max_msgs, -1)
            except Exception as e:
                logger.warning(f"Failed to hydrate Redis cache: {e}")

        return formatted

    async def save_message(
        self,
        db: AsyncSession,
        redis_client,
        session_id: str,
        role: str,
        content: str,
        tokens_used: int = 0
    ) -> Message:
        """
        Saves a message to PostgreSQL and updates the Redis active window cache.
        """
        # Ensure conversation exists
        await self.get_or_create_conversation(db, session_id=session_id)

        # 1. Persist to PostgreSQL
        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=session_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
            created_at=datetime.now(timezone.utc)
        )
        db.add(msg)

        # Update conversation timestamp & automatic title if first user message
        conv_query = select(Conversation).where(Conversation.id == session_id)
        conv_res = await db.execute(conv_query)
        conv = conv_res.scalar_one_or_none()
        if conv:
            conv.updated_at = datetime.now(timezone.utc)
            if conv.title == "New Conversation" and role == "user":
                # Truncate user prompt for clean title
                clean_title = content.strip().split("\n")[0][:40]
                if len(content.strip()) > 40:
                    clean_title += "..."
                conv.title = clean_title

        await db.flush()

        # 2. Push to Redis active cache
        try:
            cache_key = self._redis_key(session_id)
            cached_item = json.dumps({"role": role, "content": content})
            await redis_client.rpush(cache_key, cached_item)
            await redis_client.ltrim(cache_key, -settings.MAX_HISTORY_MESSAGES, -1)
        except Exception as e:
            logger.warning(f"Failed to push message to Redis for {session_id}: {e}")

        return msg

    async def list_conversations(
        self,
        db: AsyncSession,
        limit: int = 50
    ) -> List[Tuple[Conversation, int]]:
        """Lists recent conversations with their message count."""
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .execution_options(populate_existing=True)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        result = await db.execute(query)
        conversations = result.scalars().all()
        return [(c, len(c.messages)) for c in conversations]

    async def get_conversation(
        self,
        db: AsyncSession,
        session_id: str
    ) -> Optional[Conversation]:
        """Retrieves conversation with all associated messages."""
        query = (
            select(Conversation)
            .where(Conversation.id == session_id)
            .options(selectinload(Conversation.messages))
            .execution_options(populate_existing=True)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def delete_conversation(
        self,
        db: AsyncSession,
        redis_client,
        session_id: str
    ) -> bool:
        """Deletes conversation and cleans up Redis cache."""
        conv = await self.get_conversation(db, session_id)
        if not conv:
            return False

        await db.delete(conv)
        await db.flush()

        try:
            await redis_client.delete(self._redis_key(session_id))
        except Exception as e:
            logger.warning(f"Failed to delete Redis key for {session_id}: {e}")

        logger.info(f"Deleted conversation session {session_id}")
        return True


memory_service = MemoryService()
