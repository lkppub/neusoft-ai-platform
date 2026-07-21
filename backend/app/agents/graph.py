"""Build and compile the LangGraph multi-agent workflow.

Pipeline: Classifier -> Retriever -> Reply Generator <-> Quality Checker -> END
"""

from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.nodes.classifier import classifier_node
from app.agents.nodes.query import retrieval_node
from app.agents.nodes.reply import reply_generator_node
from app.agents.nodes.quality_check import quality_check_node, decide_next


def build_agent_graph():
    """Build and compile the multi-agent StateGraph."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("classifier", classifier_node)
    workflow.add_node("retriever", retrieval_node)
    workflow.add_node("reply_generator", reply_generator_node)
    workflow.add_node("quality_checker", quality_check_node)

    # Define edges
    workflow.set_entry_point("classifier")
    workflow.add_edge("classifier", "retriever")
    workflow.add_edge("retriever", "reply_generator")
    workflow.add_edge("reply_generator", "quality_checker")

    # Conditional routing: loop for revisions or finish
    workflow.add_conditional_edges(
        "quality_checker",
        decide_next,
        {
            "revise": "reply_generator",
            "done": END,
        },
    )

    return workflow.compile()


# Singleton compiled graph
_agent_graph = None


def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph


async def run_agent_pipeline(inquiry: str) -> dict:
    """Run the full multi-agent pipeline on a customer inquiry."""
    graph = get_agent_graph()

    initial_state = {
        "inquiry": inquiry,
        "messages": [],
        "classification": None,
        "retrieved_context": None,
        "draft_reply": None,
        "quality_result": None,
        "final_reply": None,
        "revision_count": 0,
    }

    result = await graph.ainvoke(initial_state)

    return {
        "inquiry": inquiry,
        "classification": result.get("classification"),
        "draft_reply": result.get("draft_reply"),
        "final_reply": result.get("final_reply"),
        "quality_score": result.get("quality_result", {}).get("score"),
        "revision_count": result.get("revision_count", 0),
    }


async def run_agent_pipeline_lite(inquiry: str, history: list | None = None) -> dict:
    """
    Lightweight pipeline for chat: skip classifier + quality checker.
    Only runs retriever → reply_generator = 1 LLM call.
    """
    from app.agents.nodes.query import retrieval_node
    from app.agents.nodes.reply import reply_generator_node

    # Run retriever manually
    state = {"inquiry": inquiry, "messages": history or []}
    retrieval_result = await retrieval_node(state)
    state.update(retrieval_result)

    # Run reply generator
    reply_result = await reply_generator_node(state)
    state.update(reply_result)

    return {
        "inquiry": inquiry,
        "final_reply": state.get("draft_reply") or state.get("final_reply") or reply_result.get("draft_reply", ""),
        "retrieved_context": state.get("retrieved_context"),
    }


async def run_agent_pipeline_with_tools(
    inquiry: str,
    user_id: str = "",
    history: list | None = None,
) -> dict:
    """
    Tool-aware pipeline: LLM decides whether to call tools or reply directly.

    Flow:
      1. Send inquiry + tools → LLM
      2a. LLM replies directly → return text
      2b. LLM requests tool calls → execute tools → send results → LLM replies
    """
    import json
    from app.services.ai.provider_factory import get_ai_provider
    from app.agents.tools import TOOLS, execute_tool

    ai = get_ai_provider()

    # ── System prompt ──
    system_prompt = (
        "你是一个智能客服助手，可以调用以下工具获取真实信息：\n\n"
        "1. **查询工单**：用户说'我的工单'、'工单状态'时 → 调用 get_my_tickets\n"
        "2. **搜索知识库**：用户问任何具体问题（如'怎么操作'、'是什么'、'怎么办'、'规则'、'流程'、'有没有'、'支持什么'等）→ 调用 search_knowledge\n\n"
        "【最重要规则】\n"
        "- ★ 用户提了具体问题，且你不确定答案时，必须调用 search_knowledge 工具查询再回答，绝对不要凭记忆编造\n"
        "- 知识库返回空时，诚实说'知识库中暂无相关信息'\n"
        "- 你只能查工单和搜知识库，不能创建、修改、删除任何数据\n"
        "- 回复保持专业、简洁、友好"
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history (last 10 rounds)
    if history:
        recent = history[-20:]
        for msg in recent:
            role = msg.get("role", "user") if isinstance(msg, dict) else getattr(msg, "role", "user")
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            if role in ("user", "human"):
                messages.append({"role": "user", "content": content})
            elif role in ("assistant", "ai"):
                messages.append({"role": "assistant", "content": content})

    # Add current inquiry
    messages.append({"role": "user", "content": inquiry})

    # ── Step 1: Initial call with tools ──
    tool_calls_log = []

    resp = await ai.chat_with_tools(messages, tools=TOOLS)

    if resp["type"] == "text":
        return {
            "inquiry": inquiry,
            "final_reply": resp["content"],
            "tool_calls": [],
        }

    # ── Step 2: Execute tool calls ──
    if resp["type"] == "tool_calls":
        # Add the assistant message with tool_calls to history
        assistant_tool_msg = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": c["id"],
                    "type": "function",
                    "function": {"name": c["name"], "arguments": c["arguments"]},
                }
                for c in resp["calls"]
            ],
        }
        messages.append(assistant_tool_msg)

        for call in resp["calls"]:
            try:
                args = json.loads(call["arguments"]) if isinstance(call["arguments"], str) else call["arguments"]
            except json.JSONDecodeError:
                args = {}

            result_text = await execute_tool(call["name"], args, user_id)
            tool_calls_log.append({"tool": call["name"], "args": args, "result_preview": result_text[:200]})

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": result_text,
            })

        # ── Step 3: Final reply with tool results ──
        final_resp = await ai.chat_with_tools(messages, tools=TOOLS)
        final_reply = final_resp.get("content", "") if final_resp["type"] == "text" else "抱歉，处理您的请求时出现了问题。"

        return {
            "inquiry": inquiry,
            "final_reply": final_reply,
            "tool_calls": tool_calls_log,
        }

    return {
        "inquiry": inquiry,
        "final_reply": "抱歉，我暂时无法处理这个请求。",
        "tool_calls": tool_calls_log,
    }


async def run_agent_pipeline_for_chat(
    inquiry: str,
    history: list | None = None,
) -> dict:
    """
    Run the full multi-agent pipeline for the chat interface.

    Differs from run_agent_pipeline by accepting conversation history,
    which the reply generator uses to maintain multi-turn context.

    Args:
        inquiry: The current user message
        history: List of prior messages [{"role": "...", "content": "..."}]
    """
    graph = get_agent_graph()

    initial_state = {
        "inquiry": inquiry,
        "messages": history or [],
        "classification": None,
        "retrieved_context": None,
        "draft_reply": None,
        "quality_result": None,
        "final_reply": None,
        "revision_count": 0,
    }

    result = await graph.ainvoke(initial_state)

    return {
        "inquiry": inquiry,
        "classification": result.get("classification"),
        "draft_reply": result.get("draft_reply"),
        "final_reply": result.get("final_reply"),
        "quality_score": result.get("quality_result", {}).get("score"),
        "retrieved_context": result.get("retrieved_context"),
        "revision_count": result.get("revision_count", 0),
    }
