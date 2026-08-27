"""Verify the ranker against a real (free) LLM key — no video needed.

Builds a synthetic transcript with prosody, calls rank_moments, prints scored
moments. Proves the LLM ranking path works end-to-end with your key before you
run a full pipeline.

Usage:
    export RANK_LLM_API_KEY=sk-or-v1-...        # or set in backend/.env
    export RANK_LLM_BASE_URL=https://openrouter.ai/api/v1
    export RANK_LLM_MODEL=meta-llama/llama-3.1-8b-instruct:free
    python scripts/check_rank.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running from backend/ or repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rank import rank_moments
from app.services.transcribe import Segment, Word


def _demo_segment() -> Segment:
    words = [
        ("this", 0.0, 0.4), ("is", 0.5, 0.8), ("the", 0.9, 1.2),
        ("part", 1.3, 1.7), ("everyone", 1.8, 2.3), ("quotes", 2.4, 2.9),
        ("you", 3.0, 3.3), ("will", 3.4, 3.7), ("not", 3.8, 4.1),
        ("believe", 4.2, 4.7), ("what", 4.8, 5.1), ("happens", 5.2, 5.7),
        ("next", 5.8, 6.1),
    ]
    ws = [Word(w[1], w[2], w[0]) for w in words]
    return Segment(0.0, 6.1, " ".join(w[0] for w in words), ws)


def main() -> int:
    if not os.environ.get("RANK_LLM_API_KEY"):
        print("ERROR: set RANK_LLM_API_KEY (and optionally RANK_LLM_BASE_URL / "
              "RANK_LLM_MODEL) first. See backend/.env.example.")
        return 1
    print(f"provider={os.environ.get('RANK_LLM_PROVIDER','openai')} "
          f"base={os.environ.get('RANK_LLM_BASE_URL','(openai)')} "
          f"model={os.environ.get('RANK_LLM_MODEL','gpt-4o-mini')}")
    segs = [_demo_segment()]
    moments = rank_moments(segs, top_n=3)
    print(f"\nRanked {len(moments)} moment(s):")
    for m in moments:
        print(f"  [{m.start:.1f}-{m.end:.1f}] score={m.score} "
              f"hook={m.hook!r}")
        print(f"      reason: {m.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
