import json
from app.agents.state import AgentState
from app.services.ai.provider_factory import get_ai_provider


async def quality_check_node(state: AgentState) -> dict:
    """Review the draft reply for quality and compliance."""
    ai = get_ai_provider()

    draft = state.get("draft_reply", "")
    inquiry = state.get("inquiry", "")
    classification = state.get("classification", {})

    prompt = f"""请审查以下客服回复的质量：

客户问题：{inquiry}
问题分类：{classification.get('category', '未知')}

草稿回复：
{draft}

请从以下维度评分并返回JSON：
1. 准确性：回复是否基于事实？
2. 完整性：是否回答了客户问题？
3. 语气：是否专业友好？
4. 合规性：是否符合商务规范？

返回JSON格式：
{{
    "score": 0-100,
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"],
    "needs_revision": true/false,
    "passed": true/false
}}

只返回JSON，不要包含其他内容。"""

    response = await ai.chat([{"role": "user", "content": prompt}])

    try:
        quality = json.loads(response)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            quality = json.loads(match.group())
        else:
            quality = {"score": 80, "issues": [], "suggestions": [], "needs_revision": False, "passed": True}

    revision_count = state.get("revision_count", 0) + 1
    max_revisions = 3

    # Force pass if max revisions reached
    if revision_count >= max_revisions:
        quality["needs_revision"] = False
        quality["passed"] = True

    return {
        "quality_result": quality,
        "revision_count": revision_count,
        "final_reply": draft if quality.get("passed", False) or not quality.get("needs_revision", False) else None,
    }


def decide_next(state: AgentState) -> str:
    """Decide whether to revise or finish."""
    quality = state.get("quality_result", {})
    if quality.get("needs_revision", False):
        return "revise"
    return "done"
