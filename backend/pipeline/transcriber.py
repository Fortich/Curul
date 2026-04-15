"""Transcribes audio files using a configurable ASR backend."""

import dataclasses
import json
import logging
import pathlib

logger = logging.getLogger(__name__)

BACKENDS = ("qwen3", "whisper")


@dataclasses.dataclass(frozen=True, slots=True)
class Segment:
    """A single timed segment produced by the ASR model."""

    start: float
    end: float
    text: str

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        """Constructs a Segment from a plain dictionary."""
        return cls(start=d["start"], end=d["end"], text=d["text"])


@dataclasses.dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """The full output returned by a transcription."""

    text: str
    segments: list[Segment]
    language: str

    @classmethod
    def from_dict(cls, d: dict) -> "TranscriptionResult":
        """Constructs a TranscriptionResult from a plain dictionary."""
        return cls(
            text=d["text"],
            segments=[Segment.from_dict(s) for s in d["segments"]],
            language=d["language"],
        )


def _transcribe_qwen3(audio_path: pathlib.Path) -> TranscriptionResult:
    """Transcribes using the Qwen3-ASR model via MLX."""
    import mlx_qwen3_asr  # lazy: only imported when this backend is used

    raw = mlx_qwen3_asr.transcribe(
        str(audio_path), return_timestamps=True, verbose=True
    )
    raw_segments = raw.segments or []
    segments = [
        Segment(
            start=s["start"] if isinstance(s, dict) else s.start,
            end=s["end"] if isinstance(s, dict) else s.end,
            text=s["text"] if isinstance(s, dict) else s.text,
        )
        for s in raw_segments
    ]
    return TranscriptionResult(
        text=raw.text,
        segments=segments,
        language=raw.language,
    )


def _transcribe_whisper(audio_path: pathlib.Path) -> TranscriptionResult:
    """Transcribes using openai-whisper (large-v3-turbo)."""
    import whisper  # lazy: only imported when this backend is used

    model = whisper.load_model("large-v3")
    raw = model.transcribe(str(audio_path))
    segments = [
        Segment(start=s["start"], end=s["end"], text=s["text"])
        for s in raw["segments"]
    ]
    return TranscriptionResult(
        text=raw["text"],
        segments=segments,
        language=raw["language"],
    )


def transcribe(
    audio_path: pathlib.Path, backend: str = "qwen3"
) -> TranscriptionResult:
    """Transcribes an audio file using the specified ASR backend.

    Args:
        audio_path: Path to the audio file to transcribe.
        backend: ASR backend to use. One of ``"qwen3"`` (default) or
            ``"whisper"``.

    Returns:
        A TranscriptionResult containing text, segments, and language.

    Raises:
        ValueError: If ``backend`` is not a recognised value.
    """
    logger.info("Transcribing: %s (backend=%s)", audio_path, backend)
    if backend == "qwen3":
        return _transcribe_qwen3(audio_path)
    if backend == "whisper":
        return _transcribe_whisper(audio_path)
    raise ValueError(f"Unknown backend {backend!r}. Valid options: {BACKENDS}")


def load_transcription(input_path: pathlib.Path) -> TranscriptionResult:
    """Loads a TranscriptionResult from a JSON file.

    The file must have been written by save_transcription.

    Args:
        input_path: pathlib.Path to the JSON file to read.

    Returns:
        The deserialized TranscriptionResult.
    """
    data = json.loads(input_path.read_text(encoding="utf-8"))
    result = TranscriptionResult.from_dict(data)
    logger.info("Transcription loaded from: %s", input_path)
    return result


def save_transcription(
    result: TranscriptionResult, output_path: pathlib.Path
) -> None:
    """Saves a transcription result to a JSON file.

    Args:
        result: The transcription result to serialize.
        output_path: pathlib.Path where the JSON file will be written.
    """
    output_path.write_text(
        json.dumps(dataclasses.asdict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Transcription saved to: %s", output_path)
