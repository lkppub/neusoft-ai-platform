from typing import List, Optional
from app.services.knowledge.vector_store import get_vector_store
from app.services.ai.provider_factory import get_ai_provider


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline."""

    def __init__(self):
        self.vector_store = get_vector_store()
        self.ai = get_ai_provider()

    async def query(
        self,
        question: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> dict:
        """Execute RAG query: retrieve context -> generate answer."""

        # Step 1: Retrieve relevant chunks
        results = await self.vector_store.similarity_search(
            question, k=top_k, score_threshold=score_threshold
        )

        # Step 2: Build context
        if not results:
            # No relevant context found — return empty so caller can handle
            import logging
            logging.getLogger(__name__).warning(
                "RAG query returned no results for: %s", question[:80]
            )
            return {"answer": "", "sources": []}

        context = "\n\n---\n\n".join([
            f"[来源: {r['metadata'].get('source', '未知')}]\n{r['content']}"
            for r in results
        ])

        # Step 3: Build RAG prompt
        system_prompt = """你是一个专业的企业知识库问答助手。请基于提供的上下文信息回答问题。
规则：
1. 如果上下文包含答案，基于上下文准确回答
2. 如果上下文不包含答案，如实告知用户
3. 回答时引用具体的来源
4. 保持专业、友好的语气"""

        user_message = f"""上下文信息：
{context}

用户问题：{question}

请基于上述上下文回答问题："""

        # Step 4: Generate answer
        answer = await self.ai.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ])

        # Step 5: Return with sources
        return {
            "answer": answer,
            "sources": [
                {
                    "content": r["content"][:300] + ("..." if len(r["content"]) > 300 else ""),
                    "score": round(r["score"], 4),
                    "metadata": r["metadata"],
                }
                for r in results
            ],
        }


_rag_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """Get the RAG pipeline singleton."""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
