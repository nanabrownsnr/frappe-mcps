from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP

from core.config import settings
from routers.helpdesk import router as helpdesk_router

app = FastAPI(title=settings.APP_TITLE, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(helpdesk_router)

mcp = FastApiMCP(
    app,
    name=settings.APP_TITLE,
    description="MCP tools for Frappe Helpdesk tickets, customers, agents, and knowledge base.",
    include_tags=["mcp-tools"],
)
mcp.mount_http(mount_path="/mcp")


@app.get("/healthz", operation_id="health_check", tags=["internal"])
async def health_check():
    return {"status": "ok"}
