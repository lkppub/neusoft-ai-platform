import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, Integer, Float, Date, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class DashboardSnapshot(Base):
    __tablename__ = "dashboard_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    snapshot_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    total_inquiries: Mapped[int] = mapped_column(Integer, default=0)
    total_tickets: Mapped[int] = mapped_column(Integer, default=0)
    resolved_tickets: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_time_seconds: Mapped[float] = mapped_column(Float, default=0)
    satisfaction_score: Mapped[float] = mapped_column(Float, default=0)  # 0-5 scale
    category_distribution: Mapped[dict] = mapped_column(JSON, nullable=True)
    top_faq_queries: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalyticsReport(Base):
    __tablename__ = "analytics_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_type: Mapped[str] = mapped_column(String(50), default="weekly_summary")  # weekly_summary, satisfaction_analysis, etc.
    title: Mapped[str] = mapped_column(String(300), default="")
    parameters: Mapped[dict] = mapped_column(JSON, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    result_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    generated_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
