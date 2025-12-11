import asyncio
import time
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException, Path

from app.model.users import CreateUserRequest, CreateUserResponse, UserResponse

app = FastAPI()

# Simulated in-memory DB
users_db: Dict[str, dict] = {}
db_lock = asyncio.Lock()


def get_request_context():
    return time.monotonic()


@app.post("/users", response_model= CreateUserResponse)
async def create_user(payload: CreateUserRequest, start_time=Depends(get_request_context)):
    await asyncio.sleep(0.2)
    async with db_lock:
        if payload.username in users_db:
            raise HTTPException(status_code=400, detail="User already exists")

        user  = {
            "username": payload.username,
            "tags": payload.tags,
            "created_at": time.monotonic()
        }
        users_db[payload.username] = user

    return {
        "user": user,
        "processing_time": time.monotonic() - start_time
    }


@app.get("/users/{username}", response_model= UserResponse)
async def get_user(username: str = Path(min_length=3, max_length=15)):
    await asyncio.sleep(0.1)
    async with db_lock:
        user = users_db.get(username)
        if not user:
            raise HTTPException(status_code=404, detail="Not found")

    return user


@app.post("/users/{username}/tags", response_model= UserResponse)
async def add_tag(username: str, tag: str):
    async with db_lock:
        user = users_db.get(username)
        if not user:
            raise HTTPException(status_code=404, detail="Not found")

        user["tags"].append(tag)

        return user
