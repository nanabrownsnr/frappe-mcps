from fastapi import Depends, Header, HTTPException, status

from core.authentication.auth_token import verify_access_token
from schemas.token import TokenData


async def get_bearer_token(authorization: str | None = Header(default=None)) -> str | None:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth header")
    return authorization.split(" ", 1)[1].strip()


async def get_current_user(token: str | None = Depends(get_bearer_token)) -> TokenData | None:
    if not token:
        return None
    return await verify_access_token(token)
