from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP

from api.v1.routers.lending import router as lending_router
from core.config import settings
from mcp_apps import register_dashboard_mcp_app
from system.license_server import license_watcher


@asynccontextmanager
async def lifespan(_: FastAPI):
    await license_watcher.start()
    try:
        yield
    finally:
        await license_watcher.stop()


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.VERSION,
    root_path=settings.ROOT_PATH,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lending_router)

mcp = FastApiMCP(
    app,
    name=settings.APP_TITLE,
    description="MCP tools for Frappe Lending",
    include_tags=["mcp-tools"],
    headers=["authorization", settings.PERSONA_ID_HEADER],
)
register_dashboard_mcp_app(mcp)
mcp.mount_http(mount_path="/mcp")


@app.get("/healthz", operation_id="health_check", tags=["internal"])
async def health_check():
    return {"status": "ok"}
