from __future__ import annotations

import asyncio
import contextlib
import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


class LicenseWatcher:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self):
        if self._task or not settings.LICENSE_SERVER_BASE_URL or not settings.LICENSE_KEY:
            return
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._task = None

    async def _run(self):
        while not self._stop_event.is_set():
            try:
                await self._validate()
            except Exception:
                logger.exception("License validation failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=60 * 60 * 24)
            except asyncio.TimeoutError:
                continue

    async def _validate(self):
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.LICENSE_SERVER_BASE_URL.rstrip('/')}/{settings.LICENSE_SERVER_ACTIVATION_ENDPOINT.lstrip('/')}",
                json={"license_key": settings.LICENSE_KEY, "service_id": settings.SERVICE_ID},
            )
            response.raise_for_status()
            logger.info("License validation succeeded")


license_watcher = LicenseWatcher()
