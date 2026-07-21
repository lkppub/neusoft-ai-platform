"""Dify integration API routes.

Endpoints for:
- Chat with Dify applications (streaming SSE)
- Execute Dify workflows
- Manage Dify knowledge bases
- Generate images via Dify tools
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.services.dify.dify_client import get_dify_client

router = APIRouter(prefix="/dify", tags=["Dify低代码"])


# ── Request / Response models ──────────────────────────────

class DifyChatRequest(BaseModel):
    query: str
    conversation_id: str = ""
    inputs: Optional[dict] = None


class DifyWorkflowRequest(BaseModel):
    inputs: dict = Field(default_factory=dict)
    response_mode: str = "blocking"


class DifyUploadRequest(BaseModel):
    dataset_id: str
    file_path: str
    file_name: str = ""
    indexing_technique: str = "high_quality"


class DifyImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    size: str = "1024x1024"
    n: int = Field(default=1, ge=1, le=4)


# ── Chat ────────────────────────────────────────────────────

@router.post("/chat")
async def dify_chat(
    request: DifyChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Send a chat message to a Dify app (SSE streaming)."""
    dify = get_dify_client()

    async def event_stream():
        full = ""
        try:
            async for token in dify.chat_stream(
                query=request.query,
                user=current_user.id,
                conversation_id=request.conversation_id,
                inputs=request.inputs,
            ):
                full += token
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': full}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/blocking")
async def dify_chat_blocking(
    request: DifyChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Send a chat message to a Dify app (non-streaming)."""
    dify = get_dify_client()
    result = await dify.chat_blocking(
        query=request.query,
        user=current_user.id,
        conversation_id=request.conversation_id,
        inputs=request.inputs,
    )
    return result


# ── Workflow ────────────────────────────────────────────────

@router.post("/workflows/run")
async def run_workflow(
    request: DifyWorkflowRequest,
    current_user: User = Depends(get_current_user),
):
    """Execute a Dify workflow."""
    dify = get_dify_client()
    result = await dify.run_workflow(
        inputs=request.inputs,
        user=current_user.id,
        response_mode=request.response_mode,
    )
    return result


# ── Knowledge Base ──────────────────────────────────────────

@router.get("/datasets")
async def list_datasets(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_role("admin")),
):
    """List Dify knowledge base datasets."""
    dify = get_dify_client()
    return await dify.list_datasets(page=page, limit=limit)


@router.post("/datasets/upload")
async def upload_to_dataset(
    request: DifyUploadRequest,
    current_user: User = Depends(require_role("admin")),
):
    """Upload a document to a Dify dataset."""
    dify = get_dify_client()
    result = await dify.upload_document(
        dataset_id=request.dataset_id,
        file_path=request.file_path,
        file_name=request.file_name,
        indexing_technique=request.indexing_technique,
    )
    return result


@router.get("/datasets/{dataset_id}/documents/{document_id}/status")
async def get_document_status(
    dataset_id: str,
    document_id: str,
    current_user: User = Depends(require_role("admin")),
):
    """Check document indexing status in Dify."""
    dify = get_dify_client()
    return await dify.get_document_status(dataset_id, document_id)


# ── Image Generation ────────────────────────────────────────

@router.post("/generate-image")
async def generate_image(
    request: DifyImageRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate an image via Dify's configured image generation tool."""
    dify = get_dify_client()
    result = await dify.generate_image(
        prompt=request.prompt,
        size=request.size,
        n=request.n,
        user=current_user.id,
    )
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result
