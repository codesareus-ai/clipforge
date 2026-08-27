"""In-memory job store (swap for Redis/DB in prod)."""
from __future__ import annotations

from app.models import JobStatus

jobs: dict[str, JobStatus] = {}
