from datetime import datetime
import re
from typing import List

from pydantic import BaseModel, Field, field_validator

class TagsParam(BaseModel):
    tags: List[str]

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        if len(v) > 3:
            raise ValueError("Max 3 tags allowed")
        if len(v) != len(set(v)):
            raise ValueError("Tags must be unique")
        for tag in v:
            if not isinstance(tag, str) or not (1 <= len(tag) <= 10):
                raise ValueError("Each tag must be 1–10 characters")

        return v    

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=15,description="Username (3–20 chars)")
    tags:List[str] = Field(default_factory=list,description="List of tags associated with the user")

    @field_validator("username")
    @classmethod    
    def validate_username(cls, v: str) -> str:
        if not re.fullmatch(r'^[a-zA-Z0-9_]+', v):
            raise ValueError("Username must contain only numbers, letters and underscores.")
        return v.lower()
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        TagsParam(tags=v)  # reuse validation
        return v

class UserResponse(BaseModel):
    username: str
    tags: list[str]
    created_at: datetime


class CreateUserResponse(BaseModel):
    user: UserResponse
    processing_time: float


class UsernameParam(BaseModel):
    username: str

    @field_validator("username")
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.lower()




    