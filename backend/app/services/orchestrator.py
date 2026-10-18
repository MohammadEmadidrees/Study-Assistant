import time
from typing import List, Dict, Tuple, Optional, AsyncGenerator
from app.services.llm_provider import BaseLLMProvider, get_llm_provider, LLMError
from app.core.logging import logger


DEFAULT_SYSTEM_PROMPT = """You are an intelligent, empathetic, and effective Study Assistant AI.
You excel at explaining complex academic concepts simply, formatting math and code clearly,
and guiding learners step-by-step with structured explanations."""


class ChatOrchestrator:
    """
    Coordinates prompt assembly, context assembly, and dispatch to LLM providers.
    Separates route handling from business and AI logic.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self._provider = provider

    def _get_provider(self, provider_name: Optional[str] = None) -> BaseLLMProvider:
        if self._provider:
            return self._provider
        return get_llm_provider(provider_name)

    def assemble_messages(
        self,
        history: List[Dict[str, str]],
        new_user_message: str
    ) -> List[Dict[str, str]]:
        """
        Assembles previous conversation context with the incoming user message.
        Ensures alternating turn integrity and valid role assignments.
        """
        assembled = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "").strip()
            if content and role in ["user", "assistant"]:
                assembled.append({"role": role, "content": content})

        assembled.append({"role": "user", "content": new_user_message.strip()})
        return assembled

    async def generate_response(
        self,
        history: List[Dict[str, str]],
        user_message: str,
        provider_name: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Tuple[str, int, float]:
        """
        Executes single-turn prompt execution.
        Returns: (assistant_response, tokens_used, latency_ms)
        """
        provider = self._get_provider(provider_name)
        messages = self.assemble_messages(history, user_message)
        prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

        start_time = time.perf_counter()
        try:
            content, tokens = await provider.generate(
                messages=messages,
                system_prompt=prompt
            )
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            logger.info(
                "Completed LLM single-turn generation",
                extra={
                    "total_tokens": tokens,
                    "latency_ms": latency_ms,
                    "provider": provider.__class__.__name__
                }
            )
            return content, tokens, latency_ms

        except LLMError:
            raise
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Orchestration failure: {exc}", extra={"latency_ms": latency_ms})
            raise LLMError("Failed to generate response from the AI provider.") from exc

    async def stream_response(
        self,
        history: List[Dict[str, str]],
        user_message: str,
        provider_name: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streams response tokens asynchronously from the LLM adapter.
        """
        provider = self._get_provider(provider_name)
        messages = self.assemble_messages(history, user_message)
        prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

        try:
            async for chunk in provider.stream(
                messages=messages,
                system_prompt=prompt
            ):
                yield chunk
        except LLMError:
            raise
        except Exception as exc:
            logger.error(f"Streaming orchestration failure: {exc}")
            raise LLMError("Streaming interrupted unexpectedly.") from exc


orchestrator = ChatOrchestrator()
