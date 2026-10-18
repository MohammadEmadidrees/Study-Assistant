import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_manager
from app.services.memory import memory_service


@pytest.mark.asyncio
async def test_memory_service_direct_crud():
    async with AsyncSessionLocal() as db:
        redis_client = redis_manager.get_client()
        session_id = str(uuid.uuid4())

        # 1. Create conversation
        conv = await memory_service.get_or_create_conversation(db, session_id=session_id, title="Test Math Chat")
        await db.commit()
        assert conv.id == session_id
        assert conv.title == "Test Math Chat"

        # 2. Save user message
        msg1 = await memory_service.save_message(
            db, redis_client, session_id, role="user", content="What is Pythagoras theorem?"
        )
        await db.commit()
        assert msg1.role == "user"

        # 3. Save assistant message
        msg2 = await memory_service.save_message(
            db, redis_client, session_id, role="assistant", content="a^2 + b^2 = c^2", tokens_used=12
        )
        await db.commit()
        assert msg2.tokens_used == 12

        # 4. Read recent messages (verifies Redis / DB hydration)
        history = await memory_service.get_recent_messages(db, redis_client, session_id)
        assert len(history) == 2
        assert history[0]["content"] == "What is Pythagoras theorem?"
        assert history[1]["content"] == "a^2 + b^2 = c^2"

        # 5. Verify conversation retrieval
        conv_full = await memory_service.get_conversation(db, session_id)
        assert conv_full is not None
        assert len(conv_full.messages) == 2

        # 6. Delete conversation
        deleted = await memory_service.delete_conversation(db, redis_client, session_id)
        await db.commit()
        assert deleted is True

        # 7. Confirm deletion
        conv_after = await memory_service.get_conversation(db, session_id)
        assert conv_after is None


@pytest.mark.asyncio
async def test_sessions_api_endpoints():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        # Create session
        create_res = await client.post("/api/v1/sessions", json={"title": "Physics 101"})
        assert create_res.status_code == 201
        session_data = create_res.json()
        session_id = session_data["id"]
        assert session_data["title"] == "Physics 101"

        # Send a message to the session
        chat_res = await client.post("/api/v1/chat", json={
            "session_id": session_id,
            "message": "Define acceleration.",
            "provider": "mock"
        })
        assert chat_res.status_code == 200

        # Retrieve session detail and verify persisted message history
        detail_res = await client.get(f"/api/v1/sessions/{session_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert len(detail["messages"]) >= 2
        assert detail["messages"][0]["role"] == "user"
        assert detail["messages"][1]["role"] == "assistant"

        # List all sessions
        list_res = await client.get("/api/v1/sessions")
        assert list_res.status_code == 200
        sessions = list_res.json()
        assert any(s["id"] == session_id for s in sessions)

        # Delete session
        del_res = await client.delete(f"/api/v1/sessions/{session_id}")
        assert del_res.status_code == 204
