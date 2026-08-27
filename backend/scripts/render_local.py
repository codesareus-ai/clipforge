"""Local end-to-end render demo (no external APIs).

Runs the REAL media pipeline stages on a local file:
  1. (optional) generate a test-pattern sample clip with ffmpeg
  2. transcribe  -> MOCKED (synthetic word-level transcript)
  3. rank        -> MOCKED (deterministic mid-clip pick)
  4. cut         -> REAL ffmpeg
  5. reframe     -> REAL (MediaPipe or static center)
  6. render      -> REAL ffmpeg 9:16 + SRT caption burn + branding

Only the AI boundaries (whisper, LLM) are mocked — the output is a genuine
vertical .mp4. Usage:

    python scripts/render_local.py                       # makes a sample clip
    python scripts/render_local.py path/to/video.mp4
"""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

from app.config import get_settings
from app.services import render, reframe
from app.services.transcribe import Segment, Word
from app.services.rank import Moment

settings = get_settings()
HERE = Path(__file__).resolve().parent
OUT = Path(settings.OUTPUT_DIR)
OUT.mkdir(parents=True, exist_ok=True)


def make_sample(path: str) -> str:
    """Generate a 12s 1280x720 test-pattern clip with a moving box + tone."""
    cmd = [
        settings.FFMPEG_BIN, "-y",
        "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30:duration=12",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=12",
        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


def mock_transcribe(src: str) -> list[Segment]:
    """Synthetic word-level transcript (stand-in for Faster-Whisper)."""
    words = [
        "This", "is", "the", "part", "everyone", "quotes",
        "you", "will", "not", "believe", "what", "happens", "next",
        "the", "secret", "is", "consistency", "and", "repetition",
    ]
    segs = []
    t = 2.0
    buf: list[Word] = []
    for i, w in enumerate(words):
        start = t + i * 0.45
        end = start + 0.4
        buf.append(Word(round(start, 2), round(end, 2), w))
    # one segment covering the mock speech window
    segs.append(Segment(2.0, 2.0 + len(words) * 0.45, " ".join(words), buf))
    return segs


def mock_rank(segs: list[Segment], top_n: int = 1) -> list[Moment]:
    """Deterministic pick: the 8s window starting at t=2 (the mock speech)."""
    return [Moment(start=2.0, end=10.0, score=88,
                   hook="the part everyone quotes",
                   reason="strong hook + quotable line")]


def main() -> int:
    if len(sys.argv) > 1:
        src = sys.argv[1]
    else:
        sample = str(OUT / "sample.mp4")
        print(f"[1] generating sample clip -> {sample}")
        make_sample(sample)
        src = sample

    print(f"[2] transcribe (mocked) -> {src}")
    segs = mock_transcribe(src)

    print("[3] rank (mocked)")
    moments = mock_rank(segs)

    for idx, m in enumerate(moments):
        print(f"[4] cut [{m.start}-{m.end}]")
        cut_path = render.cut(src, m.start, m.end, str(OUT / f"local_raw_{idx}.mp4"))

        caps = [
            {"text": w.text.strip(), "start": round(w.start - m.start, 2),
             "end": round(w.end - m.start, 2)}
            for s in segs for w in s.words
            if m.start <= w.start <= m.end
        ]
        print("[5] reframe (real)")
        keyframes = reframe.compute_reframe(cut_path)

        print("[6] render 9:16 + captions (real ffmpeg)")
        final = render.render_captioned(
            cut_path, caps, keyframes,
            {"title": m.hook, "branding": "@yourhandle"},
            str(OUT / f"local_clip_{idx}.mp4"),
        )
        manifest = {
            "source": src, "moment": {"start": m.start, "end": m.end,
                                      "hook": m.hook},
            "captions": len(caps), "keyframes": len(keyframes),
            "output": final,
        }
        (OUT / f"local_manifest_{idx}.json").write_text(__import__("json").dumps(manifest, indent=2))
        print(f"    -> {final}")
        # Verify with ffprobe if available.
        try:
            p = subprocess.run(
                [settings.FFMPEG_BIN.replace("ffmpeg", "ffprobe"), "-v", "error",
                 "-show_entries", "stream=width,height,codec_type",
                 "-of", "json", final],
                capture_output=True, text=True, check=True,
            )
            print("    ffprobe:", p.stdout.strip())
        except Exception as e:  # noqa: BLE001
            print(f"    (ffprobe check skipped: {e})")
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
