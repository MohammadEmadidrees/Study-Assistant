from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    tokens_used: int = 0
    created_at: datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageRead] = []


class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default="New Conversation")
