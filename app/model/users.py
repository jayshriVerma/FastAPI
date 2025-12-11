from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=15)
    tags: List[str] = []


class UserResponse(BaseModel):
    username: str
    tags: List[str]
    created_at: float = datetime.now(timezone.utc).isoformat()


class CreateUserResponse(BaseModel):
    user: UserResponse
    processing_time: float
