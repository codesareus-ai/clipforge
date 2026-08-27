"""Persistent job store backed by SQLite (via settings.DATABASE_URL).

Keeps the same `jobs.get(job_id)` / `jobs[job_id] = ...` interface the rest of
the app uses, so worker.py / routes.py needed minimal changes. One row per job;
JobStatus is serialized to JSON. Swap for Postgres by pointing DATABASE_URL at
it — the sqlite3 calls below are the only DB-specific bits.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from app.config import get_settings
from app.models import JobStatus

settings = get_settings()


def _path() -> str:
    # Accept sqlite:///path or a bare path.
    m = re.match(r"sqlite:///(.+)", settings.DATABASE_URL)
    p = m.group(1) if m else settings.DATABASE_URL
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_path())
    c.execute(
        """CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            state  TEXT,
            data   TEXT
        )"""
    )
    return c


class JobStore:
    """dict-like wrapper so `jobs[job_id] = JobStatus(...)` still works."""

    def get(self, job_id: str) -> JobStatus | None:
        with _conn() as c:
            row = c.execute(
                "SELECT data FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
        if not row:
            return None
        d = json.loads(row[0])
        return JobStatus(**d)

    def __setitem__(self, job_id: str, job: JobStatus) -> None:
        d = job.model_dump()
        with _conn() as c:
            c.execute(
                "REPLACE INTO jobs(job_id, state, data) VALUES (?, ?, ?)",
                (job_id, job.state, json.dumps(d)),
            )

    def __getitem__(self, job_id: str) -> JobStatus:
        j = self.get(job_id)
        if j is None:
            raise KeyError(job_id)
        return j


jobs = JobStore()
