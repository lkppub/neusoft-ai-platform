from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CreateTicketRequest(BaseModel):
    subject: str = Field(max_length=300)
    description: str = ""
    priority: str = "medium"


class UpdateTicketRequest(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class AddTicketMessageRequest(BaseModel):
    content: str


class TicketResponse(BaseModel):
    id: str
    user_id: str
    creator_name: Optional[str] = None
    assigned_to: Optional[str] = None
    assignee_name: Optional[str] = None
    subject: str
    description: str
    problem_category: Optional[str] = None
    priority: str
    status: str
    ai_classification: Optional[dict] = None
    ai_suggested_reply: Optional[str] = None
    ai_reply_confidence: Optional[float] = None
    final_reply: Optional[str] = None
    resolved_at: Optional[datetime] = None
    satisfaction_rating: Optional[int] = None   # 1-5 星
    satisfaction_comment: Optional[str] = None  # 评价留言
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    items: List[TicketResponse]
    total: int
    page: int
    page_size: int


class TicketMessageResponse(BaseModel):
    id: str
    ticket_id: str
    sender_id: str
    message_type: str
    content: str
    attachments: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ClassifyResponse(BaseModel):
    category: str
    sentiment: str
    key_details: str


class SuggestReplyResponse(BaseModel):
    suggested_reply: str
    confidence: float


class RateTicketRequest(BaseModel):
    """客户评价工单"""
    rating: int = Field(ge=1, le=5, description="满意度评分 1-5")
    comment: Optional[str] = Field(default=None, max_length=500, description="评价留言")


class ResolveTicketRequest(BaseModel):
    final_reply: str
    satisfaction_rating: Optional[int] = Field(default=None, ge=1, le=5)
    satisfaction_comment: Optional[str] = Field(default=None, max_length=500)


# Reply Templates
class CreateTemplateRequest(BaseModel):
    category: str = Field(default="通用", max_length=100)
    title: str = Field(max_length=200)
    content: str
    variables: Optional[List[str]] = None


class UpdateTemplateRequest(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: str
    category: str
    title: str
    content: str
    variables: Optional[List[str]] = None
    created_by: str
    usage_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
