"""Retry-bounded persistence bridge from the AI service to the core CRM API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ai.config.logging import get_logger


class CorePersistenceClient:
    """Persist AI session events in the SQL-backed core service.

    ``external_lead_id`` is intentionally treated as the core call identifier.
    Sessions without it remain useful for isolated AI testing and do not attempt
    cross-service writes.
    """

    def __init__(
        self,
        *,
        base_url: str | None,
        internal_api_key: str | None,
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        self._base_url = base_url.rstrip("/") if base_url else None
        self._headers = {"X-Internal-API-Key": internal_api_key} if internal_api_key else {}
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=timeout_seconds)
        self._logger = get_logger("core_persistence")

    @property
    def enabled(self) -> bool:
        return self._base_url is not None

    async def close(self) -> None:
        await self._client.aclose()

    async def _post(self, call_id: str | None, path: str, payload: dict[str, Any]) -> bool:
        if not self._base_url or not call_id:
            return True
        url = f"{self._base_url}/api/internal/calls/{call_id}/{path.lstrip('/')}"
        last_error: str | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(url, json=payload, headers=self._headers)
                response.raise_for_status()
                return True
            except (httpx.HTTPError, ValueError) as exc:
                last_error = type(exc).__name__
                if attempt < self._max_retries:
                    await asyncio.sleep(min(0.2 * (2**attempt), 1.0))
        self._logger.error(
            "core_persistence_failed",
            path=path,
            call_id=call_id,
            error_type=last_error,
        )
        return False

    async def link_session(self, call_id: str | None, session_id: str) -> bool:
        return await self._post(call_id, "session", {"ai_session_id": session_id})

    async def fetch_session_context(self, call_id: str | None) -> dict[str, Any] | None:
        if not self._base_url or not call_id:
            return None
        try:
            response = await self._client.get(
                f"{self._base_url}/api/internal/calls/{call_id}/context",
                headers=self._headers,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            return data if isinstance(data, dict) else None
        except (httpx.HTTPError, ValueError) as exc:
            self._logger.warning(
                "core_context_recovery_unavailable",
                call_id=call_id,
                error_type=type(exc).__name__,
            )
            return None

    async def persist_transcript(
        self, call_id: str | None, segments: list[dict[str, Any]]
    ) -> bool:
        return await self._post(call_id, "transcripts", {"segments": segments})

    async def persist_result(self, call_id: str | None, result: dict[str, Any]) -> bool:
        return await self._post(call_id, "copilot-results", {"result": result})

    async def persist_crm_summary(
        self,
        call_id: str | None,
        summary: dict[str, Any],
        *,
        requires_human_review: bool,
    ) -> bool:
        return await self._post(
            call_id,
            "crm-summary",
            {
                "crm_summary": summary,
                "requires_human_review": requires_human_review,
            },
        )

    async def register_knowledge_document(
        self,
        *,
        title: str,
        source: str,
        version: str | None,
        chunk_count: int,
        content_sha256: str,
    ) -> bool:
        if not self._base_url:
            return True
        url = f"{self._base_url}/api/knowledge-documents"
        try:
            response = await self._client.post(
                url,
                params={
                    "title": title,
                    "source": source,
                    "version": version,
                    "chunk_count": chunk_count,
                    "content_sha256": content_sha256,
                },
                headers=self._headers,
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            self._logger.error(
                "knowledge_catalog_persistence_failed", error_type=type(exc).__name__
            )
            return False

    async def fetch_approved_products(self) -> list[dict[str, Any]]:
        if not self._base_url:
            return []
        try:
            response = await self._client.get(
                f"{self._base_url}/api/internal/products", headers=self._headers
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", []) if isinstance(payload, dict) else []
            return [item for item in data if isinstance(item, dict)]
        except (httpx.HTTPError, ValueError) as exc:
            self._logger.warning(
                "core_product_sync_unavailable", error_type=type(exc).__name__
            )
            return []


__all__ = ["CorePersistenceClient"]
