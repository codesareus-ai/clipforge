"""API routes: job pipeline + OAuth onboarding callbacks."""
from __future__ import annotations

from fastapi import FastAPI, BackgroundTasks, Request, Query
from fastapi.responses import RedirectResponse

from app.models import JobCreate, JobStatus
from app.worker import execute_pipeline
from app.store import jobs
from app.services.upload import oauth

app = FastAPI(title="ClipForge")

BASE = "http://localhost:3000"  # frontend origin for redirects


@app.post("/jobs", response_model=JobStatus)
def create_job(body: JobCreate, bg: BackgroundTasks):
    job_id = _new_id()
    jobs[job_id] = JobStatus(job_id=job_id, state="queued")
    bg.add_task(execute_pipeline, job_id, body)
    return jobs[job_id]


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    return jobs.get(job_id, JobStatus(job_id=job_id, state="unknown"))


@app.get("/auth/{platform}/login")
def auth_login(platform: str, user_id: str = Query(...)):
    url = oauth.build_authorize_url(platform, user_id, f"{BASE}/auth/{platform}/callback")
    return RedirectResponse(url)


@app.get("/auth/{platform}/callback")
def auth_callback(platform: str, code: str = Query(...), state: str = Query(...)):
    user_id = state.split(":", 1)[0]
    oauth.exchange_code(platform, user_id, code, f"{BASE}/auth/{platform}/callback")
    return RedirectResponse(f"{BASE}/?connected={platform}")


@app.post("/cron/refresh-tokens")
def cron_refresh_tokens(user_id: str = Query("default"), platforms: str = Query("tiktok,instagram,youtube")):
    from app.services.upload import refresh

    return refresh.refresh_user_tokens(user_id, platforms.split(","))


def _new_id() -> str:
    import uuid
    return uuid.uuid4().hex
