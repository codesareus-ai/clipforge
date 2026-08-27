"""TranscribeService: Faster-Whisper (word timestamps) + optional WhisperX diarization."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.config import get_settings

settings = get_settings()


@dataclass
class Word:
    start: float
    end: float
    text: str
    speaker: str | None = None


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)
    speaker: str | None = None


def transcribe(audio_path: str) -> list[Segment]:
    """Transcribe using Faster-Whisper. Accepts a video file (whisper reads audio track)."""
    from faster_whisper import WhisperModel

    model = WhisperModel(settings.WHISPER_MODEL, device=settings.WHISPER_DEVICE)
    segs, _ = model.transcribe(audio_path, word_timestamps=True, vad_filter=True)
    out: list[Segment] = []
    for s in segs:
        words = [Word(w.start, w.end, w.word) for w in (s.words or [])]
        out.append(Segment(s.start, s.end, s.text, words))
    return out


def transcribe_with_diarization(audio_path: str) -> list[Segment]:
    """WhisperX path for multi-speaker content. Requires HF_TOKEN for pyannote models."""
    import whisperx

    device = settings.WHISPER_DEVICE
    model = whisperx.load_model(settings.WHISPER_MODEL, device, compute_type="float16")
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=16)
    align = whisperx.align(
        result["segments"],
        whisperx.load_align_model(language_code="en", device=device),
        audio, device,
    )
    diarize = whisperx.DiarizationPipeline(use_auth_token=settings.HF_TOKEN, device=device)(audio)
    result = whisperx.assign_word_speakers(diarize, align)
    out: list[Segment] = []
    for s in result["segments"]:
        out.append(Segment(s["start"], s["end"], s["text"], speaker=s.get("speaker")))
    return out
