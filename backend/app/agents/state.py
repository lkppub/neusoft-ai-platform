from typing import TypedDict, List, Optional


class AgentState(TypedDict):
    """State for the multi-agent customer service pipeline."""

    # Raw customer inquiry
    inquiry: str

    # Conversation history (plain dict list — NOT add_messages, which converts to
    # LangChain HumanMessage/AIMessage and breaks .get() access in reply nodes)
    messages: List[dict]

    # Classification result from classifier agent
    classification: Optional[dict]

    # Retrieved context from knowledge base / database
    retrieved_context: Optional[List[dict]]

    # Generated draft reply
    draft_reply: Optional[str]

    # Quality check result
    quality_result: Optional[dict]

    # Final approved reply
    final_reply: Optional[str]

    # Revision safety valve
    revision_count: int
