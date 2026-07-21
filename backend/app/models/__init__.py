from app.models.user import User, UserRole
from app.models.conversation import Conversation, Message, MessageRole
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk, FAQEntry, DocumentStatus
from app.models.ticket import CustomerServiceTicket, TicketMessage, ReplyTemplate, TicketPriority, TicketStatus, TicketMessageType
from app.models.config import AIConfig, PromptTemplate
from app.models.analytics import DashboardSnapshot, AnalyticsReport

__all__ = [
    "User", "UserRole",
    "Conversation", "Message", "MessageRole",
    "KnowledgeDocument", "KnowledgeChunk", "FAQEntry", "DocumentStatus",
    "CustomerServiceTicket", "TicketMessage", "ReplyTemplate",
    "TicketPriority", "TicketStatus", "TicketMessageType",
    "AIConfig", "PromptTemplate",
    "DashboardSnapshot", "AnalyticsReport",
]
