"""Rank tests: prosody helper + prompt building (no network/keys)."""
from app.services import rank
from app.services.transcribe import Segment, Word


def _seg(words):
    ws = [Word(w[0], w[1], w[2]) for w in words]
    return Segment(ws[0].start, ws[-1].end, " ".join(w[2] for w in words), ws)


def test_prosody_fast_speech_high_energy():
    # 10 words over 2s -> 5 wps -> energy ~1.0, no long pauses
    seg = _seg([(i * 0.2, i * 0.2 + 0.18, f"w{i}") for i in range(10)])
    p = rank._seg_prosody(seg)
    assert p["wps"] > 4.0
    assert p["energy_proxy"] == 1.0
    assert p["pauses"] == 0


def test_prosody_detects_pauses():
    # words with a 1s gap in the middle -> 1 pause
    words = [(0.0, 0.18, "a"), (0.2, 0.38, "b"), (1.5, 1.68, "c"), (1.7, 1.88, "d")]
    seg = _seg(words)
    p = rank._seg_prosody(seg)
    assert p["pauses"] == 1


def test_prosody_empty_segment_safe():
    seg = Segment(0, 0, "", [])
    p = rank._seg_prosody(seg)
    assert p == {"wps": 0.0, "pauses": 0, "energy_proxy": 0.0}


def test_transcript_text_includes_prosody():
    seg = _seg([(0.0, 0.18, "hello"), (0.2, 0.38, "world")])
    txt = rank._transcript_text([seg])
    assert "prosody:" in txt
    assert "hello" in txt
