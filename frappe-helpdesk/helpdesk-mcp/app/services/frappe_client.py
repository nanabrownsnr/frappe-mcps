from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import HTTPException

from core.config import settings


class FrappeApiClient:
    async def get_doc(self, doctype: str, name: str) -> dict[str, Any]:
        response = await self._request("GET", f"/api/resource/{doctype}/{name}")
        return response.json().get("data", {})

    async def list_docs(
        self,
        doctype: str,
        *,
        fields: list[str] | None = None,
        filters: list | dict | None = None,
        limit_page_length: int = 20,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit_page_length": limit_page_length}
        if fields:
            params["fields"] = json.dumps(fields)
        if filters:
            params["filters"] = json.dumps(filters)
        if order_by:
            params["order_by"] = order_by
        response = await self._request("GET", f"/api/resource/{doctype}", params=params)
        return response.json().get("data", [])

    async def create_doc(self, doctype: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("POST", f"/api/resource/{doctype}", json={"doctype": doctype, **payload})
        return response.json().get("data", {})

    async def update_doc(self, doctype: str, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("PUT", f"/api/resource/{doctype}/{name}", json=payload)
        return response.json().get("data", {})

    async def call_method(self, method: str, payload: dict[str, Any] | None = None) -> Any:
        response = await self._request("POST", f"/api/method/{method}", json=payload or {})
        data = response.json()
        return data.get("message", data)

    async def count(self, doctype: str, filters: list | dict | None = None) -> int:
        rows = await self.list_docs(
            doctype,
            fields=["count(name) as count"],
            filters=filters,
            limit_page_length=1,
        )
        return int((rows[0] if rows else {}).get("count") or 0)

    async def find_one(
        self,
        doctype: str,
        *,
        filters: list | dict,
        fields: list[str] | None = None,
    ) -> dict[str, Any] | None:
        rows = await self.list_docs(
            doctype,
            fields=fields or ["name"],
            filters=filters,
            limit_page_length=1,
        )
        return rows[0] if rows else None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        headers = {
            "Accept": "application/json",
            "Host": settings.FRAPPE_SITE_NAME,
            "X-Frappe-Site-Name": settings.FRAPPE_SITE_NAME,
        }
        async with httpx.AsyncClient(
            base_url=settings.FRAPPE_API_URL.rstrip("/"),
            timeout=30.0,
            verify=bool(settings.FRAPPE_VERIFY_SSL),
            headers=headers,
        ) as client:
            if settings.FRAPPE_API_KEY and settings.FRAPPE_API_SECRET:
                client.headers["Authorization"] = f"token {settings.FRAPPE_API_KEY}:{settings.FRAPPE_API_SECRET}"
            else:
                try:
                    login = await client.post(
                        "/api/method/login",
                        data={"usr": settings.FRAPPE_USERNAME, "pwd": settings.FRAPPE_PASSWORD},
                    )
                    login.raise_for_status()
                except httpx.ConnectError as exc:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Frappe backend is not reachable at {settings.FRAPPE_API_URL}. It may still be starting.",
                    ) from exc
                except httpx.TimeoutException as exc:
                    raise HTTPException(status_code=504, detail="Frappe backend timed out during login.") from exc
                except httpx.HTTPStatusError as exc:
                    raise HTTPException(status_code=exc.response.status_code, detail=self._error_detail(exc.response)) from exc

            try:
                response = await client.request(method, path, params=params, json=json)
                response.raise_for_status()
                return response
            except httpx.ConnectError as exc:
                raise HTTPException(
                    status_code=503,
                    detail=f"Frappe backend is not reachable at {settings.FRAPPE_API_URL}. It may still be starting.",
                ) from exc
            except httpx.TimeoutException as exc:
                raise HTTPException(status_code=504, detail="Frappe backend request timed out.") from exc
            except httpx.HTTPStatusError as exc:
                raise HTTPException(status_code=exc.response.status_code, detail=self._error_detail(exc.response)) from exc

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return response.text or f"Frappe returned HTTP {response.status_code}."
        server_messages = data.get("_server_messages")
        if server_messages:
            try:
                messages = json.loads(server_messages)
                if messages:
                    first_message = messages[0]
                    if isinstance(first_message, str):
                        parsed_message = json.loads(first_message)
                        if isinstance(parsed_message, dict):
                            return parsed_message.get("message") or str(parsed_message)
                        return str(parsed_message)
                    return str(first_message)
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        return data.get("exception") or data.get("exc") or data.get("message") or str(data)


def get_frappe_client() -> FrappeApiClient:
    return FrappeApiClient()
