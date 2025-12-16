from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from settings import settings

VALID_KEYS = settings.VALID_API_KEYS

api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: str = Depends(api_key_scheme)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API Key"
        )
    role = VALID_KEYS.get(api_key)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key"
        )
    return role


def require_admin(role: str = Depends(get_api_key)):
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required",)