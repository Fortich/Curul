"""Integration tests for the transcriber module.

Run the full suite with:
    uv run pytest

Skip slow tests with:
    uv run pytest -m "not slow"
"""

import dataclasses
from pathlib import Path

import pytest

from pipeline import transcriber

# Keywords Whisper should detect in "Hola, buenos días."
_EXPECTED_WORDS = {"hola", "buenos", "días", "buenas"}


@pytest.mark.slow
def test_transcribe_returns_valid_structure(short_audio: Path) -> None:
    result = transcriber.transcribe(short_audio)

    assert isinstance(result.text, str)
    assert len(result.text.strip()) > 0
    assert isinstance(result.segments, list)
    assert len(result.segments) > 0
    assert isinstance(result.language, str)


@pytest.mark.slow
def test_transcribe_detects_spanish(short_audio: Path) -> None:
    result = transcriber.transcribe(short_audio)

    assert result.language == "es", (
        f"Expected language 'es', got '{result.language}'. "
        f"Transcribed text: '{result.text}'"
    )


@pytest.mark.slow
def test_transcribe_recognizes_spoken_words(short_audio: Path) -> None:
    result = transcriber.transcribe(short_audio)
    words_in_text = set(result.text.lower().split())

    assert words_in_text & _EXPECTED_WORDS, (
        f"None of {_EXPECTED_WORDS} found in transcription: '{result.text}'"
    )


@pytest.mark.slow
def test_transcribe_segments_have_required_fields(short_audio: Path) -> None:
    result = transcriber.transcribe(short_audio)
    required_fields = {
        "id",
        "start",
        "end",
        "text",
        "tokens",
        "avg_logprob",
        "no_speech_prob",
    }
    segment_field_names = {
        f.name for f in dataclasses.fields(result.segments[0])
    }

    missing = required_fields - segment_field_names
    assert not missing, f"Segment missing fields: {missing}"

    for segment in result.segments:
        assert segment.end > segment.start, "Segment end must be after start"
