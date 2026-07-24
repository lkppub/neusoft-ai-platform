from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from app.core.database import async_session_factory, get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.models.ticket import CustomerServiceTicket, TicketMessage, TicketMessageType, TicketStatus
from app.schemas.ticket import (
    CreateTicketRequest, UpdateTicketRequest, AddTicketMessageRequest,
    TicketResponse, TicketListResponse, TicketMessageResponse,
    ClassifyResponse, SuggestReplyResponse, ResolveTicketRequest, RateTicketRequest,
)

router = APIRouter(prefix="/tickets", tags=["客服工单"])


async def _resolve_user_names(db: AsyncSession, user_ids: set) -> dict:
    """Batch-resolve user IDs to display names (full_name or username)."""
    if not user_ids:
        return {}
    result = await db.execute(
        select(User.id, User.full_name, User.username).where(User.id.in_(user_ids))
    )
    return {row[0]: row[1] or row[2] for row in result.all()}


def _enrich_ticket(item, user_map: dict) -> TicketResponse:
    """Convert ORM ticket to response with resolved user names."""
    d = TicketResponse.model_validate(item).model_dump()
    d["creator_name"] = user_map.get(item.user_id, "") or ""
    if item.assigned_to:
        d["assignee_name"] = user_map.get(item.assigned_to, "") or ""
    return TicketResponse(**d)


