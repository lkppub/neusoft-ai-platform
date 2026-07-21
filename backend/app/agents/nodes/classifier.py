import json
from app.agents.state import AgentState
from app.services.ai.provider_factory import get_ai_provider


async def classifier_node(state: AgentState) -> dict:
    """Classify the customer inquiry by intent, category, priority, and sentiment."""
    ai = get_ai_provider()

    prompt = f"""请分析以下客户咨询，并以JSON格式返回分类结果：

客户咨询：{state['inquiry']}

返回JSON格式：
{{
    "category": "问题分类（技术支持/账单咨询/产品咨询/投诉建议/账号问题/其他）",
    "priority": "优先级（low/medium/high/urgent）",
    "intent": "客户意图",
    "sentiment": "情绪（positive/neutral/negative）",
    "key_entities": ["关键实体1", "关键实体2"],
    "required_knowledge": "需要查询的知识类型"
}}

只返回JSON，不要包含其他内容。"""

    response = await ai.chat([{"role": "user", "content": prompt}])

    # Parse JSON response
    try:
        classification = json.loads(response)
    except json.JSONDecodeError:
        # Extract JSON from response if mixed with text
        import re
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            classification = json.loads(match.group())
        else:
            classification = {
                "category": "其他",
                "priority": "medium",
                "intent": "未知",
                "sentiment": "neutral",
                "key_entities": [],
                "required_knowledge": "通用知识",
            }

    return {"classification": classification}
