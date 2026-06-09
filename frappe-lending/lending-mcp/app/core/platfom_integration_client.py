from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from fastapi import Depends, Header

from core.authentication.auth_middleware import get_current_user
from core.config import settings
from schemas.token import TokenData

logger = logging.getLogger(__name__)


@dataclass
class FrappeCredentials:
    api_key: str
    api_secret: str
    username: str | None = None
    password: str | None = None
    source: str = "env"


class PlatformIntegrationClient:
    def __init__(self, authorization: str | None, persona_id: str | None):
        self.authorization = authorization
        self.persona_id = persona_id

    async def get_frappe_credentials(self) -> FrappeCredentials:
        if self.authorization and self.persona_id and settings.PLATFORM_INT_URL:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(
                        f"{settings.PLATFORM_INT_URL.rstrip('/')}/api/v1/integrations/credential",
                        params={"service": settings.PLATFORM_KEY_SERVICE_NAME},
                        headers={
                            "Authorization": self.authorization,
                            settings.PERSONA_ID_HEADER: self.persona_id,
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    data = payload.get("data") or payload
                    api_key = data.get("api_key") or data.get("key")
                    api_secret = data.get("api_secret") or data.get("secret")
                    if api_key and api_secret:
                        return FrappeCredentials(
                            api_key=api_key,
                            api_secret=api_secret,
                            username=data.get("username"),
                            password=data.get("password"),
                            source="platform",
                        )
            except Exception:
                logger.exception("Failed to fetch Frappe credentials from platform integration")

        return FrappeCredentials(
            api_key=settings.FRAPPE_API_KEY,
            api_secret=settings.FRAPPE_API_SECRET,
            username=settings.FRAPPE_USERNAME,
            password=settings.FRAPPE_PASSWORD,
            source="env",
        )

    def get_env_fallback_credentials(self) -> FrappeCredentials:
        return FrappeCredentials(
            api_key=settings.FRAPPE_API_KEY,
            api_secret=settings.FRAPPE_API_SECRET,
            username=settings.FRAPPE_USERNAME,
            password=settings.FRAPPE_PASSWORD,
            source="env",
        )


async def get_platform_client(
    user: TokenData | None = Depends(get_current_user),
    authorization: str | None = Header(default=None),
    persona_id: str | None = Header(default=None, alias=settings.PERSONA_ID_HEADER),
) -> PlatformIntegrationClient:
    bearer = authorization
    if user and not bearer:
        bearer = f"Bearer {user.access_token}"
    return PlatformIntegrationClient(authorization=bearer, persona_id=persona_id)
