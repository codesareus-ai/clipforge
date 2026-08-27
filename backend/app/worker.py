"""Pipeline orchestration. `execute_pipeline` is the shared body used by both
the FastAPI BackgroundTasks fallback and the optional Celery worker."""
from __future__ import annotations

from app.models import JobCreate, JobStatus, ClipMoment, PublishResult
from app.store import jobs
from app.services import ingest, transcribe, rank, render, reframe
from app.services.upload import storage, publish


def execute_pipeline(job_id: str, body) -> None:
    if isinstance(body, dict):
        body = JobCreate(**body)
    job = jobs.get(job_id)
    if not job:
        return
    user_id = job.user_id
    try:
        job.state = "running"
        jobs[job_id] = job  # persist (store is now persistent, not in-memory)
        # 1. Ingest
        src = ingest.download(body.url, "downloads", live=body.live)
        # 2. Transcribe (word-level)
        segs = transcribe.transcribe(src)
        # 3. Rank viral moments
        moments = rank.rank_moments(segs, top_n=body.top_n)
        results: list[PublishResult] = []
        for idx, m in enumerate(moments):
            cut_path = render.cut(src, m.start, m.end, f"outputs/{job_id}_raw_{idx}.mp4")
            # Word-level captions for this moment window
            caps = [
                {"text": w.text.strip(), "start": round(w.start - m.start, 2),
                 "end": round(w.end - m.start, 2)}
                for s in segs for w in s.words
                if m.start <= w.start <= m.end
            ]
            # 4. Smooth face-track reframe -> 9:16 keyframes
            keyframes = reframe.compute_reframe(cut_path)
            # 5. Render captioned + reframed vertical clip via Remotion
            final_path = render.render_captioned(
                cut_path, caps, keyframes,
                {"title": m.hook, "branding": "@yourhandle"},
                f"outputs/{job_id}_{idx}.mp4")
            # 6. Publish to each platform
            public_url = storage.upload_public(final_path, f"{job_id}_{idx}.mp4")
            for plat in body.platforms:
                out = publish.publish_clip(user_id, plat, final_path, public_url,
                                           title=m.hook, caption=m.reason)
                results.append(PublishResult(**out))
        job.moments = [ClipMoment(**m.__dict__) for m in moments]
        job.publish_results = results
        job.state = "done"
        jobs[job_id] = job
    except Exception as e:  # noqa: BLE001
        job.state = "error"
        job.error = str(e)
        jobs[job_id] = job


def run_pipeline(job_id: str, body: JobCreate) -> None:
    """BackgroundTasks entrypoint (dev / single-process)."""
    execute_pipeline(job_id, body)
