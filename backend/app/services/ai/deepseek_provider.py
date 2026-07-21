from typing import AsyncGenerator, List
from openai import AsyncOpenAI
from app.services.ai.base import BaseAIProvider
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class DeepSeekProvider(BaseAIProvider):
    """DeepSeek API provider via OpenAI-compatible SDK."""

    def __init__(self, api_key: str, base_url: str, default_model: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.default_model = default_model

    async def chat_with_tools(
        self,
        messages: List[dict],
        tools: List[dict],
        **kwargs,
    ) -> dict:
        """
        Send a chat request with function-calling tools.

        Returns a dict:
          - {"type": "text", "content": "..."}   — model replied directly
          - {"type": "tool_calls", "calls": [...]} — model wants to call tools
        """
        model = kwargs.get("model", self.default_model)
        temperature = kwargs.get("temperature", settings.DEEPSEEK_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", settings.DEEPSEEK_MAX_TOKENS)

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice="auto",
            stream=False,
        )

        choice = response.choices[0]
        msg = choice.message

        if msg.tool_calls:
            calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in msg.tool_calls
            ]
            logger.info("LLM requested tool calls: %s", [c["name"] for c in calls])
            return {"type": "tool_calls", "calls": calls}
        else:
            return {"type": "text", "content": msg.content or ""}

    async def chat_stream(self, messages: List[dict], **kwargs) -> AsyncGenerator[str, None]:
        model = kwargs.get("model", self.default_model)
        temperature = kwargs.get("temperature", settings.DEEPSEEK_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", settings.DEEPSEEK_MAX_TOKENS)

        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def chat(self, messages: List[dict], **kwargs) -> str:
        model = kwargs.get("model", self.default_model)
        temperature = kwargs.get("temperature", settings.DEEPSEEK_TEMPERATURE)
        max_tokens = kwargs.get("max_tokens", settings.DEEPSEEK_MAX_TOKENS)

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return response.choices[0].message.content or ""

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings. DeepSeek does not provide a dedicated embeddings API,
        so we fall back to using the chat model to produce simple hash-based vectors.
        This allows RAG to remain functional while using DeepSeek for chat.

        For production RAG, consider using a dedicated embedding provider
        (e.g., text-embedding-3-small from OpenAI, or a local sentence-transformer).
        """
        logger.warning(
            "DeepSeek does not support embeddings API. "
            "Using hash-based fallback vectors. RAG retrieval accuracy will be limited."
        )
        import hashlib
        dim = 1536  # common embedding dimension
        embeddings = []
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            vec = [(b / 255.0) * 2 - 1 for b in h]
            while len(vec) < dim:
                vec.extend(vec[:dim - len(vec)])
            embeddings.append(vec[:dim])
        return embeddings
