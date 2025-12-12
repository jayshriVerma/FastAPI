import asyncio
import os
import time
from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Path, Request

from app.dependencies.security import get_api_key
from app.model.users import CreateUserRequest, CreateUserResponse, UserResponse
from app.repositories.interface import UserRepository
from app.repositories.user_repo import RedisUserRepository

load_dotenv()
router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL is None:
    raise RuntimeError("REDIS_URL environment variable is missing!")

repo = RedisUserRepository(redis_url=REDIS_URL)


def get_user_repo() -> UserRepository:
    return repo


def get_request_context():
    return time.monotonic()


@router.get("/health")
async def health(request: Request):
    redis = request.app.state.redis
    await redis.ping()
    return {"status": "ok"}


@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    payload: CreateUserRequest,
    start_time=Depends(get_request_context),
    repo: UserRepository = Depends(get_user_repo),
):
    await asyncio.sleep(0.2)

    user = {
        "username": payload.username,
        "tags": payload.tags,
        "created_at": time.monotonic(),
    }
    try:
        await repo.create_user(user)
    except ValueError:
        raise HTTPException(status_code=400, detail="User already exists")

    return {"user": user, "processing_time": time.monotonic() - start_time}


@router.get("/users")
async def list_users(
    repo: UserRepository = Depends(get_user_repo), api_key: str = Depends(get_api_key)
):
    return {"users": await repo.list_users()}


@router.get("/users/{username}", response_model=UserResponse)
async def get_user(
    username: Annotated[str, Path(min_length=3, max_length=15)],
    repo: UserRepository = Depends(get_user_repo),
    api_key: str = Depends(get_api_key),
):

    user = await repo.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="Not found")

    await asyncio.sleep(0.1)
    return user


@router.post("/users/{username}/tags", response_model=UserResponse)
async def add_tag(
    username: str, tag: str, repo: UserRepository = Depends(get_user_repo)
):
    try:
        user = await repo.add_tag(username, tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")
    return user
