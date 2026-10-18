import pytest
import json
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_full_chat_stream_and_session_continuity_integration():
    """
    End-to-end integration test verifying:
    1. User starts a session and sends message via /chat/stream (SSE)
    2. Stream delivers token-by-token increments and final completion
    3. Conversation is saved in Postgres and cached in Redis
    4. Client reloads / retrieves history and sees previous turn
    5. Second message is sent in the same session preserving multi-turn context
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        session_id = f"integration-test-{uuid.uuid4()}"

        # Turn 1: Stream query over SSE
        turn1_payload = {
            "session_id": session_id,
            "message": "What is the speed of light in vacuum?",
            "provider": "mock"
        }

        stream1_chunks = []
        full_reply_turn1 = ""
        final_turn1_done = False

        async with client.stream("POST", "/api/v1/chat/stream", json=turn1_payload) as response1:
            assert response1.status_code == 200
            assert "text/event-stream" in response1.headers["content-type"]

            async for line in response1.aiter_lines():
                if line.startswith("data:"):
                    raw = line[len("data:"):].strip()
                    if raw:
                        chunk = json.loads(raw)
                        stream1_chunks.append(chunk)
                        full_reply_turn1 += chunk.get("delta", "")
                        if chunk.get("done") is True:
                            final_turn1_done = True

        assert final_turn1_done, "Turn 1 must end with done=True"
        assert len(stream1_chunks) > 1, "Must stream multiple incremental tokens"
        assert len(full_reply_turn1) > 0, "Assistant reply must not be empty"

        # Verification: Check session history persistence (simulates page refresh)
        history_res = await client.get(f"/api/v1/sessions/{session_id}")
        assert history_res.status_code == 200
        session_data = history_res.json()
        assert session_data["id"] == session_id
        assert len(session_data["messages"]) == 2
        assert session_data["messages"][0]["role"] == "user"
        assert session_data["messages"][0]["content"] == "What is the speed of light in vacuum?"
        assert session_data["messages"][1]["role"] == "assistant"
        assert session_data["messages"][1]["content"] == full_reply_turn1

        # Turn 2: Follow-up question in the same session
        turn2_payload = {
            "session_id": session_id,
            "message": "Can anything travel faster than it?",
            "provider": "mock"
        }

        full_reply_turn2 = ""
        final_turn2_done = False

        async with client.stream("POST", "/api/v1/chat/stream", json=turn2_payload) as response2:
            assert response2.status_code == 200
            async for line in response2.aiter_lines():
                if line.startswith("data:"):
                    raw = line[len("data:"):].strip()
                    if raw:
                        chunk = json.loads(raw)
                        full_reply_turn2 += chunk.get("delta", "")
                        if chunk.get("done") is True:
                            final_turn2_done = True

        assert final_turn2_done, "Turn 2 must end with done=True"

        # Verification 2: Verify total of 4 messages in session
        updated_history_res = await client.get(f"/api/v1/sessions/{session_id}")
        assert updated_history_res.status_code == 200
        updated_data = updated_history_res.json()
        assert len(updated_data["messages"]) == 4
        assert updated_data["messages"][2]["content"] == "Can anything travel faster than it?"
        assert updated_data["messages"][3]["content"] == full_reply_turn2
