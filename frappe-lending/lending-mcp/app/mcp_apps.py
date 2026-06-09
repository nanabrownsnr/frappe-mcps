from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi_mcp.server import HTTPRequestInfo
from mcp import types
from mcp.server.lowlevel.helper_types import ReadResourceContents

APP_RESOURCE_URI = "ui://lending/loan-dashboard.html"
APP_RESOURCE_NAME = "Lending Loan Dashboard"
APP_RESOURCE_MIME = "text/html;profile=mcp-app"
TOOL_NAMES = {"dashboard_loan_summary"}
LEGACY_RESOURCE_URI_META_KEY = "ui/resourceUri"
UI_DIST_PATH = Path(__file__).resolve().parent.parent / "ui-dashboard" / "dist" / "mcp-app.html"


def _app_meta(*, visibility: list[str] | None = None) -> dict[str, Any]:
    ui_meta: dict[str, Any] = {"resourceUri": APP_RESOURCE_URI}
    if visibility:
        ui_meta["visibility"] = visibility
    return {"ui": ui_meta, LEGACY_RESOURCE_URI_META_KEY: APP_RESOURCE_URI}


def register_dashboard_mcp_app(mcp) -> None:
    original_tools = list(mcp.tools)
    updated_tools: list[types.Tool] = []
    for tool in original_tools:
        if tool.name not in TOOL_NAMES:
            updated_tools.append(tool)
            continue
        meta = dict(tool.meta or {})
        meta.update(_app_meta(visibility=["model", "app"]))
        updated_tools.append(tool.model_copy(update={"_meta": meta}))

    mcp.tools = updated_tools

    @mcp.server.list_tools()
    async def handle_list_tools():
        return mcp.tools

    @mcp.server.list_resources()
    async def handle_list_resources():
        return [
            types.Resource(
                name=APP_RESOURCE_NAME,
                title=APP_RESOURCE_NAME,
                uri=APP_RESOURCE_URI,
                description="Interactive Lending dashboard for the loan dashboard summary tool.",
                mimeType=APP_RESOURCE_MIME,
            )
        ]

    @mcp.server.read_resource()
    async def handle_read_resource(uri):
        if str(uri) != APP_RESOURCE_URI:
            raise ValueError(f"Unknown resource: {uri}")
        html = UI_DIST_PATH.read_text(encoding="utf-8")
        return [
            ReadResourceContents(
                content=html,
                mime_type=APP_RESOURCE_MIME,
                meta={"ui": {"prefersBorder": True}},
            )
        ]

    @mcp.server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any]):
        if name in TOOL_NAMES:
            payload = await _invoke_json_tool(mcp, name, arguments or {})
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=_render_summary_text(name, payload))],
                structuredContent=payload,
                _meta=_app_meta(),
            )

        request_context = None
        try:
            request_context = mcp.server.request_context
        except LookupError:
            request_context = None
        http_request = getattr(request_context, "request", None) if request_context else None
        http_request_info = None
        if http_request and hasattr(http_request, "method"):
            http_request_info = HTTPRequestInfo(
                method=http_request.method,
                path=http_request.url.path,
                headers=dict(http_request.headers),
                cookies=http_request.cookies,
                query_params=dict(http_request.query_params),
                body=None,
            )

        return await mcp._execute_api_tool(
            client=mcp._http_client,
            tool_name=name,
            arguments=arguments or {},
            operation_map=mcp.operation_map,
            http_request_info=http_request_info,
        )

    for tool in mcp.tools:
        mcp.server._tool_cache[tool.name] = tool


async def _invoke_json_tool(mcp, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    operation = mcp.operation_map[tool_name]
    path = operation["path"]
    method = operation["method"]
    parameters: list[dict[str, Any]] = operation.get("parameters", [])
    args = dict(arguments)

    for param in parameters:
        if param.get("in") == "path" and param.get("name") in args:
            path = path.replace(f"{{{param['name']}}}", str(args.pop(param["name"])))

    query: dict[str, Any] = {}
    headers: dict[str, Any] = {}
    for param in parameters:
        param_name = param.get("name")
        if param_name not in args:
            continue
        if param.get("in") == "query":
            query[param_name] = args.pop(param_name)
        elif param.get("in") == "header":
            headers[param_name] = args.pop(param_name)

    request_context = None
    try:
        request_context = mcp.server.request_context
    except LookupError:
        request_context = None
    http_request = getattr(request_context, "request", None) if request_context else None
    if http_request:
        for header_name, header_value in http_request.headers.items():
            if header_name.lower() in mcp._forward_headers:
                headers[header_name] = header_value

    body = args or None
    response = await mcp._request(mcp._http_client, method, path, query, headers, body)
    if 400 <= response.status_code < 600:
        raise ValueError(f"Error calling {tool_name}: {response.text}")
    return response.json()


def _render_summary_text(tool_name: str, payload: dict[str, Any]) -> str:
    overview_cards = payload.get("overview", {}).get("cards", {})
    outstanding_totals = payload.get("outstanding_totals", {})
    return (
        "Loan dashboard summary: "
        f"{overview_cards.get('active_loans', 0)} active loans, "
        f"{float(overview_cards.get('total_disbursed', 0)):,.2f} disbursed, "
        f"{float(outstanding_totals.get('pending_principal_amount', 0)):,.2f} principal outstanding."
    )
