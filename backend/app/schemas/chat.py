from typing import Optional, Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, description="Message text content")


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(
        default=None,
        description="Session / Conversation ID. If not provided, a new session will be created."
    )
    message: str = Field(..., min_length=1, description="User's query")
    stream: bool = Field(default=False, description="Whether to stream the response")
    provider: Optional[str] = Field(default=None, description="LLM provider override (e.g. claude)")


class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessage
    tokens_used: int = 0
    latency_ms: float = 0.0


class StreamChunk(BaseModel):
    session_id: str
    delta: str = ""
    done: bool = False
    error: Optional[str] = None
    tokens_used: Optional[int] = None
