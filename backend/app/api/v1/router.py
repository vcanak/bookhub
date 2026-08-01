"""Aggregate router for API v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, posts, tasks, uploads, users

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
