from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any, Tuple, Optional
import asyncio
import anthropic
from app.core.config import settings
from app.core.logging import logger


class LLMError(Exception):
    """Custom exception for LLM provider errors."""
    pass


class BaseLLMProvider(ABC):
    """
    Abstract Base Class for LLM providers.
    All providers (Claude, OpenAI, Gemini, etc.) must implement generate and stream.
    Route handlers and services interact ONLY with this interface.
    """

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        **kwargs: Any
    ) -> Tuple[str, int]:
        """
        Non-streaming generation.
        Returns: (response_text, total_tokens_used)
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """
        Streaming generation.
        Yields text deltas token by token.
        """
        pass


class ClaudeProvider(BaseLLMProvider):
    """
    Anthropic Claude implementation of BaseLLMProvider.
    Uses AsyncAnthropic client.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS

        self.is_mock = (
            not self.api_key
            or self.api_key.startswith("mock")
            or self.api_key == "mock-or-valid-key"
        )

        if not self.is_mock:
            self.client = anthropic.AsyncAnthropic(
                api_key=self.api_key,
                timeout=self.timeout
            )
        else:
            self.client = None

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        **kwargs: Any
    ) -> Tuple[str, int]:
        if self.is_mock:
            last_msg = messages[-1]["content"] if messages else "Hello"
            await asyncio.sleep(0.05)
            mock_reply = f"[Claude Response]: I received your message: '{last_msg}'. How can I assist your study today?"
            # Estimate roughly 1 token per 4 chars
            tokens_used = (len(last_msg) + len(mock_reply)) // 4
            return mock_reply, max(tokens_used, 15)

        try:
            # Format messages for Anthropic (roles: user or assistant)
            formatted_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in messages
                if m["role"] in ["user", "assistant"]
            ]

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt or "You are a helpful and knowledgeable study assistant.",
                messages=formatted_messages,
                **kwargs
            )
            reply_text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            tokens = (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0
            return reply_text, tokens

        except anthropic.APITimeoutError as exc:
            logger.error(f"Claude API timed out after {self.timeout}s: {exc}")
            raise LLMError("The AI service timed out while processing your request. Please try again.") from exc
        except anthropic.RateLimitError as exc:
            logger.error(f"Claude rate limit hit: {exc}")
            raise LLMError("The AI service is currently busy. Please wait a moment and retry.") from exc
        except anthropic.APIError as exc:
            logger.error(f"Claude API error: {exc}")
            raise LLMError(f"AI service error: {exc.message}") from exc
        except Exception as exc:
            logger.error(f"Unexpected error in ClaudeProvider: {exc}")
            raise LLMError("An unexpected error occurred while communicating with the AI service.") from exc

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        if self.is_mock:
            last_msg = messages[-1]["content"] if messages else "Hello"
            sample_words = [
                "[Claude Stream]: ", "I ", "received ", "your ", "query: ",
                f"'{last_msg}'. ", "Here ", "is ", "a ", "structured ", "response ",
                "to ", "help ", "you ", "study ", "effectively!"
            ]
            for word in sample_words:
                await asyncio.sleep(0.04)
                yield word
            return

        try:
            formatted_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in messages
                if m["role"] in ["user", "assistant"]
            ]

            async with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt or "You are a helpful and knowledgeable study assistant.",
                messages=formatted_messages,
                **kwargs
            ) as stream_resp:
                async for text in stream_resp.text_stream:
                    yield text

        except anthropic.APITimeoutError as exc:
            logger.error(f"Claude stream timeout: {exc}")
            raise LLMError("Stream timed out from the AI provider.") from exc
        except anthropic.RateLimitError as exc:
            logger.error(f"Claude stream rate limit: {exc}")
            raise LLMError("Rate limit reached. Please pause a moment before asking again.") from exc
        except Exception as exc:
            logger.error(f"Claude stream error: {exc}")
            raise LLMError("Streaming error encountered from the AI provider.") from exc


class MockProvider(BaseLLMProvider):
    """Provider specifically configured for deterministic unit and integration tests."""

    def __init__(self, canned_response: str = "This is a deterministic test response."):
        self.canned_response = canned_response

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        **kwargs: Any
    ) -> Tuple[str, int]:
        return self.canned_response, 25

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        chunks = self.canned_response.split(" ")
        for i, chunk in enumerate(chunks):
            await asyncio.sleep(0.01)
            prefix = "" if i == 0 else " "
            yield prefix + chunk


# Provider Registry / Factory
_PROVIDERS: Dict[str, type] = {
    "claude": ClaudeProvider,
    "mock": MockProvider,
}


def get_llm_provider(provider_name: Optional[str] = None) -> BaseLLMProvider:
    """
    Factory to retrieve an LLM provider instance.
    Swapping provider requires adding the class here or changing DEFAULT_LLM_PROVIDER.
    """
    selected = (provider_name or settings.DEFAULT_LLM_PROVIDER).lower()
    provider_cls = _PROVIDERS.get(selected)
    if not provider_cls:
        logger.warning(f"Unknown provider '{selected}', defaulting to 'claude'.")
        provider_cls = ClaudeProvider
    return provider_cls()
