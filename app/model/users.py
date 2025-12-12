from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=15)
    tags: List[str] = []


class UserResponse(BaseModel):
    username: str
    tags: List[str]
    created_at: datetime


class CreateUserResponse(BaseModel):
    user: UserResponse
    processing_time: float
