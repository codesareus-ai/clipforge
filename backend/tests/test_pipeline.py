"""End-to-end pipeline test with every external boundary mocked.
Proves orchestration works without live keys, network, ffmpeg, or GPU."""
from app.worker import execute_pipeline
from app.store import jobs
from app.services import rank
from app.models import JobCreate, JobStatus


class W:
    def __init__(self, st, en, t):
        self.start, self.end, self.text = st, en, t


class S:
    def __init__(self, st, en, t, ws):
        self.start, self.end, self.text, self.words = st, en, t, ws


def test_pipeline_runs_with_mocks(monkeypatch):
    monkeypatch.setattr("app.services.ingest.download", lambda *a, **k: "/tmp/fake.mp4")
    monkeypatch.setattr("app.services.transcribe.transcribe",
                        lambda *a, **k: [S(0, 5, "hi there", [W(0, 1, "hi"), W(1, 2, "there")])])
    monkeypatch.setattr("app.services.rank.rank_moments",
                        lambda segs, top_n=7: [rank.Moment(0, 5, 90, "hook", "reason")])
    monkeypatch.setattr("app.services.render.cut", lambda *a, **k: "/tmp/cut.mp4")
    monkeypatch.setattr("app.services.render.render_captioned", lambda *a, **k: "/tmp/final.mp4")
    monkeypatch.setattr("app.services.reframe.compute_reframe",
                        lambda *a, **k: [{"t": 0, "x": 0.5, "y": 0.5, "scale": 1.0}])
    monkeypatch.setattr("app.services.upload.storage.upload_public",
                        lambda *a, **k: "https://cdn/abc.mp4")
    monkeypatch.setattr("app.services.upload.publish.publish_clip",
                        lambda *a, **k: {"platform": "tiktok", "ok": True, "publish_id": "x"})

    job_id = "test-job"
    jobs[job_id] = JobStatus(job_id=job_id, user_id="test-user", state="queued")
    execute_pipeline(job_id, JobCreate(url="https://x", top_n=1, platforms=["tiktok"]))

    job = jobs[job_id]
    assert job.state == "done", job.error
    assert len(job.moments) == 1
    assert job.publish_results[0].ok is True
