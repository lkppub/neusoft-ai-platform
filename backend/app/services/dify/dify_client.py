"""Dify low-code platform integration client.

Supports:
- Chat application (streaming / blocking)
- Workflow execution
- Knowledge base management (upload / query / status)
- Text-to-image generation via Dify tools
"""

import json
import logging
from typing import AsyncGenerator, Optional, Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class DifyClient:
    """Async HTTP client for Dify API v1."""

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        timeout: float = 120.0,
    ):
        self.base_url = (base_url or settings.DIFY_API_URL).rstrip("/")
        self.api_key = api_key or settings.DIFY_API_KEY
        self.timeout = timeout

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "app-your-dify-key")

    # ── Chat Application ─────────────────────────────────────

    async def chat_blocking(
        self,
        query: str,
        user: str = "default",
        conversation_id: str = "",
        inputs: Optional[dict] = None,
        response_mode: str = "blocking",
    ) -> dict:
        """Send a chat message to a Dify app (non-streaming)."""
        if not self.is_configured:
            return {"answer": "[Dify not configured]", "conversation_id": ""}

        payload = {
            "inputs": inputs or {},
            "query": query,
            "user": user,
            "response_mode": response_mode,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat-messages",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def chat_stream(
        self,
        query: str,
        user: str = "default",
        conversation_id: str = "",
        inputs: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        """Send a chat message to a Dify app (SSE streaming)."""
        if not self.is_configured:
            yield "[Dify not configured]"
            return

        payload = {
            "inputs": inputs or {},
            "query": query,
            "user": user,
            "response_mode": "streaming",
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat-messages",
                headers=self._headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            event = data.get("event", "")
                            if event == "message" or event == "agent_message":
                                yield data.get("answer", "")
                            elif event == "message_end":
                                break
                            elif event == "error":
                                logger.error("Dify stream error: %s", data)
                                yield f"[Error: {data.get('message', 'unknown')}]"
                                break
                        except json.JSONDecodeError:
                            continue

    # ── Workflow Execution ──────────────────────────────────

    async def run_workflow(
        self,
        inputs: dict,
        user: str = "default",
        response_mode: str = "blocking",
    ) -> dict:
        """Execute a Dify workflow."""
        if not self.is_configured:
            return {"data": {"outputs": {}}, "error": "Dify not configured"}

        payload = {
            "inputs": inputs,
            "user": user,
            "response_mode": response_mode,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/workflows/run",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    # ── Knowledge Base ──────────────────────────────────────

    async def list_datasets(self, page: int = 1, limit: int = 20) -> dict:
        """List knowledge base datasets."""
        if not self.is_configured:
            return {"data": [], "has_more": False}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/datasets",
                headers=self._headers,
                params={"page": page, "limit": limit},
            )
            resp.raise_for_status()
            return resp.json()

    async def upload_document(
        self,
        dataset_id: str,
        file_path: str,
        file_name: str,
        indexing_technique: str = "high_quality",
        process_rule: Optional[dict] = None,
    ) -> dict:
        """Upload a document to a Dify dataset."""
        if not self.is_configured:
            return {"document": {"id": ""}, "error": "Dify not configured"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, "application/octet-stream")}
                data = {
                    "indexing_technique": indexing_technique,
                    "process_rule": json.dumps(process_rule or {"mode": "automatic"}),
                }
                resp = await client.post(
                    f"{self.base_url}/datasets/{dataset_id}/document/create-by-file",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    data=data,
                    files=files,
                )
                resp.raise_for_status()
                return resp.json()

    async def get_document_status(self, dataset_id: str, document_id: str) -> dict:
        """Check document indexing status."""
        if not self.is_configured:
            return {"document": {"indexing_status": "unknown"}}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/datasets/{dataset_id}/documents/{document_id}/indexing-status",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    # ── Text-to-Image ───────────────────────────────────────

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1,
        user: str = "default",
    ) -> dict:
        """Generate an image via Dify's configured image generation tool.

        Note: This requires an image generation tool node in the Dify workflow.
        Uses a generic workflow pattern.
        """
        if not self.is_configured:
            return {"url": "", "error": "Dify not configured"}

        result = await self.run_workflow(
            inputs={
                "prompt": prompt,
                "size": size,
                "num_images": n,
            },
            user=user,
        )
        return result.get("data", {}).get("outputs", {})


# Singleton
_dify_client: Optional[DifyClient] = None


def get_dify_client() -> DifyClient:
    global _dify_client
    if _dify_client is None:
        _dify_client = DifyClient()
    return _dify_client
