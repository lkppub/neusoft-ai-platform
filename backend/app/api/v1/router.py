from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.tickets import router as tickets_router
from app.api.v1.templates import router as templates_router
from app.api.v1.admin import router as admin_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.voice import router as voice_router
from app.api.v1.agent import router as agent_router
from app.api.v1.dify import router as dify_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(knowledge_router)
api_v1_router.include_router(tickets_router)
api_v1_router.include_router(templates_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(voice_router)
api_v1_router.include_router(agent_router)
api_v1_router.include_router(dify_router)
