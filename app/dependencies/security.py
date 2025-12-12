import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

load_dotenv()

VALID_KEYS = [
    k.strip()
    for k in os.getenv("VALID_API_KEYS", "secret-key-1,secret-key-2").split(",")
]

api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: str = Depends(api_key_scheme)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API Key"
        )
    if api_key not in VALID_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key"
        )
    return api_key
