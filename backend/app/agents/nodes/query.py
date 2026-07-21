from app.agents.state import AgentState
from app.services.knowledge.rag_pipeline import get_rag_pipeline


async def retrieval_node(state: AgentState) -> dict:
    """Retrieve relevant knowledge based on classification."""
    classification = state.get("classification", {})
    inquiry = state.get("inquiry", "")

    # Query RAG pipeline for relevant knowledge
    rag = get_rag_pipeline()
    result = await rag.query(
        question=inquiry,
        top_k=5,
        score_threshold=0.5,
    )

    retrieved_context = result.get("sources", [])

    # If no RAG results, provide classification-only context with clear signal
    if not retrieved_context:
        retrieved_context = [{
            "content": (
                f"【注意：知识库中未检索到相关内容】\n"
                f"问题分类: {classification.get('category', '未知')}，"
                f"优先级: {classification.get('priority', 'medium')}"
            ),
            "score": 0.0,
            "metadata": {"source": "系统提示（无知识库匹配）"},
        }]

    return {"retrieved_context": retrieved_context}
