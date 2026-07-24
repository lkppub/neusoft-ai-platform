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

async def _get_my_tickets(
    user_id: str,
    limit: int = 5,
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
) -> str:
    """Query the database for the current user's tickets, with optional filters."""
    from app.core.database import async_session_factory
    from sqlalchemy import text

    conditions = ["user_id = :uid"]
    params: dict = {"uid": user_id, "lim": limit}

    if status:
        status_map = {
            "待处理": "OPEN", "处理中": "IN_PROGRESS", "等待客户": "WAITING_CUSTOMER",
            "已解决": "RESOLVED", "已关闭": "CLOSED",
            "未处理": "OPEN", "未解决": "OPEN",
        }
        db_status = status_map.get(status, status.upper() if status.isascii() else status)
        conditions.append("status = :st")
        params["st"] = db_status

    if category:
        conditions.append("problem_category LIKE :cat")
        params["cat"] = f"%{category}%"

    if priority:
        prio_map = {"低": "LOW", "中": "MEDIUM", "高": "HIGH", "紧急": "URGENT"}
        db_prio = prio_map.get(priority, priority.upper() if priority.isascii() else priority)
        conditions.append("priority = :pr")
        params["pr"] = db_prio

    where = " AND ".join(conditions)

    async with async_session_factory() as db:
        result = await db.execute(
            text(
                f"SELECT subject, status, priority, problem_category, created_at "
                f"FROM customer_service_tickets "
                f"WHERE {where} ORDER BY created_at DESC LIMIT :lim"
            ),
            params,
        )
        rows = result.fetchall()
        if not rows:
            filters_desc = []
            if status:
                filters_desc.append(f"状态为'{status}'")
            if category:
                filters_desc.append(f"分类为'{category}'")
            desc = "且".join(filters_desc) if filters_desc else ""
            return f"您目前没有{desc}的工单。" if desc else "您目前没有工单记录。"

        status_cn = {"OPEN": "待处理", "IN_PROGRESS": "处理中", "RESOLVED": "已解决", "CLOSED": "已关闭"}
        items = []
        for r in rows:
            st = status_cn.get(r[1], r[1])
            items.append(f"- [{st}] {r[0]} (优先级: {r[2]}, 分类: {r[3] or '未分类'}, 创建: {r[4]})")

        header = f"以下是最新{len(items)}条工单（系统限制最多显示{limit}条）：\n" if len(items) == limit else f"您的工单列表（共{len(items)}条）：\n"
        return header + "\n".join(items)


_get_my_tickets_schema = {
    "type": "function",
    "function": {
        "name": "get_my_tickets",
        "description": (
            "查询当前用户的工单列表。当用户想查看自己的工单、问'我的工单'、问工单状态时调用。"
            "系统限制每次最多返回5条工单。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "返回的工单数量上限，固定为5条",
                    "default": 5,
                },
                "status": {
                    "type": "string",
                    "description": "按状态筛选：待处理/未处理（未解决的）、处理中、已解决、已关闭。用户说'未处理的'、'没解决的'、'进行中的'时使用此参数。",
                },
                "category": {
                    "type": "string",
                    "description": "按分类筛选：技术支持、账号问题、账单咨询、产品咨询、投诉建议等。",
                },
                "priority": {
                    "type": "string",
                    "description": "按优先级筛选：低、中、高、紧急。用户说'优先级为中的'、'高优先级的'时使用此参数。",
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
