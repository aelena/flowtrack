"""Thin async client over the FlowTrack REST API.

Deliberately thin. The MCP server's job is to expose FlowTrack's *questions*,
not to mirror its endpoints, so the shaping happens in server.py and this file
stays a transport.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_URL = "http://localhost:7028"


class FlowTrackError(RuntimeError):
    pass


class FlowTrackClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.environ.get("FLOWTRACK_API_URL", DEFAULT_URL)).rstrip("/")
        self.api_key = api_key or os.environ.get("FLOWTRACK_API_KEY", "")
        if not self.api_key:
            raise FlowTrackError(
                "FLOWTRACK_API_KEY is not set. It must match the API_KEY in FlowTrack's .env."
            )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = {"X-API-Key": self.api_key}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as http:
            try:
                resp = await http.request(method, path, headers=headers, **kwargs)
            except httpx.ConnectError as exc:
                raise FlowTrackError(
                    f"Cannot reach FlowTrack at {self.base_url}. Is `docker compose up` running?"
                ) from exc

        if resp.status_code == 401:
            raise FlowTrackError("FlowTrack rejected the API key (401).")
        if resp.status_code >= 400:
            detail = ""
            try:
                detail = resp.json().get("detail", "")
            except Exception:
                detail = resp.text[:200]
            raise FlowTrackError(f"{method} {path} failed ({resp.status_code}): {detail}")

        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # --- Reads ---------------------------------------------------------------

    async def list_projects(self, *, archived: bool = False, **params: Any) -> list[dict]:
        params = {k: v for k, v in params.items() if v is not None}
        params["archived"] = archived
        return await self._request("GET", "/api/projects/", params=params)

    async def get_project(self, project_id: str) -> dict:
        return await self._request("GET", f"/api/projects/{project_id}")

    async def list_tasks(self, project_id: str) -> list[dict]:
        return await self._request("GET", f"/api/projects/{project_id}/tasks/")

    async def list_notes(self, *, project_id: str | None = None) -> list[dict]:
        params = {"project_id": project_id} if project_id else {}
        return await self._request("GET", "/api/notes/", params=params)

    async def list_areas(self) -> list[dict]:
        return await self._request("GET", "/api/areas/")

    # --- Writes --------------------------------------------------------------

    async def create_tasks(self, project_id: str, content: str) -> list[dict]:
        return await self._request("POST", f"/api/projects/{project_id}/tasks/", json={"content": content})

    async def update_task(self, project_id: str, task_id: str, **fields: Any) -> dict:
        return await self._request("PUT", f"/api/projects/{project_id}/tasks/{task_id}", json=fields)

    async def create_note(self, **fields: Any) -> dict:
        return await self._request("POST", "/api/notes/", json=fields)

    async def update_project(self, project_id: str, **fields: Any) -> dict:
        fields = {k: v for k, v in fields.items() if v is not None}
        return await self._request("PUT", f"/api/projects/{project_id}", json=fields)
