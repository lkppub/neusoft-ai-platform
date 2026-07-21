from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.conversation import Conversation, Message
from app.models.ticket import CustomerServiceTicket, TicketStatus
from app.schemas.dashboard import DashboardOverviewResponse
from app.services.cache.redis_cache import get_cache


async def get_dashboard_stats(db: AsyncSession) -> DashboardOverviewResponse:
    """Aggregate dashboard overview statistics with Redis caching."""

    cache = get_cache()
    cached = await cache.get_stats("dashboard_overview")
    if cached:
        return DashboardOverviewResponse(**cached)

    # Total conversations (inquiries)
    total_convs = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0

    # Ticket stats
    total_tickets = (await db.execute(select(func.count(CustomerServiceTicket.id)))).scalar() or 0
    open_tickets = (await db.execute(
        select(func.count(CustomerServiceTicket.id))
        .where(CustomerServiceTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]))
    )).scalar() or 0
    resolved_tickets = (await db.execute(
        select(func.count(CustomerServiceTicket.id))
        .where(CustomerServiceTicket.status == TicketStatus.RESOLVED)
    )).scalar() or 0

    # Resolution rate
    resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0.0

    # Active users (users who sent messages today)
    from datetime import date
    today = date.today()
    active_users = (await db.execute(
        select(func.count(func.distinct(Conversation.user_id)))
        .where(func.date(Conversation.updated_at) == today)
    )).scalar() or 0

    # Calculate real avg response time and satisfaction from snapshots
    from app.models.analytics import DashboardSnapshot
    recent_snapshots = (await db.execute(
        select(DashboardSnapshot)
        .order_by(DashboardSnapshot.snapshot_date.desc())
        .limit(7)
    )).scalars().all()

    avg_response = 120.0
    satisfaction = 4.1
    if recent_snapshots:
        avg_response = sum(
            s.avg_response_time_seconds for s in recent_snapshots
        ) / len(recent_snapshots)
        satisfaction = sum(
            s.satisfaction_score for s in recent_snapshots
        ) / len(recent_snapshots)

    result = DashboardOverviewResponse(
        total_inquiries=total_convs,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        resolved_tickets=resolved_tickets,
        resolution_rate=round(resolution_rate, 1),
        avg_response_time_seconds=round(avg_response, 1),
        satisfaction_score=round(satisfaction, 1),
        active_users_today=active_users,
    )

    # Cache result
    await cache.set_stats("dashboard_overview", result.model_dump())
    return result
