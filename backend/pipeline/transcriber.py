"""Transcribes audio files using the Whisper speech recognition model."""

import dataclasses
import json
import logging
import pathlib

import torch
import whisper

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True, slots=True)
class Segment:
    """A single timed segment produced by Whisper."""

    id: int
    seek: int
    start: float
    end: float
    text: str
    tokens: list[int]
    temperature: float
    avg_logprob: float
    compression_ratio: float
    no_speech_prob: float

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        """Constructs a Segment from a plain dictionary."""
        return cls(**{f.name: d[f.name] for f in dataclasses.fields(cls)})


@dataclasses.dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """The full output returned by a Whisper transcription."""

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


def get_device() -> str:
    """Returns the best available compute device for inference."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def transcribe(
    audio_path: pathlib.Path, device: str | None = None
) -> TranscriptionResult:
    """Transcribes an audio file using the Whisper large-v3 model.

    Args:
        audio_path: pathlib.Path to the audio file to transcribe.
        device: Compute device to use (cuda/mps/cpu). Auto-detected if None.

    Returns:
        A TranscriptionResult containing text, segments, and language.
    """
    device = device or get_device()
    logger.info("Using device: %s", device)
    model = whisper.load_model("large-v3", device=device)
    raw = model.transcribe(str(audio_path), verbose=True)
    return TranscriptionResult.from_dict(raw)


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
