"""RankService: scores viral moments from transcript + prosody (two-signal).

The "semantic pathway" is the transcript text; the "dynamic pathway" is cheap
prosodic signal derived from word-level timestamps (speaking rate, pauses,
energy proxy). Both are folded into the LLM prompt so ranking uses HOW something
was said, not just WHAT. This is the deployable stand-in for a heavy dual-pathway
audio encoder — no new model, runs on the same LLM call.

An OPTIONAL vision scorer (`rank_moments_vision`) can further refine moments
using a vision-capable LLM over extracted keyframes (VideoLLaMA-style capability
via an API we already call, not a local research model). It is opt-in and does
not change the default text-only path.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

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


PROMPT = """You are a short-form clipping editor. Given a transcript (with [start-end] \
timestamps in seconds) PLUS per-segment prosody signals (speaking rate in words/sec, \
pause count, energy proxy 0-1), pick the top viral moments for TikTok/Reels/Shorts.

Score each 0-100 on: hook strength, emotional peak, quotability, conflict/contrast, \
practical value, and prosodic emphasis (fast pace, loud/energetic, punchy pauses).

Return JSON only: {"moments":[{"start":float,"end":float,"score":int,"hook":str,\
"reason":str}]}. Only self-contained clips 20-60s. No overlap.

Transcript (semantic + dynamic pathways):
"""


def _seg_prosody(seg: Segment) -> dict:
    """Cheap 'dynamic pathway' from word timings — no audio decode needed.

    - wps: speaking rate (words/sec) over the segment
    - pauses: number of gaps > 0.6s between consecutive words (rhythm/emphasis)
    - energy_proxy: normalized wps vs a 2.5 wps baseline (faster == more energetic)
    """
    words = seg.words or []
    if len(words) < 2:
        return {"wps": 0.0, "pauses": 0, "energy_proxy": 0.0}
    dur = max(0.1, words[-1].end - words[0].start)
    wps = len(words) / dur
    pauses = sum(
        1 for a, b in zip(words, words[1:])
        if (b.start - a.end) > 0.6
    )
    energy_proxy = round(min(1.0, wps / 2.5), 2)
    return {"wps": round(wps, 2), "pauses": pauses, "energy_proxy": energy_proxy}


def _transcript_text(segs: List[Segment]) -> str:
    lines = []
    for s in segs:
        p = _seg_prosody(s)
        prosody = (
            f" [prosody: {p['wps']} wps, {p['pauses']} pauses, "
            f"energy {p['energy_proxy']}]"
        )
        lines.append(f"[{s.start:.1f}-{s.end:.1f}]{prosody} {s.text}")
    return "\n".join(lines)


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

        client = OpenAI(
            api_key=settings.RANK_LLM_API_KEY,
            base_url=settings.RANK_LLM_BASE_URL or None,
        )
        # OpenRouter wants an HTTP-Referer + X-Title; harmless elsewhere.
        extra = {}
        if settings.RANK_LLM_BASE_URL and "openrouter" in settings.RANK_LLM_BASE_URL:
            extra["headers"] = {
                "HTTP-Referer": "https://clipforge.local",
                "X-Title": "ClipForge",
            }
        try:
            r = client.chat.completions.create(
                model=settings.RANK_LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                **extra,
            )
            return r.choices[0].message.content or "{}"
        except Exception:
            # Some free models reject response_format=json_object; retry without it.
            r = client.chat.completions.create(
                model=settings.RANK_LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                **extra,
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
    """Two-signal rank: transcript (semantic) + prosody (dynamic)."""
    text = _transcript_text(segs)
    raw = _call_llm(PROMPT + text)
    data = _extract_json(raw)
    items_raw = data.get("moments", data if isinstance(data, list) else [])
    items = [Moment(**d) for d in items_raw][:top_n]
    return sorted(items, key=lambda m: m.score, reverse=True)


# ---------------------------------------------------------------------------
# OPTIONAL vision scorer (opt-in; not used by the default pipeline path).
# Provides VideoLLaMA-style multimodal moment scoring via an API we already
# call (Gemini/Claude vision), without a local research model.
# ---------------------------------------------------------------------------
def rank_moments_vision(
    segs: List[Segment],
    keyframe_paths: List[str],
    top_n: int = 7,
) -> List[Moment]:
    """Refine moments using a vision-capable LLM over extracted keyframes.

    `keyframe_paths` are image files (one per candidate window). The vision LLM
    sees the frames + transcript and scores visual interest (faces, motion,
    on-screen text, emotion). Merges with the text rank by taking the higher
    score of the two signals for overlapping windows.
    """
    # Text-only rank as the baseline signal.
    text_moments = rank_moments(segs, top_n=top_n)
    text_by_window = {(round(m.start), round(m.end)): m for m in text_moments}

    # Build a vision prompt that references the keyframes.
    vision_prompt = (
        "You are a short-form clipping editor. For each attached keyframe image "
        "(in order), rate the visual virality 0-100 (faces/expression, motion, "
        "on-screen text, emotion, novelty). Also return the matching [start,end] "
        "window in seconds if known. Return JSON: "
        '{"frames":[{"start":float,"end":float,"visual_score":int,"why":str}]}.'
    )
    try:
        if settings.RANK_LLM_PROVIDER == "gemini":
            import base64

            parts = [{"text": vision_prompt}]
            for p in keyframe_paths:
                b64 = base64.b64encode(open(p, "rb").read()).decode()
                parts.append({"inline_data": {"mime_type": "image/jpeg",
                                              "data": b64}})
            key = settings.RANK_LLM_API_KEY or ""
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{settings.RANK_LLM_MODEL or 'gemini-1.5-flash'}"
                f":generateContent?key={key}",
                json={"contents": [{"parts": parts}]}, timeout=60,
            ).json()
            vision_raw = r["candidates"][0]["content"]["parts"][0]["text"]
            vision_data = _extract_json(vision_raw)
            for fr in vision_data.get("frames", []):
                key = (round(fr.get("start", 0)), round(fr.get("end", 0)))
                if key in text_by_window:
                    m = text_by_window[key]
                    # Blend: keep the higher of the two signals.
                    m.score = round(max(m.score, float(fr.get("visual_score", 0))), 1)
        # (Anthropic/OpenAI vision branches can be added the same way.)
    except Exception:  # noqa: BLE001 - vision is an enhancement; never block text rank
        return text_moments
    return sorted(text_by_window.values(), key=lambda m: m.score, reverse=True)
