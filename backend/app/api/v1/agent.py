import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/agent", tags=["智能体"])


class SingleAgentChatRequest(BaseModel):
    message: str
    conversation_history: Optional[list] = None


class MultiAgentAnalyzeRequest(BaseModel):
    input_text: str


@router.post("/single/chat")
async def single_agent_chat(
    request: SingleAgentChatRequest,
    current_user: User = Depends(get_current_user),
):
    """单智能体对话（流式SSE）"""
    from app.services.ai.provider_factory import get_ai_provider
    ai = get_ai_provider()

    messages = [{"role": "system", "content": "你是东软智慧商务AI助手，帮助用户解决商务问题。你可以查询数据库、检索知识库。"}]
    if request.conversation_history:
        messages.extend(request.conversation_history)
    messages.append({"role": "user", "content": request.message})

    async def event_stream():
        full = ""
        try:
            async for token in ai.chat_stream(messages):
                full += token
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': full}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/multi/analyze")
async def multi_agent_analyze(
    request: MultiAgentAnalyzeRequest,
    current_user: User = Depends(get_current_user),
):
    """多智能体协作分析"""
    from app.agents.graph import run_agent_pipeline

    result = await run_agent_pipeline(request.input_text)
    return result