async def auto_classify_ticket(ticket_id: str) -> dict | None:
    """后台自动分类工单——创建工单时由 BackgroundTasks 触发，也可被 classify_ticket 端点调用。"""
    import logging
    _log = logging.getLogger(__name__)

    async with async_session_factory() as db:
        try:
            _log.info("[auto_classify] 开始分类工单 %s", ticket_id)

            result = await db.execute(
                select(CustomerServiceTicket).where(CustomerServiceTicket.id == ticket_id)
            )
            ticket = result.scalar_one_or_none()
            if not ticket:
                _log.warning("[auto_classify] 工单 %s 不存在", ticket_id)
                return None

            from app.services.ai.provider_factory import get_ai_provider
            from app.models.config import AIConfig, PromptTemplate
            ai = get_ai_provider()

            # ── 读取 AI 配置参数 ──
            configs_result = await db.execute(select(AIConfig))
            configs = {c.config_key: c.config_value for c in configs_result.scalars().all()}
            temperature = float(configs.get("temperature", "0.7"))
            max_tokens = int(configs.get("max_tokens", "4096"))

            # ── 查找匹配的提示词模板：客服场景 + 名称含"分类" ──
            template_result = await db.execute(
                select(PromptTemplate).where(
                    PromptTemplate.scenario == "customer_service",
                    PromptTemplate.name.contains("分类"),
                    PromptTemplate.is_active == True,
                ).order_by(PromptTemplate.updated_at.desc()).limit(1)
            )
            template = template_result.scalars().first()

            # ── 构建 prompt ──
            if template and template.system_prompt:
                system_prompt = template.system_prompt
                user_prompt = template.user_prompt_template or "{inquiry}"
                inquiry = f"主题：{ticket.subject}\n描述：{ticket.description}"
                for key, val in {"subject": ticket.subject, "description": ticket.description, "inquiry": inquiry}.items():
                    user_prompt = user_prompt.replace(f"{{{key}}}", str(val or ""))
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            else:
                prompt = f"""请对以下客户工单进行分类。你必须从下列分类中选择最匹配的一项：

【可用分类】
技术支持、账号问题、账单咨询、产品咨询、投诉建议、售后服务、功能需求、商务咨询、其他

【规则】
- category 必须严格从上述列表中选取，不得自创
- 如果无法明确归入前8类，使用"其他"

【工单信息】
主题：{ticket.subject}
描述：{ticket.description}

请返回JSON格式：{{"category": "上述分类之一", "sentiment": "positive/neutral/negative", "key_details": "关键信息摘要"}}"""
                messages = [{"role": "user", "content": prompt}]

            _log.info("[auto_classify] 调用 AI 分类...")
            response = await ai.chat(messages, temperature=temperature, max_tokens=max_tokens)
            _log.info("[auto_classify] AI 响应: %s", response[:200])

            import json
            try:
                classification = json.loads(response)
            except json.JSONDecodeError:
                classification = {"category": "未分类", "sentiment": "neutral", "key_details": response[:200]}

            # 只更新分类信息，不修改优先级（优先级由用户创建工单时决定）
            ticket.problem_category = classification.get("category", "未分类")
            ticket.ai_classification = classification
            await db.commit()

            _log.info("[auto_classify] 工单 %s 分类完成: category=%s, priority=%s",
                      ticket_id, ticket.problem_category, ticket.priority)
            return classification

        except Exception as e:
            _log.error("[auto_classify] 分类失败: %s", e, exc_info=True)
            await db.rollback()
            return None


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str = Query(default=None),
    priority: str = Query(default=None),
    category: str = Query(default=None),
    search: str = Query(default=None),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取工单列表（支持筛选、搜索、排序）"""
    base_q = select(CustomerServiceTicket)

    # Role-based filtering
    if current_user.role.value == "enterprise":
        base_q = base_q.where(CustomerServiceTicket.user_id == current_user.id)
    elif current_user.role.value == "customer_service":
        base_q = base_q.where(
            (CustomerServiceTicket.assigned_to == current_user.id) |
            (CustomerServiceTicket.assigned_to.is_(None))
        )

    if status:
        base_q = base_q.where(CustomerServiceTicket.status == status)
    if priority:
        base_q = base_q.where(CustomerServiceTicket.priority == priority)
    if category:
        base_q = base_q.where(CustomerServiceTicket.problem_category == category)
    if search:
        base_q = base_q.where(
            CustomerServiceTicket.subject.ilike(f"%{search}%") |
            CustomerServiceTicket.description.ilike(f"%{search}%")
        )

    # Dynamic sorting — map frontend sort keys to model columns
    sort_map = {
        "updated_at": CustomerServiceTicket.updated_at,
        "created_at": CustomerServiceTicket.created_at,
        "priority": CustomerServiceTicket.priority,
        "status": CustomerServiceTicket.status,
        "subject": CustomerServiceTicket.subject,
    }
    sort_col = sort_map.get(sort_by, CustomerServiceTicket.updated_at)
    if sort_order == "asc":
        base_q = base_q.order_by(sort_col.asc())
    else:
        base_q = base_q.order_by(sort_col.desc())

    # Use func.count() without column ref to avoid cartesian product
    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar()

    q = base_q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    # Resolve user names for display
    user_ids = {item.user_id for item in items}
    for item in items:
        if item.assigned_to:
            user_ids.add(item.assigned_to)
    user_map = await _resolve_user_names(db, user_ids)

    return TicketListResponse(
        items=[_enrich_ticket(item, user_map) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(
    request: CreateTicketRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建工单（自动触发 AI 分类）"""
    ticket = CustomerServiceTicket(
        user_id=current_user.id,
        subject=request.subject,
        description=request.description,
        priority=request.priority,
    )
    db.add(ticket)
    await db.flush()

    # Add initial message
    msg = TicketMessage(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        message_type=TicketMessageType.CUSTOMER,
        content=request.description or request.subject,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(ticket)

    # Fire-and-forget: 异步分类不阻塞创建响应
    import asyncio
    asyncio.create_task(auto_classify_ticket(ticket.id))

    return ticket


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取工单详情"""
    result = await db.execute(select(CustomerServiceTicket).where(CustomerServiceTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")
    user_ids = {ticket.user_id}
    if ticket.assigned_to:
        user_ids.add(ticket.assigned_to)
    user_map = await _resolve_user_names(db, user_ids)
    return _enrich_ticket(ticket, user_map)


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    request: UpdateTicketRequest,
    current_user: User = Depends(require_role("admin", "customer_service")),
    db: AsyncSession = Depends(get_db),
):
    """更新工单"""
    result = await db.execute(select(CustomerServiceTicket).where(CustomerServiceTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    if request.subject is not None:
        ticket.subject = request.subject
    if request.description is not None:
        ticket.description = request.description
    if request.assigned_to is not None:
        ticket.assigned_to = request.assigned_to
    if request.priority is not None:
        ticket.priority = request.priority
    if request.status is not None:
        ticket.status = request.status

    await db.flush()
    await db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/messages", response_model=TicketMessageResponse)
async def add_ticket_message(
    ticket_id: str,
    request: AddTicketMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加工单消息"""
    result = await db.execute(select(CustomerServiceTicket).where(CustomerServiceTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    msg_type = TicketMessageType.AGENT if current_user.role.value in ["admin", "customer_service"] else TicketMessageType.CUSTOMER
    msg = TicketMessage(
        ticket_id=ticket_id,
        sender_id=current_user.id,
        message_type=msg_type,
        content=request.content,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


@router.post("/{ticket_id}/classify", response_model=ClassifyResponse)
async def classify_ticket(
    ticket_id: str,
    current_user: User = Depends(require_role("admin", "customer_service")),
    db: AsyncSession = Depends(get_db),
):
    """AI分类工单（手动触发，复用 auto_classify_ticket）"""
    # 先确认工单存在（在当前 session 中校验权限）
    result = await db.execute(select(CustomerServiceTicket).where(CustomerServiceTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    classification = await auto_classify_ticket(ticket_id)

    if classification is None:
        raise HTTPException(status_code=500, detail="AI分类失败，请稍后重试")

    return ClassifyResponse(
        category=classification.get("category", "未分类"),
        sentiment=classification.get("sentiment", "neutral"),
        key_details=classification.get("key_details", ""),
    )


# ── 分类关键词 → 模板名称关键词映射 ──
CATEGORY_TEMPLATE_KEYWORDS = {
    "技术支持": "技术支持",
    "账号问题": "账号问题",
    "账单咨询": "账单咨询",
    "产品咨询": "产品咨询",
    "投诉建议": "投诉建议",
    "售后服务": "售后服务",
}


@router.post("/{ticket_id}/suggest-reply", response_model=SuggestReplyResponse)
async def suggest_reply(
    ticket_id: str,
    current_user: User = Depends(require_role("admin", "customer_service")),
    db: AsyncSession = Depends(get_db),
):
    """AI建议回复——按工单分类匹配差异化回复模板"""
    result = await db.execute(select(CustomerServiceTicket).where(CustomerServiceTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    from app.services.ai.provider_factory import get_ai_provider
    from app.models.config import AIConfig, PromptTemplate
    from sqlalchemy import or_
    ai = get_ai_provider()

    # ── 读取 AI 配置参数 ──
    configs_result = await db.execute(select(AIConfig))
    configs = {c.config_key: c.config_value for c in configs_result.scalars().all()}
    temperature = float(configs.get("temperature", "0.7"))
    max_tokens = int(configs.get("max_tokens", "4096"))

    # ── Phase 1.2: 按工单分类匹配专属回复模板 ──
    category = ticket.problem_category or ""
    template = None

    # Step 1: 根据分类关键词精确匹配专属模板
    template_keyword = None
    for cat_key, tpl_key in CATEGORY_TEMPLATE_KEYWORDS.items():
        if cat_key in category:
            template_keyword = tpl_key
            break

    if template_keyword:
        template_result = await db.execute(
            select(PromptTemplate).where(
                PromptTemplate.is_active == True,
                PromptTemplate.scenario == "customer_service",
                PromptTemplate.name.contains(template_keyword),
            ).order_by(PromptTemplate.updated_at.desc()).limit(1)
        )
        template = template_result.scalars().first()

    # Step 2: 回退——匹配通用客服模板
    if not template:
        template_result = await db.execute(
            select(PromptTemplate).where(
                PromptTemplate.is_active == True,
                or_(
                    PromptTemplate.scenario == "customer_service",
                    PromptTemplate.scenario == "general_chat",
                ),
            ).order_by(PromptTemplate.updated_at.desc())
        )
        candidates = template_result.scalars().all()
        for t in candidates:
            if "客服" in (t.name or "") or "回复" in (t.name or ""):
                # 排除分类专用模板，只取通用客服模板
                if "通用" in (t.name or "") or t.name == "通用客服":
                    template = t
                    break
        if not template and candidates:
            template = candidates[0]

    # ── 构建 prompt ──
    if template and template.system_prompt:
        system_prompt = template.system_prompt
        user_prompt = template.user_prompt_template or "{question}"
        # 变量替换
        for key, val in {
            "subject": ticket.subject,
            "description": ticket.description,
            "category": category or "未分类",
            "question": f"客户问题：{ticket.subject}\n问题详情：{ticket.description}\n问题分类：{category or '未分类'}",
            "inquiry": f"客户问题：{ticket.subject}\n问题详情：{ticket.description}",
        }.items():
            user_prompt = user_prompt.replace(f"{{{key}}}", str(val or ""))
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    else:
        # 回退到硬编码 prompt（向后兼容）
        prompt = f"""作为专业客服，请为以下客户问题撰写礼貌、专业的回复：
客户问题：{ticket.subject}
问题详情：{ticket.description}
问题分类：{category or '未分类'}

请直接给出回复内容，不要包含其他说明。"""
        messages = [{"role": "user", "content": prompt}]

    reply = await ai.chat(messages, temperature=temperature, max_tokens=max_tokens)

    ticket.ai_suggested_reply = reply
    ticket.ai_reply_confidence = 0.85
    await db.flush()

    return SuggestReplyResponse(suggested_reply=reply, confidence=0.85)


@router.post("/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: str,
    request: ResolveTicketRequest,
    current_user: User = Depends(require_role("admin", "customer_service")),
    db: AsyncSession = Depends(get_db),
):
    """解决并关闭工单"""
    result = await db.execute(select(CustomerServiceTicket).where(CustomerServiceTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    ticket.status = TicketStatus.RESOLVED
    ticket.final_reply = request.final_reply
    ticket.resolved_at = datetime.now(timezone.utc)

    # 客服解决时可附带评分
    if request.satisfaction_rating is not None:
        ticket.satisfaction_rating = request.satisfaction_rating
        ticket.satisfaction_comment = request.satisfaction_comment

    # Add resolution message
    msg = TicketMessage(
        ticket_id=ticket_id,
        sender_id=current_user.id,
        message_type=TicketMessageType.SYSTEM,
        content=f"工单已解决: {request.final_reply}",
    )
    db.add(msg)
    await db.flush()

    return {"message": "工单已解决", "ticket_id": ticket_id}


@router.post("/{ticket_id}/rate")
async def rate_ticket(
    ticket_id: str,
    request: RateTicketRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """客户评价已解决的工单（1-5 星）"""
    result = await db.execute(select(CustomerServiceTicket).where(CustomerServiceTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    if ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能评价自己的工单")

    if ticket.status != TicketStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="只能评价已解决的工单")

    ticket.satisfaction_rating = request.rating
    ticket.satisfaction_comment = request.comment
    await db.flush()

    return {"message": "评价成功", "rating": request.rating}


@router.get("/{ticket_id}/messages")
async def get_ticket_messages(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取工单消息列表"""
    q = (
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at)
    )
    result = await db.execute(q)
    messages = result.scalars().all()
    return [TicketMessageResponse.model_validate(m) for m in messages]
