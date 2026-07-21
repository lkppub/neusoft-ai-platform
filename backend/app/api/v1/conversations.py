import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.conversation import Conversation, Message, MessageRole
from app.schemas.conversation import (
    CreateConversationRequest, SendMessageRequest,
    ConversationResponse, MessageResponse, ConversationListResponse,
)
from app.services.cache.redis_cache import get_cache

router = APIRouter(prefix="/conversations", tags=["对话"])


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的对话列表"""
    # Count total
    count_q = select(func.count(Conversation.id)).where(
        Conversation.user_id == current_user.id,
        Conversation.is_archived == False,
    )
    total = (await db.execute(count_q)).scalar()

    # Fetch page
    q = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.is_archived == False)
        .order_by(desc(Conversation.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    items = result.scalars().all()

    return ConversationListResponse(
        items=[ConversationResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新对话"""
    conversation = Conversation(
        user_id=current_user.id,
        title=request.title,
        model_name=request.model_name,
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    await db.commit()  # commit immediately so subsequent fetchConversations() can see it
    return conversation


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取对话详情"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conversation


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """归档对话（软删除）"""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="对话不存在")
    conversation.is_archived = True
    return {"message": "对话已归档"}


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取对话消息历史"""
    # Verify ownership
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="对话不存在")

    q = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    messages = result.scalars().all()
    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送消息并获取AI流式回复 (SSE)"""
    # Verify ownership
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="对话不存在")

    # Save user message
    user_msg = Message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=request.content,
    )
    db.add(user_msg)

    # Update conversation title from first message if needed
    if conversation.message_count == 0:
        conversation.title = request.content[:50] + ("..." if len(request.content) > 50 else "")

    conversation.message_count += 1
    await db.flush()

    # Build history for AI (excluding the current message for LangGraph context)
    history_q = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .limit(20)
    )
    history_result = await db.execute(history_q)
    history = history_result.scalars().all()

    # Build conversation history (previous messages only, current is the inquiry)
    history_for_ai = [
        {"role": msg.role.value, "content": msg.content}
        for msg in history
    ]
    # Split: last message is the current inquiry, rest is context
    inquiry = request.content
    history_context = history_for_ai[:-1] if len(history_for_ai) > 1 else []

    cache = get_cache()

    async def event_stream():
        full_response = ""
        try:
            # Check cache for identical recent query (scoped to user)
            last_msg = {"role": "user", "content": inquiry}
            cached = await cache.get_ai_response([last_msg], user_id=current_user.id)
            if cached:
                full_response = cached
                yield f"data: {json.dumps({'type': 'token', 'content': cached}, ensure_ascii=False)}\n\n"
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=full_response,
                )
                db.add(assistant_msg)
                conversation.message_count += 1
                await db.flush()
                yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id}, ensure_ascii=False)}\n\n"
                return

            # ── AI Pipeline (tool-aware: Function Calling) ──
            from app.agents.graph import run_agent_pipeline_with_tools

            yield f"data: {json.dumps({'type': 'status', 'phase': 'analyzing'}, ensure_ascii=False)}\n\n"

            pipeline_result = await run_agent_pipeline_with_tools(
                inquiry=inquiry,
                user_id=current_user.id,
                history=history_context,
            )

            full_response = pipeline_result.get("final_reply") or ""

            # Log pipeline metadata for debugging/admin
            import logging
            logger = logging.getLogger(__name__)
            tool_calls = pipeline_result.get("tool_calls", [])
            tool_names = [tc.get("tool", "?") for tc in tool_calls] if tool_calls else []
            logger.info(
                "Agent pipeline complete: tools_called=%s, reply_len=%d",
                tool_names or ["none"],
                len(full_response),
            )

            # Stream the final reply in small chunks (simulated streaming)
            if full_response:
                chunk_size = 3
                for i in range(0, len(full_response), chunk_size):
                    chunk = full_response[i:i + chunk_size]
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.015)  # ~15ms per chunk

            # Cache the response (scoped to user)
            if full_response:
                await cache.set_ai_response([last_msg], full_response, user_id=current_user.id)

            # Save assistant message
            assistant_msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=full_response,
            )
            db.add(assistant_msg)
            conversation.message_count += 1
            await db.flush()

            yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
