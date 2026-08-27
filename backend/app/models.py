"""Pydantic schemas for API + internal data."""
from __future__ import annotations

from pydantic import BaseModel


class ClipMoment(BaseModel):
    start: float
    end: float
    score: float
    hook: str
    reason: str


class JobCreate(BaseModel):
    url: str
    live: bool = False
    top_n: int = 7
    platforms: list[str] = ["tiktok", "instagram", "youtube"]


class PublishResult(BaseModel):
    platform: str
    ok: bool
    publish_id: str | None = None
    id: str | None = None
    error: str | None = None


class JobStatus(BaseModel):
    job_id: str
    state: str  # queued | running | done | error
    moments: list[ClipMoment] = []
    publish_results: list[PublishResult] = []
    error: str | None = None
