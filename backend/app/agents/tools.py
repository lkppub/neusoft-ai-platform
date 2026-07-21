"""Agent tools with OpenAI-compatible Function Calling schemas.

Each tool has:
- An OpenAI function schema (name, description, parameters)
- A handler function that executes the actual logic
"""

import json
import logging

logger = logging.getLogger(__name__)

# ── Tool Registry ────────────────────────────────────────────

TOOLS: list[dict] = []
TOOL_HANDLERS: dict[str, callable] = {}


def _register(schema: dict, handler: callable):
    """Register a tool schema + handler."""
    TOOLS.append(schema)
    TOOL_HANDLERS[schema["function"]["name"]] = handler


# ── Tool: Query customer service tickets ─────────────────────

async def _get_my_tickets(user_id: str, limit: int = 5) -> str:
    """Query the database for the current user's tickets."""
    from app.core.database import async_session_factory
    from sqlalchemy import select, text

    async with async_session_factory() as db:
        result = await db.execute(
            text(
                "SELECT subject, status, priority, problem_category, created_at "
                "FROM customer_service_tickets "
                "WHERE user_id = :uid ORDER BY created_at DESC LIMIT :lim"
            ),
            {"uid": user_id, "lim": limit},
        )
        rows = result.fetchall()
        if not rows:
            return "您目前没有工单记录。"

        items = []
        for r in rows:
            items.append(
                f"- [{r[1]}] {r[0]} (优先级: {r[2]}, 分类: {r[3] or '未分类'}, 创建: {r[4]})"
            )
        return "您的工单列表：\n" + "\n".join(items)


_get_my_tickets_schema = {
    "type": "function",
    "function": {
        "name": "get_my_tickets",
        "description": "查询当前用户的工单列表。当用户想查看自己的工单、问'我的工单'、问工单状态时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "返回的工单数量上限，默认5条",
                    "default": 5,
                },
            },
        },
    },
}
_register(_get_my_tickets_schema, _get_my_tickets)


# ── Tool 2: Search knowledge base ─────────────────────────────

async def _search_knowledge(query: str, top_k: int = 3) -> str:
    """Search the enterprise knowledge base for relevant documents."""
    from app.services.knowledge.vector_store import get_vector_store

    vector_store = get_vector_store()
    results = await vector_store.similarity_search(query, k=top_k, score_threshold=0.3)

    if not results:
        return "知识库中未找到相关信息。"

    items = []
    for r in results:
        src = r.get("metadata", {}).get("source", "未知来源")
        content = r.get("content", "")[:500]
        items.append(f"【{src}】{content}")
    return "\n\n".join(items)


_search_knowledge_schema = {
    "type": "function",
    "function": {
        "name": "search_knowledge",
        "description": "在企业知识库中搜索相关信息。当用户询问产品/业务/政策等问题时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量，默认3",
                    "default": 3,
                },
            },
            "required": ["query"],
        },
    },
}
_register(_search_knowledge_schema, _search_knowledge)


# ── Tool 3: Create ticket ─────────────────────────────────────

async def _create_ticket(user_id: str, subject: str, description: str, priority: str = "medium") -> str:
    """Create a new customer service ticket."""
    from app.core.database import async_session_factory
    from app.models.ticket import CustomerServiceTicket, TicketMessage, TicketMessageType
    import uuid

    async with async_session_factory() as db:
        ticket = CustomerServiceTicket(
            user_id=user_id,
            subject=subject,
            description=description,
            priority=priority,
        )
        db.add(ticket)
        await db.flush()

        msg = TicketMessage(
            ticket_id=ticket.id,
            sender_id=user_id,
            message_type=TicketMessageType.CUSTOMER,
            content=description or subject,
        )
        db.add(msg)
        await db.commit()
        return f"工单已创建成功！工单主题：{subject}，优先级：{priority}。我们的客服人员会尽快处理。"


_create_ticket_schema = {
    "type": "function",
    "function": {
        "name": "create_ticket",
        "description": "为用户创建新的客服工单。当用户明确要求创建工单、提交问题、报修时报障时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "工单主题",
                },
                "description": {
                    "type": "string",
                    "description": "工单详细描述",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "优先级，默认medium",
                },
            },
            "required": ["subject", "description"],
        },
    },
}
# _register(_create_ticket_schema, _create_ticket)  ← 已禁用


# ── Tool execution dispatcher ─────────────────────────────────

async def execute_tool(tool_name: str, tool_args: dict, user_id: str) -> str:
    """Execute a tool by name and return its result as a string."""
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return f"未知工具: {tool_name}"

    # Inject user_id for tools that need it
    # (the LLM doesn't know the user_id, so we inject it server-side)
    if "user_id" in handler.__code__.co_varnames:
        tool_args = {**tool_args, "user_id": user_id}

    try:
        logger.info("Executing tool: %s(%s)", tool_name, tool_args)
        result = await handler(**tool_args)
        logger.info("Tool %s returned %d chars", tool_name, len(result))
        return result
    except Exception as exc:
        logger.error("Tool %s failed: %s", tool_name, exc)
        return f"工具执行失败: {exc}"
