import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, Path, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from settings import settings

from app.dependencies.security import get_api_key, require_admin
from app.model.users import (
    CreateUserRequest,
    CreateUserResponse,
    DeletedCountResponse,
    TagsParam,
    UsernameParam,
    UserResponse,
)
from app.repositories.interface import UserRepository
from app.repositories.user_repo import RedisUserRepository

health_router = APIRouter()
router = APIRouter(dependencies=[Depends(get_api_key)])

REDIS_URL = settings.redis_url
repo = RedisUserRepository(redis_url=REDIS_URL)


def get_user_repo() -> UserRepository:
    return repo


def get_request_context():
    return time.monotonic()


@health_router.get("/health")
async def health(request: Request):
    redis = request.app.state.redis
    await redis.ping()
    return {"status": "ok"}


@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    payload: CreateUserRequest,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    start_time=Depends(get_request_context),
    repo: UserRepository = Depends(get_user_repo),
):
    idemp_key = request.headers.get("Idempotency-Key")
    api_key = request.headers.get("X-API-Key")

    if not idemp_key:
        raise HTTPException(400, "Idempotency-Key required")

    redis = request.app.state.redis
    cache_key = f"idemp:{api_key}:{idempotency_key}:POST:/users"
    print(cache_key)
    # check for Idempotency FIRST
    cached = await redis.get(cache_key)
    print(cached)
    if cached:
        cached_data = json.loads(cached)
        return JSONResponse(
            status_code=cached_data["status"],
            content=cached_data["body"],
        )

    user = await repo.get_user(payload.username)
    if user:
        raise HTTPException(409, "User already exists")
    user = {
       "username": payload.username,
        "tags": payload.tags,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await repo.create_user(user)
    response ={"user": user, "processing_time": time.monotonic() - start_time}
    # cache only valid responses
    validated_response = CreateUserResponse(**response)
    encoded = jsonable_encoder(validated_response)
    await redis.setex(
        cache_key,
        300,  # 5 minutes
        json.dumps({"status": 201, "body": encoded}),
    )
    return validated_response


@router.get("/users")
async def list_users(repo: UserRepository = Depends(get_user_repo)):
    return {"users": await repo.list_users()}


@router.get("/users/{username}", response_model=CreateUserResponse)
async def get_user(
    username: Annotated[str, Path(min_length=3, max_length=15)],
    repo: UserRepository = Depends(get_user_repo),
    start_time=Depends(get_request_context)
):
    data = UsernameParam(username=username)
    user = await repo.get_user(data.username)
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    await repo.touch_user(data.username)
    await asyncio.sleep(0.1)
    response ={"user": user, "processing_time": time.monotonic() - start_time}
    return response


@router.post("/users/{username}/tags", response_model=UserResponse)
async def add_tag(
    username: str, payload: TagsParam, repo: UserRepository = Depends(get_user_repo)
):
    data = UsernameParam(username=username)
    user = await repo.get_user(data.username)
    if user is None:
        raise HTTPException(status_code=404, detail="Not found")

    candidate_tags = user["tags"] + payload.tags
    try:
        validated = TagsParam(tags=candidate_tags)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()[0]["msg"])
    await repo.add_tag(data.username, validated.tags)
    await repo.touch_user(data.username)
    user = await repo.get_user(data.username)
    return user


@router.delete("/users/{username}", status_code=204)
async def delete_user(username: str, repo: UserRepository = Depends(get_user_repo)):
    data = UsernameParam(username=username)
    try:
        await repo.delete_user(data.username)
    except KeyError:
        raise HTTPException(status_code=404, detail="Not found")


@router.delete("/admin/users", dependencies=[Depends(require_admin)])
async def delete_all_users(repo: UserRepository = Depends(get_user_repo)):
    await repo.delete_all()


@router.delete(
    "/admin/users/inactive",
    dependencies=[Depends(require_admin)],
    response_model=DeletedCountResponse,
)
async def delete_inactive_users(
    inactive_since: int = Query(..., ge=1, description="Days of inactivity"),
    repo: UserRepository = Depends(get_user_repo),
):
    cutoff_time = time.time() - inactive_since * 86400
    deleted_count = await repo.delete_inactive_users(cutoff_time)
    return {"deleted_count": deleted_count}
