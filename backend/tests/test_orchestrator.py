import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.orchestrator import ChatOrchestrator
from app.services.llm_provider import MockProvider, BaseLLMProvider, LLMError


@pytest.mark.asyncio
async def test_orchestrator_prompt_assembly():
    orch = ChatOrchestrator(MockProvider())
    history = [
        {"role": "user", "content": "What is Newton's second law?"},
        {"role": "assistant", "content": "F = m * a"},
    ]
    assembled = orch.assemble_messages(history, "Give me an example.")
    assert len(assembled) == 3
    assert assembled[-1]["role"] == "user"
    assert assembled[-1]["content"] == "Give me an example."


@pytest.mark.asyncio
async def test_orchestrator_generate_with_mock_provider():
    custom_mock = MockProvider(canned_response="Photosynthesis is the process by which green plants make food.")
    orch = ChatOrchestrator(custom_mock)

    content, tokens, latency = await orch.generate_response(
        history=[],
        user_message="Explain photosynthesis."
    )

    assert "Photosynthesis" in content
    assert tokens > 0
    assert latency >= 0


@pytest.mark.asyncio
async def test_chat_endpoint_single_turn():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        payload = {
            "message": "Hello study buddy!",
            "provider": "mock"
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["message"]["role"] == "assistant"
        assert len(data["message"]["content"]) > 0
        assert data["tokens_used"] > 0
        assert data["latency_ms"] >= 0
