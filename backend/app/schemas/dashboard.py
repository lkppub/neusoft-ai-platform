from pydantic import BaseModel
from typing import Optional, List


class DashboardOverviewResponse(BaseModel):
    total_inquiries: int = 0
    total_tickets: int = 0
    open_tickets: int = 0
    resolved_tickets: int = 0
    resolution_rate: float = 0.0
    avg_response_time_seconds: float = 0.0
    satisfaction_score: float = 0.0
    active_users_today: int = 0


class CategoryDistribution(BaseModel):
    name: str
    value: int
    percentage: float


class SatisfactionTrend(BaseModel):
    date: str
    score: float


class VolumeTrend(BaseModel):
    date: str
    inquiries: int
    tickets: int


class InsightCard(BaseModel):
    id: str
    title: str
    content: str
    icon: str = "trend"
    change: Optional[float] = None
    change_type: str = "neutral"  # up, down, neutral


class HotTopic(BaseModel):
    keyword: str
    count: int
    trend: str = "stable"  # up, down, stable


class RealTimeMetric(BaseModel):
    active_conversations: int = 0
    messages_per_minute: float = 0.0
    pending_tickets: int = 0
    ai_response_rate: float = 0.0
