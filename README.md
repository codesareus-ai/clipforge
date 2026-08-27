# ClipForge

Auto-clip a long YouTube/Twitch video into viral short-form clips, edit them
(captions, branding, 9:16 face-tracked reframe), and upload to TikTok /
Instagram Reels / YouTube Shorts.

## Stack
- **Frontend**: Next.js + Remotion (auth UI, clip gallery, in-browser preview)
- **Backend**: FastAPI (pipeline orchestration) + ffmpeg render workers
- **Pipeline**: yt-dlp/streamlink → Faster-Whisper/WhisperX → LLM rank →
  MediaPipe reframe + Remotion render (captions, branding) → official upload APIs
- **Persistence**: SQLite (jobs + users + encrypted token vault)
- **Cache/queue**: Redis (optional Celery worker path)

## Quick start
```bash
# 1. Generate backend/.env with secure random secrets (TOKEN_SECRET, vault key)
python setup_env.py

# 2. Edit backend/.env to add: platform OAuth keys (client id/secret),
#    S3/R2 creds (needed for Instagram pull-from-URL), and an LLM API key.

# 3. Build + run the whole stack (backend :8000, frontend :3000, redis)
docker compose up --build
# Frontend: http://localhost:3000   Backend API: http://localhost:8000
```
Open the frontend, register a handle, then paste a video URL to start a job.

## Auth
Self-contained token auth (no external IdP required):
- `POST /auth/register` → bearer token
- `POST /auth/login` → bearer token
- `POST /auth/logout` → revokes the current token
- `GET  /me` → echoes your user_id

Tokens are HMAC-signed (itsdangerous) over a random UUID `user_id`; passwords
are bcrypt-hashed. Login is rate-limited (5 fails / 5 min). All job endpoints
require `Authorization: Bearer <token>` and are scoped to the owner.

## API contract (frontend ↔ backend)
- `POST /jobs` (auth) → `{job_id, state}`; runs the pipeline in the background.
- `GET /jobs/{id}` (auth) → current `JobStatus` (state, moments, publish_results).
- `GET /auth/{platform}/login` + `/callback` → OAuth onboarding (TikTok/IG/YouTube).
- `POST /cron/refresh-tokens` (auth) → refresh rotated platform tokens.

## ⚠️ TikTok audit gate
TikTok's Content Posting API requires a **2–6 week app review**. Until approved,
all API posts default to **private (SELF_ONLY)**. The publish layer already
honors this — public posting stays gated until your app passes audit. Also note:
Instagram Reels via Graph API is capped at 90s; YouTube Shorts auto-classifies
vertical <3min videos. All three require 9:16.

## Testing
```bash
cd backend
uv venv .venv && uv pip install -r requirements-dev.txt
python -m pytest tests/ -q        # 9 tests: pipeline + auth
```
CI runs the same suite on every push/PR.

## What's implemented vs. needs-you
**Done:** ingest, transcription, LLM virality ranking (OpenAI/Anthropic/Gemini),
MediaPipe face-track reframe, Remotion captioned render, OAuth vault +
refresh, publish dispatch (TikTok/IG/YouTube), auth, persistent SQLite store,
Docker stack, CI.
**Needs your input:** live API credentials in `.env`; passing TikTok's audit;
`npm install` already run (frontend compiles via `next build`).
