from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from core.config import settings
from core.platfom_integration_client import FrappeCredentials, PlatformIntegrationClient

logger = logging.getLogger(__name__)


@dataclass
class FrappeRequestContext:
    credentials: FrappeCredentials
    fallback_credentials: FrappeCredentials


class FrappeApiClient:
    def __init__(self, request_context: FrappeRequestContext):
        self.request_context = request_context

    @classmethod
    async def from_platform_client(cls, platform_client: PlatformIntegrationClient) -> "FrappeApiClient":
        credentials = await platform_client.get_frappe_credentials()
        fallback_credentials = platform_client.get_env_fallback_credentials()
        return cls(FrappeRequestContext(credentials=credentials, fallback_credentials=fallback_credentials))

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
        body = {"doctype": doctype, **payload}
        response = await self._request("POST", f"/api/resource/{doctype}", json=body)
        return response.json().get("data", {})

    async def update_doc(self, doctype: str, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._request("PUT", f"/api/resource/{doctype}/{name}", json=payload)
        return response.json().get("data", {})

    async def call_method(self, method: str, *, params: dict[str, Any] | None = None) -> Any:
        response = await self._request("POST", f"/api/method/{method}", json=params or {})
        payload = response.json()
        return payload.get("message", payload)

    async def get_count(self, doctype: str, filters: list | dict | None = None) -> int:
        payload: dict[str, Any] = {"doctype": doctype}
        if filters:
            payload["filters"] = filters
        result = await self.call_method("frappe.client.get_count", params=payload)
        return int(result or 0)

    async def get_aggregate(self, doctype: str, expression: str, filters: list | dict | None = None) -> float:
        rows = await self.list_docs(
            doctype,
            fields=[expression],
            filters=filters,
            limit_page_length=1,
        )
        if not rows:
            return 0.0
        row = rows[0]
        value = next(iter(row.values()), 0)
        return float(value or 0)

    async def run_report(self, report_name: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/api/method/frappe.desk.query_report.run",
            json={"report_name": report_name, "filters": filters or {}},
        )
        return response.json().get("message", {})

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        response = await self._request_once(
            method,
            path,
            credentials=self.request_context.credentials,
            params=params,
            json=json,
        )
        if (
            response.status_code in (401, 403)
            and self.request_context.credentials.source == "platform"
            and self.request_context.fallback_credentials.api_key
            and self.request_context.fallback_credentials.api_secret
        ):
            logger.warning("Retrying Frappe request with env fallback credentials")
            response = await self._request_once(
                method,
                path,
                credentials=self.request_context.fallback_credentials,
                params=params,
                json=json,
            )

        response.raise_for_status()
        return response

    async def _request_once(
        self,
        method: str,
        path: str,
        *,
        credentials: FrappeCredentials,
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
            if credentials.api_key and credentials.api_secret:
                client.headers["Authorization"] = (
                    f"token {credentials.api_key}:{credentials.api_secret}"
                )
            elif credentials.username and credentials.password:
                login_response = await client.post(
                    "/api/method/login",
                    data={"usr": credentials.username, "pwd": credentials.password},
                )
                login_response.raise_for_status()
            return await client.request(method, path, params=params, json=json)
