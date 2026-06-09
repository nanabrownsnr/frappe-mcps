import asyncio
from datetime import datetime, timedelta
from logging import getLogger

import httpx
from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt

from core.config import settings
from schemas.token import TokenData

logger = getLogger(__name__)

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


class CachedJWKSHelper:
    jwks: list[dict] | None = None
    last_updated: datetime | None = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_jwks(cls) -> list[dict]:
        async with cls._lock:
            if (
                cls.jwks is not None
                and cls.last_updated is not None
                and datetime.now()
                < cls.last_updated + timedelta(seconds=settings.ACCOUNT_SERVICE_JWKS_CACHE_TTL)
            ):
                return cls.jwks

            if not settings.ACCOUNT_SERVICE_URL:
                raise credentials_exception

            jwks_url = (
                f"{settings.ACCOUNT_SERVICE_URL.rstrip('/')}"
                f"/{settings.ACCOUNT_SERVICE_JWKS_ENDPOINT.lstrip('/')}"
            )

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
                cls.jwks = response.json()["keys"]
                cls.last_updated = datetime.now()
                return cls.jwks

    @classmethod
    async def get_public_key(cls, kid: str) -> dict:
        jwks = await cls.get_jwks()
        for jwk in jwks:
            if jwk["kid"] == kid:
                return jwk
        raise credentials_exception


async def verify_access_token(token: str, audience: str | None = None) -> TokenData:
    try:
        header = jwt.get_unverified_header(token)
        key = await CachedJWKSHelper.get_public_key(header["kid"])
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=audience or settings.SERVICE_ID,
        )
        return TokenData(
            id=str(payload.get("id", "")),
            email=str(payload.get("sub", "")),
            role=str(payload.get("role", "")),
            type=str(payload.get("type", "")),
            client_id=str(payload.get("client_id", "")),
            username=str(payload.get("username", "")),
            access_token=token,
        )
    except ExpiredSignatureError as exc:
        logger.warning("Expired access token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except JWTError as exc:
        logger.warning("Invalid access token")
        raise credentials_exception from exc
