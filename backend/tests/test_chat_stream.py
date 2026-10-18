import pytest
import json
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.orchestrator import orchestrator
from app.services.llm_provider import MockProvider, LLMError


@pytest.mark.asyncio
async def test_chat_stream_token_delivery():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        payload = {
            "message": "Explain the concept of inertia.",
            "provider": "mock"
        }

        async with client.stream("POST", "/api/v1/chat/stream", json=payload) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            chunks = []
            final_received = False
            full_text = ""

            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    raw_data = line[len("data:"):].strip()
                    if raw_data:
                        data = json.loads(raw_data)
                        chunks.append(data)
                        full_text += data.get("delta", "")
                        if data.get("done") is True:
                            final_received = True

            assert len(chunks) > 1, "Should receive multiple streamed chunks"
            assert final_received, "Should receive final chunk with done=True"
            assert len(full_text) > 0, "Accumulated text should not be empty"


@pytest.mark.asyncio
async def test_chat_stream_error_handling(monkeypatch):
    class FailingProvider(MockProvider):
        async def stream(self, messages, system_prompt=None, max_tokens=1024, **kwargs):
            raise LLMError("API connection reset by peer")
            yield "never"

    orch = orchestrator
    monkeypatch.setattr(orch, "_get_provider", lambda _: FailingProvider())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        payload = {
            "message": "Trigger failure test",
            "provider": "mock"
        }

        async with client.stream("POST", "/api/v1/chat/stream", json=payload) as response:
            assert response.status_code == 200

            error_found = False
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    raw_data = line[len("data:"):].strip()
                    if raw_data:
                        data = json.loads(raw_data)
                        if data.get("error") is not None:
                            error_found = True
                            assert "API connection reset" in data["error"]

            assert error_found, "Should have received an error event chunk"
