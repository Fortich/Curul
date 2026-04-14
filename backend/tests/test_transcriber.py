"""Unit tests for get_device and save_transcription."""

import dataclasses
import json
from pathlib import Path
from unittest import mock

import pytest

from pipeline import transcriber

# ---------------------------------------------------------------------------
# get_device
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "cuda, mps, expected",
    [
        (True, False, "cuda"),
        (False, True, "mps"),
        (True, True, "cuda"),  # cuda takes priority
        (False, False, "cpu"),
    ],
)
def test_get_device(cuda: bool, mps: bool, expected: str) -> None:
    with (
        mock.patch("torch.cuda.is_available", return_value=cuda),
        mock.patch("torch.backends.mps.is_available", return_value=mps),
    ):
        assert transcriber.get_device() == expected


@pytest.mark.unit
def test_get_device_returns_valid_device_string_on_current_machine() -> None:
    assert transcriber.get_device() in {"cuda", "mps", "cpu"}


# ---------------------------------------------------------------------------
# save_transcription
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_result() -> transcriber.TranscriptionResult:
    return transcriber.TranscriptionResult(
        text=" Hola, buenos días.",
        segments=[
            transcriber.Segment(
                id=0,
                seek=0,
                start=0.0,
                end=1.5,
                text=" Hola, buenos días.",
                tokens=[50364, 2952],
                temperature=0.0,
                avg_logprob=-0.3,
                compression_ratio=1.0,
                no_speech_prob=0.01,
            )
        ],
        language="es",
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
    assert parsed["language"] == "es"


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
def test_load_transcription_text(
    tmp_path: Path, sample_result: transcriber.TranscriptionResult
) -> None:
    path = tmp_path / "out.json"
    transcriber.save_transcription(sample_result, path)
    loaded = transcriber.load_transcription(path)
    assert loaded.text == sample_result.text


@pytest.mark.unit
def test_load_transcription_language(
    tmp_path: Path, sample_result: transcriber.TranscriptionResult
) -> None:
    path = tmp_path / "out.json"
    transcriber.save_transcription(sample_result, path)
    loaded = transcriber.load_transcription(path)
    assert loaded.language == sample_result.language


@pytest.mark.unit
def test_load_transcription_segments(
    tmp_path: Path, sample_result: transcriber.TranscriptionResult
) -> None:
    path = tmp_path / "out.json"
    transcriber.save_transcription(sample_result, path)
    loaded = transcriber.load_transcription(path)
    assert loaded.segments == sample_result.segments


@pytest.mark.unit
def test_load_transcription_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        transcriber.load_transcription(tmp_path / "nonexistent.json")
