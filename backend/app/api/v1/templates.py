from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.models.ticket import ReplyTemplate, CustomerServiceTicket
from app.schemas.ticket import CreateTemplateRequest, UpdateTemplateRequest, TemplateResponse

router = APIRouter(prefix="/templates", tags=["回复模板"])


@router.get("")
async def list_templates(
    category: str = Query(default=None),
    include_inactive: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取回复模板列表。include_inactive=True 时同时返回已禁用的模板。"""
    base_q = select(ReplyTemplate)
    if not include_inactive:
        base_q = base_q.where(ReplyTemplate.is_active == True)
    if category:
        base_q = base_q.where(ReplyTemplate.category == category)

    q = base_q.order_by(desc(ReplyTemplate.usage_count))
    result = await db.execute(q)
    items = result.scalars().all()
    return [TemplateResponse.model_validate(item) for item in items]


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(
    request: CreateTemplateRequest,
    current_user: User = Depends(require_role("admin", "customer_service")),
    db: AsyncSession = Depends(get_db),
):
    """创建回复模板"""
    template = ReplyTemplate(
        category=request.category,
        title=request.title,
        content=request.content,
        variables=request.variables,
        created_by=current_user.id,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    current_user: User = Depends(require_role("admin", "customer_service")),
    db: AsyncSession = Depends(get_db),
):
    """更新回复模板"""
    result = await db.execute(select(ReplyTemplate).where(ReplyTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    if request.category is not None:
        template.category = request.category
    if request.title is not None:
        template.title = request.title
    if request.content is not None:
        template.content = request.content
    if request.variables is not None:
        template.variables = request.variables
    if request.is_active is not None:
        template.is_active = request.is_active

    await db.flush()
    await db.refresh(template)
    return template


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(require_role("admin", "customer_service")),
    db: AsyncSession = Depends(get_db),
):
    """删除回复模板"""
    result = await db.execute(select(ReplyTemplate).where(ReplyTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    await db.delete(template)
    return {"message": "模板已删除"}


@router.post("/{template_id}/use")
async def use_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """使用模板（递增 usage_count）"""
    result = await db.execute(select(ReplyTemplate).where(ReplyTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    template.usage_count += 1
    await db.flush()
    return {"message": "ok"}


@router.get("/{template_id}/render")
async def render_template(
    template_id: str,
    ticket_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """渲染模板变量（根据工单上下文替换占位符）"""
    # 查模板
    result = await db.execute(select(ReplyTemplate).where(ReplyTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 查工单
    result = await db.execute(select(CustomerServiceTicket).where(CustomerServiceTicket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    # 查客户信息
    result = await db.execute(select(User).where(User.id == ticket.user_id))
    customer = result.scalar_one_or_none()
    customer_name = customer.full_name if customer else "客户"

    # 替换变量
    content = template.content
    replacements = {
        "customer_name": customer_name,
        "issue_summary": ticket.subject,
    }
    # 尝试从 AI 分类结果中获取 possible_cause
    possible_cause = "未知"
    if ticket.ai_classification and isinstance(ticket.ai_classification, dict):
        possible_cause = ticket.ai_classification.get("key_details", "未知")
    replacements["possible_cause"] = possible_cause

    for key, val in replacements.items():
        content = content.replace(f"{{{key}}}", val)

    return {"content": content}
