from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RAGQueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[dict]


class DocumentResponse(BaseModel):
    id: str
    uploaded_by: str
    title: str
    file_name: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    chunk_size: int
    chunk_overlap: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int


class CreateFAQRequest(BaseModel):
    category: str = Field(default="通用", max_length=100)
    question: str
    answer: str
    is_published: bool = True


class UpdateFAQRequest(BaseModel):
    category: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    is_published: Optional[bool] = None


class FAQResponse(BaseModel):
    id: str
    category: str
    question: str
    answer: str
    created_by: str
    is_published: bool
    view_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FAQListResponse(BaseModel):
    items: List[FAQResponse]
    total: int
    page: int
    page_size: int
