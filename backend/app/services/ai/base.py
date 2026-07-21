from abc import ABC, abstractmethod
from typing import AsyncGenerator, List


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""

    async def chat_with_tools(self, messages: List[dict], tools: List[dict], **kwargs) -> dict:
        """Chat with function-calling tools. Default: fall back to plain chat."""
        text = await self.chat(messages, **kwargs)
        return {"type": "text", "content": text}

    @abstractmethod
    async def chat_stream(self, messages: List[dict], **kwargs) -> AsyncGenerator[str, None]:
        """Stream chat response token by token."""
        ...

    @abstractmethod
    async def chat(self, messages: List[dict], **kwargs) -> str:
        """Non-streaming chat, returns complete response."""
        ...

    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for input texts."""
        ...
