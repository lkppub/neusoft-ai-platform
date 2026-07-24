from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, timedelta

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.ticket import CustomerServiceTicket
from app.schemas.dashboard import (
    DashboardOverviewResponse, RealTimeMetric,
)
from app.services.analytics.stats_service import get_dashboard_stats

router = APIRouter(prefix="/dashboard", tags=["数据大屏"])


@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """仪表盘概览 — 从数据库实时统计"""
    return await get_dashboard_stats(db)


@router.get("/categories")
async def get_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """问题分类分布 — 从工单表实时统计"""
    result = await db.execute(
        select(
            CustomerServiceTicket.problem_category,
            func.count(CustomerServiceTicket.id),
        )
        .where(CustomerServiceTicket.problem_category.isnot(None))
        .where(CustomerServiceTicket.problem_category != "")
        .group_by(CustomerServiceTicket.problem_category)
        .order_by(func.count(CustomerServiceTicket.id).desc())
    )
    rows = result.all()
    total = sum(r[1] for r in rows)

    if not rows or total == 0:
        return []

    return [
        {
            "name": r[0] or "未分类",
            "value": r[1],
            "percentage": round(r[1] / total * 100, 1),
        }
        for r in rows
    ]


@router.get("/satisfaction")
async def get_satisfaction_trend(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """满意度趋势 — 从真实工单评分统计"""
    start_date = date.today() - timedelta(days=days)

    # 只查有评价的已解决工单
    result = await db.execute(
        select(
            func.date(CustomerServiceTicket.resolved_at),
            func.avg(CustomerServiceTicket.satisfaction_rating),
            func.count(CustomerServiceTicket.satisfaction_rating),
        )
        .where(CustomerServiceTicket.satisfaction_rating.isnot(None))
        .where(func.date(CustomerServiceTicket.resolved_at) >= start_date)
        .group_by(func.date(CustomerServiceTicket.resolved_at))
        .order_by(func.date(CustomerServiceTicket.resolved_at))
    )
    daily_ratings = {
        str(r[0]): {"avg": round(float(r[1]), 1), "count": r[2]}
        for r in result.all()
    }

    trend = []
    for i in range(days, 0, -1):
        d = str(date.today() - timedelta(days=i))
        item = daily_ratings.get(d)
        trend.append({
            "date": d,
            "score": item["avg"] if item else None,
            "count": item["count"] if item else 0,
        })

    return trend


@router.get("/volume")
async def get_volume_trend(
    days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """咨询量趋势 — 从对话和工单表实时统计"""
    start_date = date.today() - timedelta(days=days)

    # Conversations per day
    conv_result = await db.execute(
        select(func.date(Conversation.created_at), func.count(Conversation.id))
        .where(func.date(Conversation.created_at) >= start_date)
        .group_by(func.date(Conversation.created_at))
    )
    conv_counts = {str(r[0]): r[1] for r in conv_result.all()}

    # Tickets per day
    ticket_result = await db.execute(
        select(func.date(CustomerServiceTicket.created_at), func.count(CustomerServiceTicket.id))
        .where(func.date(CustomerServiceTicket.created_at) >= start_date)
        .group_by(func.date(CustomerServiceTicket.created_at))
    )
    ticket_counts = {str(r[0]): r[1] for r in ticket_result.all()}

    trend = []
    for i in range(days, 0, -1):
        d = str(date.today() - timedelta(days=i))
        trend.append({
            "date": d,
            "inquiries": conv_counts.get(d, 0),
            "tickets": ticket_counts.get(d, 0),
        })

    return trend


@router.get("/insights")
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 智能分析洞察 — 基于真实统计数据生成"""
    # Gather real stats
    total_tickets = (await db.execute(
        select(func.count(CustomerServiceTicket.id))
    )).scalar() or 0

    open_tickets = (await db.execute(
        select(func.count(CustomerServiceTicket.id))
        .where(CustomerServiceTicket.status.in_(["open", "in_progress"]))
    )).scalar() or 0

    resolved_tickets = (await db.execute(
        select(func.count(CustomerServiceTicket.id))
        .where(CustomerServiceTicket.status == "resolved")
    )).scalar() or 0

    resolution_rate = round(resolved_tickets / total_tickets * 100, 1) if total_tickets > 0 else 0

    total_convs = (await db.execute(
        select(func.count(Conversation.id))
    )).scalar() or 0

    # Top category
    top_cat_result = await db.execute(
        select(
            CustomerServiceTicket.problem_category,
            func.count(CustomerServiceTicket.id),
        )
        .where(CustomerServiceTicket.problem_category.isnot(None))
        .where(CustomerServiceTicket.problem_category != "")
        .group_by(CustomerServiceTicket.problem_category)
        .order_by(func.count(CustomerServiceTicket.id).desc())
        .limit(1)
    )
    top_cat = top_cat_result.first()
    top_category_name = top_cat[0] if top_cat else "暂无"

    # Try AI generation, fall back to template
    try:
        from app.services.ai.provider_factory import get_ai_provider
        ai = get_ai_provider()

        prompt = f"""基于以下真实平台数据，生成4条简短的分析洞察（每条不超过40字）：

- 总工单数：{total_tickets}
- 待处理工单：{open_tickets}
- 解决率：{resolution_rate}%
- 总咨询量：{total_convs}
- 问题最多类别：{top_category_name}

以JSON列表格式返回：[{{"title": "标题", "content": "内容"}}]"""
        response = await ai.chat([{"role": "user", "content": prompt}])
        import json
        try:
            insights = json.loads(response)
            return [{"id": str(i), **item} for i, item in enumerate(insights)]
        except json.JSONDecodeError:
            pass
    except Exception:
        pass

    # Fallback with real numbers
    return [
        {
            "id": "1",
            "title": f"{open_tickets} 个待处理工单",
            "content": f"当前有 {open_tickets} 个工单等待处理，解决率 {resolution_rate}%",
        },
        {
            "id": "2",
            "title": f"问题热点：{top_category_name}",
            "content": f"'{top_category_name}' 类问题占比最高，建议重点关注",
        },
        {
            "id": "3",
            "title": f"累计 {total_convs} 次 AI 对话",
            "content": f"AI 对话助手已服务 {total_convs} 次咨询",
        },
        {
            "id": "4",
            "title": f"工单总量 {total_tickets}",
            "content": f"系统累计处理 {total_tickets} 个工单，已解决 {resolved_tickets} 个",
        },
    ]


@router.get("/hot-topics")
async def get_hot_topics(
    limit: int = Query(default=10, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """热门话题 — 从工单主题词统计"""
    result = await db.execute(
        select(
            CustomerServiceTicket.problem_category,
            func.count(CustomerServiceTicket.id),
        )
        .where(CustomerServiceTicket.problem_category.isnot(None))
        .where(CustomerServiceTicket.problem_category != "")
        .group_by(CustomerServiceTicket.problem_category)
        .order_by(func.count(CustomerServiceTicket.id).desc())
        .limit(limit)
    )
    rows = result.all()

    if not rows:
        return []

    max_count = rows[0][1] if rows else 1
    return [
        {
            "keyword": r[0],
            "count": r[1],
            "trend": "up" if r[1] >= max_count * 0.5 else "stable",
        }
        for r in rows
    ]


@router.get("/realtime", response_model=RealTimeMetric)
async def get_realtime(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """实时指标 — 从数据库实时统计"""
    # Active conversations (distinct users who sent messages)
    active_users = (await db.execute(
        select(func.count(func.distinct(Conversation.user_id)))
    )).scalar() or 0

    # Pending tickets
    pending = (await db.execute(
        select(func.count(CustomerServiceTicket.id))
        .where(CustomerServiceTicket.status.in_(["open", "in_progress"]))
    )).scalar() or 0

    # AI response rate (tickets with AI classification / total)
    total_tickets = (await db.execute(
        select(func.count(CustomerServiceTicket.id))
    )).scalar() or 1

    ai_classified = (await db.execute(
        select(func.count(CustomerServiceTicket.id))
        .where(CustomerServiceTicket.ai_classification.isnot(None))
    )).scalar() or 0

    ai_rate = round(ai_classified / total_tickets * 100, 1) if total_tickets > 0 else 0

    return RealTimeMetric(
        active_conversations=active_users,
        messages_per_minute=0,
        pending_tickets=pending,
        ai_response_rate=ai_rate,
    )
