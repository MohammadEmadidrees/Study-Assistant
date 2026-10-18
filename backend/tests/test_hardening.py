import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.rate_limiter import rate_limiter
from app.services.orchestrator import orchestrator
from app.services.llm_provider import MockProvider, LLMError


@pytest.mark.asyncio
async def test_rate_limiting_exceeded():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        test_session_id = f"ratelimit-test-{uuid.uuid4()}"

        # Temporarily set lower limit for fast test execution
        original_limit = rate_limiter.limit
        rate_limiter.limit = 3

        try:
            responses = []
            for _ in range(5):
                res = await client.post("/api/v1/chat", json={
                    "session_id": test_session_id,
                    "message": "Spam test message",
                    "provider": "mock"
                })
                responses.append(res.status_code)

            # At least one request must have been rate limited
            assert 429 in responses, f"Expected 429 Too Many Requests in {responses}"

        finally:
            rate_limiter.limit = original_limit


@pytest.mark.asyncio
async def test_graceful_llm_error_degradation(monkeypatch):
    class TimeoutProvider(MockProvider):
        async def generate(self, messages, system_prompt=None, max_tokens=1024, **kwargs):
            raise LLMError("Anthropic API request timed out after 60s")

    orch = orchestrator
    monkeypatch.setattr(orch, "_get_provider", lambda _: TimeoutProvider())

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        res = await client.post("/api/v1/chat", json={
            "message": "Trigger timeout",
            "provider": "mock"
        })

        # Must degrade gracefully (502) rather than throwing an unhandled 500 crash
        assert res.status_code == 502
        data = res.json()
        assert "timed out" in data["detail"]
        assert "X-Request-ID" in res.headers


@pytest.mark.asyncio
async def test_structured_request_id_header():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        custom_req_id = "test-custom-req-id-12345"
        res = await client.get("/api/v1/health", headers={"X-Request-ID": custom_req_id})
        assert res.status_code == 200
        assert res.headers["X-Request-ID"] == custom_req_id
