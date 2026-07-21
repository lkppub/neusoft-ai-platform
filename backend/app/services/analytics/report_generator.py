import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.analytics import AnalyticsReport
from app.models.conversation import Conversation
from app.models.ticket import CustomerServiceTicket


async def generate_analytics_report(
    db: AsyncSession,
    report_type: str,
    parameters: dict | None,
    user_id: str,
) -> AnalyticsReport:
    """Generate an AI analytics report."""

    from app.services.ai.provider_factory import get_ai_provider
    ai = get_ai_provider()

    # Gather stats
    total_convs = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0
    total_tickets = (await db.execute(select(func.count(CustomerServiceTicket.id)))).scalar() or 0

    # Generate AI summary
    prompt = f"""请根据以下数据生成一份简短的商务分析报告摘要：

- 总对话次数：{total_convs}
- 总工单数：{total_tickets}
- 报告类型：{report_type}

请用中文输出3-5句话的分析摘要，包含关键发现和建议。"""

    summary = await ai.chat([{"role": "user", "content": prompt}])

    report = AnalyticsReport(
        id=str(uuid.uuid4()),
        report_type=report_type,
        title=f"{report_type}_分析报告",
        parameters=parameters or {},
        summary=summary,
        result_data={
            "total_conversations": total_convs,
            "total_tickets": total_tickets,
            "report_type": report_type,
        },
        generated_by=user_id,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report
