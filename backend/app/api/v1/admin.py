from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.database import get_db
from app.core.security import hash_password
from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.models.config import AIConfig, PromptTemplate
from app.models.conversation import Conversation, Message
from app.models.analytics import AnalyticsReport
from app.schemas.admin import (
    AdminCreateUserRequest, AdminUpdateUserRequest, AdminUserResponse, AdminUserListResponse,
    UpdateAIConfigRequest, AIConfigResponse,
    CreatePromptRequest, UpdatePromptRequest, TestPromptRequest, PromptResponse,
    GenerateReportRequest, ReportResponse,
)

router = APIRouter(prefix="/admin", tags=["管理后台"])


# ===== User Management =====
@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: str = Query(default=None),
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表（管理员）"""
    base_q = select(User)
    if role:
        base_q = base_q.where(User.role == role)

    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar()

    q = base_q.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()

    return AdminUserListResponse(
        items=[AdminUserResponse.model_validate(item) for item in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("/users", response_model=AdminUserResponse, status_code=201)
async def create_user(
    request: AdminCreateUserRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """创建用户（管理员）"""
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        role=request.role,
        full_name=request.full_name,
        company_name=request.company_name,
        department=request.department,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: str,
    request: AdminUpdateUserRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """更新用户（管理员）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    for field in ["username", "email", "role", "full_name", "company_name", "department"]:
        val = getattr(request, field, None)
        if val is not None:
            setattr(user, field, val)
    if request.is_active is not None:
        user.is_active = request.is_active

    await db.flush()
    await db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """删除用户（管理员）- 硬删除"""
    # Prevent deleting self
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await db.delete(user)
    await db.flush()
    return {"message": "用户已删除"}


@router.put("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """重置用户密码"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.hashed_password = hash_password("123456")
    await db.flush()
    return {"message": "密码已重置为默认密码"}


# ===== AI Configuration =====
@router.get("/ai/configs")
async def list_ai_configs(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """获取AI配置列表"""
    result = await db.execute(select(AIConfig))
    configs = result.scalars().all()
    return [AIConfigResponse.model_validate(c) for c in configs]


@router.put("/ai/configs/{config_key}", response_model=AIConfigResponse)
async def update_ai_config(
    config_key: str,
    request: UpdateAIConfigRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """更新AI配置"""
    result = await db.execute(select(AIConfig).where(AIConfig.config_key == config_key))
    config = result.scalar_one_or_none()
    if not config:
        config = AIConfig(config_key=config_key)
        db.add(config)
    config.config_value = request.config_value
    config.description = request.description
    config.updated_by = current_user.id
    await db.flush()
    await db.refresh(config)
    return config


# ===== Prompt Templates =====
@router.get("/ai/prompts")
async def list_prompts(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """获取提示词模板列表"""
    result = await db.execute(select(PromptTemplate).order_by(desc(PromptTemplate.updated_at)))
    items = result.scalars().all()
    return [PromptResponse.model_validate(item) for item in items]


@router.post("/ai/prompts", response_model=PromptResponse, status_code=201)
async def create_prompt(
    request: CreatePromptRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """创建提示词模板"""
    prompt = PromptTemplate(
        name=request.name,
        scenario=request.scenario,
        system_prompt=request.system_prompt,
        user_prompt_template=request.user_prompt_template,
        variables=request.variables,
        created_by=current_user.id,
    )
    db.add(prompt)
    await db.flush()
    await db.refresh(prompt)
    return prompt


@router.put("/ai/prompts/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    request: UpdatePromptRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """更新提示词模板"""
    result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="模板不存在")

    for field in ["name", "scenario", "system_prompt", "user_prompt_template", "variables"]:
        val = getattr(request, field, None)
        if val is not None:
            setattr(prompt, field, val)
    if request.is_active is not None:
        prompt.is_active = request.is_active

    await db.flush()
    await db.refresh(prompt)
    return prompt


@router.delete("/ai/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """删除提示词模板"""
    result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="模板不存在")
    await db.delete(prompt)
    return {"message": "模板已删除"}


@router.post("/ai/prompts/{prompt_id}/test")
async def test_prompt(
    prompt_id: str,
    request: TestPromptRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """测试提示词模板"""
    result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="模板不存在")

    from app.services.ai.provider_factory import get_ai_provider
    ai = get_ai_provider()

    user_prompt = prompt.user_prompt_template
    for key, val in request.variables.items():
        user_prompt = user_prompt.replace(f"{{{key}}}", str(val))

    messages = [
        {"role": "system", "content": prompt.system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = await ai.chat(messages)
    return {"prompt_name": prompt.name, "response": response}


# ===== Conversation Records =====
@router.get("/conversations")
async def list_all_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """查看所有对话记录（管理员）"""
    count_q = select(func.count(Conversation.id))
    total = (await db.execute(count_q)).scalar()

    q = select(Conversation).order_by(desc(Conversation.updated_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    items = result.scalars().all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/conversations/stats")
async def get_conversation_stats(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """对话统计"""
    total_conversations = (await db.execute(select(func.count(Conversation.id)))).scalar()
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar()
    return {"total_conversations": total_conversations, "total_messages": total_messages}


# ===== Reports =====
@router.get("/reports")
async def list_reports(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """获取报告列表"""
    result = await db.execute(select(AnalyticsReport).order_by(desc(AnalyticsReport.created_at)).limit(20))
    items = result.scalars().all()
    return [ReportResponse.model_validate(item) for item in items]


@router.post("/reports/generate", response_model=ReportResponse, status_code=201)
async def generate_report(
    request: GenerateReportRequest,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """生成分析报告"""
    from app.services.analytics.report_generator import generate_analytics_report
    report = await generate_analytics_report(
        db=db,
        report_type=request.report_type,
        parameters=request.parameters,
        user_id=current_user.id,
    )
    return report


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """获取报告详情"""
    result = await db.execute(select(AnalyticsReport).where(AnalyticsReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return report


@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: str,
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """删除报告"""
    result = await db.execute(select(AnalyticsReport).where(AnalyticsReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    await db.delete(report)
    return {"message": "报告已删除"}
