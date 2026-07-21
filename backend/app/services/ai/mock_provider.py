import asyncio
import hashlib
from typing import AsyncGenerator, List
from app.services.ai.base import BaseAIProvider

# Simulated knowledge base responses
MOCK_RESPONSES = {
    "default": "您好！我是东软智慧商务AI助手，很高兴为您服务。请问有什么可以帮助您的？",
    "客服": "感谢您的咨询。根据您描述的问题，我建议：\n\n1. 首先检查您的账户信息是否正确\n2. 确认相关服务是否在有效期内\n3. 如果问题仍然存在，我们的客服团队将在24小时内与您联系\n\n还有其他需要帮助的吗？",
    "技术": "这是一个技术问题，让我为您分析：\n\n该问题可能由以下原因导致：\n- 系统配置不匹配\n- 网络连接不稳定\n- 软件版本过旧\n\n建议您先尝试重启服务，如果问题依然存在，我们会安排技术人员跟进。",
    "退款": "关于退款问题，我们的政策如下：\n\n1. 7天内无理由退款\n2. 超过7天需根据具体情况评估\n3. 退款将在3-5个工作日原路返回\n\n请问您需要我帮您提交退款申请吗？",
    "产品": "关于产品信息，让我为您详细介绍：\n\n我们的产品线涵盖：\n- 基础版：适合小型企业\n- 专业版：适合中型企业\n- 企业版：适合大型企业\n\n每个版本都有不同的功能配置，您可以根据需求选择。",
}

EMBEDDING_DIM = 768


def _get_mock_response(message: str) -> str:
    """Select a mock response based on message keywords."""
    keywords = {
        "客服": ["客服", "服务", "帮助", "咨询"],
        "技术": ["技术", "错误", "bug", "故障", "报错", "问题"],
        "退款": ["退款", "退货", "退费", "取消订单"],
        "产品": ["产品", "价格", "版本", "功能", "介绍", "了解"],
    }
    msg_lower = message.lower()
    for category, kws in keywords.items():
        if any(kw in msg_lower for kw in kws):
            return MOCK_RESPONSES[category]
    return MOCK_RESPONSES["default"]


def _simple_embed(texts: List[str]) -> List[List[float]]:
    """Generate deterministic mock embeddings using text hash."""
    embeddings = []
    for text in texts:
        h = hashlib.md5(text.encode()).digest()
        vec = [(b / 255.0) * 2 - 1 for b in h]
        # Pad to target dimension
        while len(vec) < EMBEDDING_DIM:
            vec.extend(vec[:EMBEDDING_DIM - len(vec)])
        embeddings.append(vec[:EMBEDDING_DIM])
    return embeddings


class MockAIProvider(BaseAIProvider):
    """Mock AI provider for development/demo without API keys."""

    async def chat_stream(self, messages: List[dict], **kwargs) -> AsyncGenerator[str, None]:
        # Get the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        response = _get_mock_response(user_message)

        # Simulate streaming with small delays
        for i, char in enumerate(response):
            yield char
            await asyncio.sleep(0.03)  # ~30ms per character

    async def chat(self, messages: List[dict], **kwargs) -> str:
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        await asyncio.sleep(0.3)  # Simulate API latency
        return _get_mock_response(user_message)

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        return _simple_embed(texts)
