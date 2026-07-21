"""
Embedding service using sentence-transformers for semantic text embeddings.

Supports Chinese and English text. Uses a configurable local model —
no external API calls needed.
"""
import logging
from typing import List
from functools import lru_cache

logger = logging.getLogger(__name__)

# 默认使用支持中文的多语言模型，体积适中（~120MB）
DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# 模型加载后缓存在模块级别
_model = None
_model_name = None


def get_embedding_model(model_name: str = DEFAULT_MODEL):
    """Lazy-load the sentence-transformers model (singleton per model name)."""
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model

    logger.info("Loading embedding model: %s ...", model_name)
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_name)
        _model_name = model_name
        logger.info(
            "Embedding model loaded: %s (dim=%d)",
            model_name,
            _model.get_sentence_embedding_dimension(),
        )
    except ImportError:
        logger.error(
            "sentence-transformers not installed. "
            "Run: pip install sentence-transformers"
        )
        raise
    except Exception as e:
        logger.error("Failed to load model '%s': %s", model_name, e)
        raise

    return _model


class EmbeddingService:
    """Generates semantic embeddings using sentence-transformers."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or DEFAULT_MODEL

    @property
    def model(self):
        return get_embedding_model(self.model_name)

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    async def encode(self, texts: List[str]) -> List[List[float]]:
        """Encode a list of texts into embeddings (async-compatible)."""
        import asyncio
        # sentence-transformers encode is synchronous and blocking — run in thread pool
        # to avoid blocking the event loop (critical for background tasks).
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self.model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            ),
        )
        return embeddings.tolist()

    async def encode_query(self, text: str) -> List[float]:
        """Encode a single query string."""
        results = await self.encode([text])
        return results[0]


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service(model_name: str | None = None) -> EmbeddingService:
    """Get the global embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        from app.core.config import settings
        model = model_name or settings.EMBEDDING_MODEL
        _embedding_service = EmbeddingService(model_name=model)
    return _embedding_service
