import json
from app.agents.state import AgentState
from app.services.ai.provider_factory import get_ai_provider


async def classifier_node(state: AgentState) -> dict:
    """Classify the customer inquiry by intent, category, priority, and sentiment."""
    ai = get_ai_provider()

    prompt = f"""请分析以下客户咨询。你必须从下列分类中选择最匹配的一项：

【可用分类】
技术支持、账号问题、账单咨询、产品咨询、投诉建议、售后服务、功能需求、商务咨询、其他

【规则】
- category 必须严格从上述列表中选取，不得自创
- 如果无法明确归入前8类，使用"其他"

客户咨询：{state['inquiry']}

返回JSON格式：
{{
    "category": "上述分类之一",
    "intent": "客户意图",
    "sentiment": "positive/neutral/negative",
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
