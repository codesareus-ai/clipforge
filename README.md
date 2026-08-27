# ClipForge

Auto-clip a long YouTube/Twitch video into viral short-form clips, edit them
(captions, branding, 9:16 reframe), and upload to TikTok / Instagram Reels / YouTube Shorts.

## Stack
- **Frontend**: Next.js + Remotion (in-browser clip preview/gallery)
- **Backend**: FastAPI (pipeline orchestration) + ffmpeg render workers
- **Pipeline**: yt-dlp/streamlink → Faster-Whisper/WhisperX → LLM rank → ffmpeg + Remotion render → official upload APIs

## Quick start
```bash
cp backend/.env.example backend/.env   # fill in keys
docker compose up --build
# frontend: http://localhost:3000   backend: http://localhost:8000
```

## Architecture
```
URL → IngestService (yt-dlp/streamlink)
   → Faster-Whisper/WhisperX → transcript + word timestamps
   → LLM ranks viral moments (0–100, [start,end])
   → ffmpeg cut + Remotion render (9:16, captions, branding)
   → S3/R2 public URL → UploadService (TikTok / IG Reels / YT Shorts)
```

## ⚠️ TikTok audit gate
TikTok's Content Posting API requires a **2–6 week app review**. Until approved,
all API posts default to **private (SELF_ONLY)**. Build the OAuth onboarding +
token vault, but gate public posting behind audit approval.

## TODO before production
- Replace in-memory `store.jobs` with Redis/DB.
- Move pipeline to Celery/RQ/Temporal workers.
- Implement Anthropic/Gemini branches in `services/rank.py`.
- Complete OAuth callback routes + token refresh cron (tokens rotate every call).
- Wire TikTok/IG upload clients into `worker.py` (currently stubbed).
- Add face-track reframe (MediaPipe/YOLO) instead of static scale.
