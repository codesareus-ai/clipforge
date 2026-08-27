"""RankService: LLM scores viral moments from transcript (0-100) with [start,end] + reason."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List

import requests

from app.config import get_settings
from app.services.transcribe import Segment

settings = get_settings()


@dataclass
class Moment:
    start: float
    end: float
    score: float
    hook: str
    reason: str


PROMPT = """You are a short-form clipping editor. Given a transcript (with [start-end] timestamps in seconds),
pick the top viral moments for TikTok/Reels/Shorts. Score each 0-100 on: hook strength, emotional peak,
quotability, conflict/contrast, practical value. Return JSON only: {"moments":[{"start":float,"end":float,
"score":int,"hook":str,"reason":str}]}. Only self-contained clips 20-60s. No overlap.

Transcript:
"""


def _transcript_text(segs: List[Segment]) -> str:
    return "\n".join(f"[{s.start:.1f}-{s.end:.1f}] {s.text}" for s in segs)


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def _call_llm(prompt: str) -> str:
    if settings.RANK_LLM_PROVIDER == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=settings.RANK_LLM_API_KEY)
        r = client.chat.completions.create(
            model=settings.RANK_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return r.choices[0].message.content or "{}"
    if settings.RANK_LLM_PROVIDER == "anthropic":
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": settings.RANK_LLM_API_KEY or "",
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": settings.RANK_LLM_MODEL or "claude-3-5-sonnet-20241022",
                  "max_tokens": 2000,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        ).json()
        return r["content"][0]["text"]
    if settings.RANK_LLM_PROVIDER == "gemini":
        key = settings.RANK_LLM_API_KEY or ""
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.RANK_LLM_MODEL or 'gemini-1.5-flash'}:generateContent?key={key}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=60,
        ).json()
        return r["candidates"][0]["content"]["parts"][0]["text"]
    raise NotImplementedError(f"provider {settings.RANK_LLM_PROVIDER} not implemented")


def rank_moments(segs: List[Segment], top_n: int = 7) -> List[Moment]:
    text = _transcript_text(segs)
    raw = _call_llm(PROMPT + text)
    data = _extract_json(raw)
    items_raw = data.get("moments", data if isinstance(data, list) else [])
    items = [Moment(**d) for d in items_raw][:top_n]
    return sorted(items, key=lambda m: m.score, reverse=True)
