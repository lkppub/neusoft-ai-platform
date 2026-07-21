"""
Chat context builder: system prompt + FAQ retrieval + conversation history.
Provides business-aware context for the AI chat assistant.
"""
import logging
from typing import List, Dict, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import FAQEntry
from app.models.config import AIConfig

logger = logging.getLogger(__name__)

# 默认系统提示词（如果数据库中没有配置）
DEFAULT_SYSTEM_PROMPT = """你是东软智慧商务AI助手，专门为东软集团的企业客户提供专业服务。

你的职责包括：
1. 回答产品相关问题（版本功能、价格、技术规格等）
2. 处理售后问题（退款、技术支持、账号问题等）
3. 提供商务咨询和建议

回答规则：
- 如果知识库中有相关信息，请基于知识库准确回答，并引用来源
- 如果知识库中没有相关信息，请诚实告知，并提供替代建议（如转接人工客服）
- 语气专业、友好、耐心，体现东软的企业形象
- 回答结构清晰，适当使用要点列表
- 涉及退款、账号等敏感操作时，务必确认用户身份"""


async def search_faq_by_keywords(
    db: AsyncSession,
    query: str,
    top_k: int = 5,
) -> List[dict]:
    """
    用关键词匹配搜索 SQLite 中的 FAQ 条目。
    在 Chroma 向量搜索不可用（如 DeepSeek 无 embeddings API）时作为检索主力。
    """
    # 分词：按常见分隔符拆分
    import re
    keywords = re.split(r'[，。！？\s,!.?]+', query)
    keywords = [kw.strip() for kw in keywords if len(kw.strip()) >= 2]

    if not keywords:
        keywords = [query.strip()]

    # 中文 n-gram 补充：对长度>=4的无标点中文短语，生成2~4字片段
    ngram_keywords = []
    for kw in keywords[:3]:  # 只对前3个关键词做n-gram
        if len(kw) >= 4:
            # 生成2-gram和3-gram
            for n in (2, 3):
                for i in range(len(kw) - n + 1):
                    ngram_keywords.append(kw[i:i+n])
    # 去重，原关键词优先
    keywords = keywords + [k for k in ngram_keywords if k not in keywords]

    # 构建 OR 条件：匹配问题或分类
    conditions = []
    for kw in keywords[:10]:  # 最多 10 个关键词
        conditions.append(FAQEntry.question.contains(kw))
        conditions.append(FAQEntry.category.contains(kw))

    stmt = (
        select(FAQEntry)
        .where(
            FAQEntry.is_published == True,
            or_(*conditions),
        )
        .limit(top_k * 2)  # 多取一些用于打分
    )

    result = await db.execute(stmt)
    faqs = result.scalars().all()

    if not faqs:
        return []

    # 简单打分：匹配的关键词数量
    scored = []
    for faq in faqs:
        score = 0
        q_lower = faq.question.lower()
        c_lower = faq.category.lower()
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in q_lower:
                score += 3  # 问题匹配权重更高
            if kw_lower in c_lower:
                score += 1
        if score > 0:
            scored.append((score, faq))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    # 递增匹配 FAQ 的查看计数
    for _, faq in top:
        faq.view_count += 1
    await db.flush()

    return [
        {
            "content": f"Q: {faq.question}\nA: {faq.answer}",
            "score": score / (len(keywords) * 3),
            "metadata": {
                "source": "FAQ",
                "category": faq.category,
            },
        }
        for score, faq in top
    ]


async def get_system_prompt(db: AsyncSession) -> str:
    """从数据库读取 system prompt 配置，无则用默认值。"""
    try:
        result = await db.execute(
            select(AIConfig).where(AIConfig.config_key == "system_prompt")
        )
        config = result.scalar_one_or_none()
        if config and config.config_value:
            return config.config_value.strip()
    except Exception:
        pass
    return DEFAULT_SYSTEM_PROMPT


async def build_chat_context(
    db: AsyncSession,
    user_message: str,
    history: List[dict],
    enable_rag: bool = True,
    top_k: int = 3,
) -> List[dict]:
    """
    构建发送给 AI 的完整消息列表。

    结构：[system_prompt] + [knowledge_context] + [history...]

    Args:
        db: 数据库会话
        user_message: 当前用户消息
        history: 历史消息列表 [{"role": "...", "content": "..."}]
        enable_rag: 是否启用知识库检索
        top_k: 检索条数

    Returns:
        完整的 messages 列表
    """
    messages = []

    # 1. System prompt
    system_prompt = await get_system_prompt(db)
    messages.append({"role": "system", "content": system_prompt})

    # 2. Knowledge context — ChromaDB 语义搜索优先，SQLite 关键词回退
    if enable_rag:
        faq_results = []
        try:
            # 主力：ChromaDB 语义向量搜索（自动处理中文分词问题）
            from app.services.knowledge.vector_store import get_vector_store
            vs = get_vector_store()
            vector_results = await vs.similarity_search(user_message, k=top_k, score_threshold=0.3)

            if vector_results:
                # 转为统一格式并递增 FAQ 的 view_count
                for r in vector_results:
                    src = r["metadata"].get("source", "")
                    if src.startswith("FAQ-"):
                        # 从 FAQ 表递增 view_count
                        faq_id = r["metadata"].get("doc_id", "").replace("faq-", "")
                        if faq_id:
                            try:
                                from sqlalchemy import select as _sel
                                faq_result = await db.execute(_sel(FAQEntry).where(FAQEntry.id == faq_id))
                                faq_entry = faq_result.scalar_one_or_none()
                                if faq_entry:
                                    faq_entry.view_count += 1
                                    await db.flush()
                            except Exception:
                                pass
                    faq_results.append({
                        "content": r["content"],
                        "score": r["score"],
                        "metadata": r["metadata"],
                    })
                logger.debug(
                    "ChromaDB FAQ search: query='%s' → %d results",
                    user_message[:50], len(faq_results),
                )
        except Exception as e:
            logger.warning("ChromaDB search failed, falling back to SQLite: %s", e)

        # 回退：SQLite 关键词搜索
        if not faq_results:
            try:
                faq_results = await search_faq_by_keywords(db, user_message, top_k=top_k)
                if faq_results:
                    logger.debug(
                        "SQLite FAQ fallback: query='%s' → %d results",
                        user_message[:50], len(faq_results),
                    )
            except Exception as e:
                logger.warning("SQLite FAQ search also failed: %s", e)

        if faq_results:
            context_parts = ["【参考知识 - 请优先基于以下信息回答】"]
            for i, r in enumerate(faq_results):
                cat = r["metadata"].get("category", "未知")
                source = r["metadata"].get("source", "")
                label = f"FAQ-{cat}" if source.startswith("FAQ-") else source
                context_parts.append(f"[{label}] {r['content']}")
            context_text = "\n\n".join(context_parts)

            messages.append({
                "role": "system",
                "content": context_text,
            })

    # 3. Conversation history
    messages.extend(history)

    return messages


async def build_chat_context_simple(
    user_message: str,
    history: List[dict],
) -> List[dict]:
    """
    构建简化版消息列表（不查数据库，不查知识库）。
    仅添加默认 system prompt + 历史消息。
    """
    messages = [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}]
    messages.extend(history)
    return messages
