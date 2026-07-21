from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# User Management
class AdminCreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    role: str
    email: str = ""
    full_name: str = ""
    company_name: str = ""
    department: str = ""


class AdminUpdateUserRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class AdminUserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    full_name: str
    company_name: str
    department: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminUserListResponse(BaseModel):
    items: List[AdminUserResponse]
    total: int
    page: int
    page_size: int


# AI Configuration
class UpdateAIConfigRequest(BaseModel):
    config_value: str
    description: str = ""


class AIConfigResponse(BaseModel):
    id: str
    config_key: str
    config_value: str
    description: str
    updated_at: datetime

    class Config:
        from_attributes = True


# Prompt Templates
class CreatePromptRequest(BaseModel):
    name: str = Field(max_length=200)
    scenario: str = Field(default="general_chat")
    system_prompt: str = ""
    user_prompt_template: str = ""
    variables: Optional[List[dict]] = None


class UpdatePromptRequest(BaseModel):
    name: Optional[str] = None
    scenario: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    variables: Optional[List[dict]] = None
    is_active: Optional[bool] = None


class TestPromptRequest(BaseModel):
    variables: dict = {}


class PromptResponse(BaseModel):
    id: str
    name: str
    scenario: str
    system_prompt: str
    user_prompt_template: str
    variables: Optional[list] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Reports
class GenerateReportRequest(BaseModel):
    report_type: str = "weekly_summary"
    parameters: Optional[dict] = None


class ReportResponse(BaseModel):
    id: str
    report_type: str
    title: str
    parameters: Optional[dict] = None
    summary: str
    result_data: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True
