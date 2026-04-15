"""Unit tests for save_transcription and load_transcription."""

import dataclasses
import json
from pathlib import Path

import pytest

from pipeline import transcriber

# ---------------------------------------------------------------------------
# save_transcription
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_result() -> transcriber.TranscriptionResult:
    return transcriber.TranscriptionResult(
        text=" Hola, buenos días.",
        segments=[
            transcriber.Segment(
                start=0.0,
                end=1.5,
                text=" Hola, buenos días.",
            )
        ],
        language="Spanish",
    )


@pytest.mark.unit
def test_save_transcription_creates_file(
    tmp_path: Path, sample_result: transcriber.TranscriptionResult
) -> None:
    output = tmp_path / "out.json"
    transcriber.save_transcription(sample_result, output)
    assert output.exists()


@pytest.mark.unit
def test_save_transcription_content_is_valid_json(
    tmp_path: Path, sample_result: transcriber.TranscriptionResult
) -> None:
    output = tmp_path / "out.json"
    transcriber.save_transcription(sample_result, output)
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)


@pytest.mark.unit
def test_save_transcription_content_matches_result(
    tmp_path: Path, sample_result: transcriber.TranscriptionResult
) -> None:
    output = tmp_path / "out.json"
    transcriber.save_transcription(sample_result, output)
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert parsed["text"] == sample_result.text
    assert parsed["language"] == sample_result.language
    assert parsed["segments"] == [
        dataclasses.asdict(seg) for seg in sample_result.segments
    ]


@pytest.mark.unit
def test_save_transcription_preserves_non_ascii_characters(
    tmp_path: Path, sample_result: transcriber.TranscriptionResult
) -> None:
    output = tmp_path / "out.json"
    transcriber.save_transcription(sample_result, output)
    raw = output.read_text(encoding="utf-8")
    # ensure_ascii=False: characters like 'í' must appear literally, not escaped
    assert "días" in raw
    assert r"\u" not in raw


@pytest.mark.unit
def test_save_transcription_output_is_pretty_printed(
    tmp_path: Path, sample_result: transcriber.TranscriptionResult
) -> None:
    output = tmp_path / "out.json"
    transcriber.save_transcription(sample_result, output)
    raw = output.read_text(encoding="utf-8")
    # indent=2 produces newlines and leading spaces
    assert "\n" in raw
    assert "  " in raw


@pytest.mark.unit
def test_save_transcription_overwrites_existing_file(
    tmp_path: Path, sample_result: transcriber.TranscriptionResult
) -> None:
    output = tmp_path / "out.json"
    output.write_text("stale content", encoding="utf-8")
    transcriber.save_transcription(sample_result, output)
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert parsed["language"] == "Spanish"


# ---------------------------------------------------------------------------
# load_transcription
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_transcription_roundtrip(
    tmp_path: Path, sample_result: transcriber.TranscriptionResult
) -> None:
    path = tmp_path / "out.json"
    transcriber.save_transcription(sample_result, path)
    loaded = transcriber.load_transcription(path)
    assert loaded == sample_result


@pytest.mark.unit
def test_load_transcription_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        transcriber.load_transcription(tmp_path / "nonexistent.json")


# ---------------------------------------------------------------------------
# transcribe
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_transcribe_invalid_backend_raises() -> None:
    with pytest.raises(ValueError, match="Unknown backend"):
        transcriber.transcribe(
            Path("dummy.wav"), backend="invalid_backend"
        )
