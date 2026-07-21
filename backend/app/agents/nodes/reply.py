from app.agents.state import AgentState
from app.services.ai.provider_factory import get_ai_provider


async def reply_generator_node(state: AgentState) -> dict:
    """Generate a professional reply based on classification, retrieved context, and conversation history."""
    ai = get_ai_provider()

    inquiry = state.get("inquiry", "")
    classification = state.get("classification", {})
    retrieved = state.get("retrieved_context", [])
    quality_feedback = state.get("quality_result", {})
    history = state.get("messages", [])

    # Build context from retrieved knowledge
    context_text = "\n\n".join([
        f"[{r.get('metadata', {}).get('source', '未知来源')}]: {r.get('content', '')}"
        for r in retrieved
    ]) if retrieved else "（未检索到相关知识库内容，请基于通用商务知识回答）"

    # Build conversation history text (exclude system messages, limit to last 10 turns)
    history_text = ""
    if history:
        recent = history[-20:]  # 最近 20 条（10 轮对话）
        history_parts = []
        for msg in recent:
            # 兼容 dict 和 LangChain 消息对象（HumanMessage / AIMessage）
            if hasattr(msg, 'get'):
                role = msg.get("role", "")
                content = msg.get("content", "")
            else:
                # LangChain message: .type → "human"|"ai"|"system", .content → str
                msg_type = getattr(msg, 'type', 'user')
                role = "user" if msg_type == "human" else ("assistant" if msg_type == "ai" else msg_type)
                content = getattr(msg, 'content', '') or ""
            role_label = "客户" if role in ("user", "human") else "客服"
            history_parts.append(f"[{role_label}]: {content}")
        if history_parts:
            history_text = "\n".join(history_parts)

    revision_note = ""
    if quality_feedback and quality_feedback.get("issues"):
        issues = quality_feedback.get("issues", [])
        suggestions = quality_feedback.get("suggestions", [])
        revision_note = f"""
【修改要求 - 请针对以下问题进行改进】
问题：{'; '.join(issues)}
建议：{'; '.join(suggestions)}
"""

    # Detect if we have real knowledge or just a "no results" signal
    has_real_knowledge = bool(retrieved) and not any(
        "知识库中未检索到相关内容" in r.get("content", "")
        for r in retrieved
    )

    prompt = f"""你是一个知识库问答助手。你只能基于「参考知识」中提供的真实信息回答问题。

【你的能力边界 — 必须严格遵守】
1. 你无权访问任何后端系统：无法查询数据库、无法查看工单、无法获取用户信息、无法执行任何操作
2. 你唯一的信息来源是下方的「参考知识」。参考知识之外的信息一律视为不存在
3. 如果用户要求你执行操作（如查询工单、查看订单、修改信息等），你必须明确回复："抱歉，我无法直接访问系统为您查询。如需帮助，请转接人工客服。"
4. 绝对禁止编造、杜撰、或使用你训练数据中的产品信息/价格/政策/功能

客户问题：{inquiry}

参考知识：
{context_text}

{"对话历史：\n" + history_text if history_text else ""}
{revision_note}

【回复要求】
{'''1. 仅基于参考知识中的信息回答，引用具体来源
2. 回复结构清晰，适当使用要点列表''' if has_real_knowledge else '''1. ★ 参考知识中没有相关信息 — 诚实告知用户你无法回答
2. 可以参考"你的能力边界"中的话术回复用户
3. 语气保持专业友好'''}

请直接输出回复内容："""

    response = await ai.chat([{"role": "user", "content": prompt}])

    return {"draft_reply": response}
