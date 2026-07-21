from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CreateConversationRequest(BaseModel):
    title: str = Field(default="新对话", max_length=200)
    model_name: str = Field(default="deepseek-chat")


class SendMessageRequest(BaseModel):
    content: str


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    model_name: str
    message_count: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    token_count: Optional[int] = None
    tool_calls: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    items: List[ConversationResponse]
    total: int
    page: int
    page_size: int
