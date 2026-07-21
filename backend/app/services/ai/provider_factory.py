from app.core.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.mock_provider import MockAIProvider

_ai_provider: BaseAIProvider | None = None


def get_ai_provider() -> BaseAIProvider:
    """Get the AI provider based on settings (singleton)."""
    global _ai_provider

    if _ai_provider is not None:
        return _ai_provider

    if settings.AI_PROVIDER == "deepseek":
        from app.services.ai.deepseek_provider import DeepSeekProvider
        _ai_provider = DeepSeekProvider(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            default_model=settings.DEEPSEEK_MODEL,
        )
    else:
        _ai_provider = MockAIProvider()

    return _ai_provider
