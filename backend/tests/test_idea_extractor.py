"""Unit tests for idea_extractor."""

import json
from unittest import mock

import pytest

from pipeline import idea_extractor, session_info_extractor, transcriber

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_segment(
    id: int, start: float, end: float, text: str
) -> transcriber.Segment:
    return transcriber.Segment(start=start, end=end, text=text)


def _make_session_result(
    participants: list[str] | None = None,
    themes: list[str] | None = None,
) -> session_info_extractor.SessionResult:
    return session_info_extractor.SessionResult(
        session="S1",
        summary="Resumen de prueba.",
        participants=participants or ["García López"],
        themes=themes or ["Economía"],
        youtube_url="",
        date="2026-01-01",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_transcription() -> transcriber.TranscriptionResult:
    return transcriber.TranscriptionResult(
        text=" El señor García dijo algo importante.",
        segments=[
            _make_segment(0, 10.0, 20.0, " El señor García"),
            _make_segment(1, 20.0, 35.5, " dijo algo importante."),
        ],
        language="es",
    )


@pytest.fixture
def session_result() -> session_info_extractor.SessionResult:
    return _make_session_result()


@pytest.fixture
def llm_payload() -> str:
    return json.dumps(
        {
            "ideas": [
                {
                    "congressman_name": "García López",
                    "quote": "dijo algo importante",
                    "start": 10.0,
                    "end": 35.5,
                    "tags": ["economía", "presupuestos"],
                }
            ]
        }
    )


# ---------------------------------------------------------------------------
# _format_segments
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_format_segments_includes_timestamps(
    sample_transcription: transcriber.TranscriptionResult,
) -> None:
    result = idea_extractor._format_segments(sample_transcription.segments)
    assert "10.0s" in result
    assert "35.5s" in result


@pytest.mark.unit
def test_format_segments_includes_text(
    sample_transcription: transcriber.TranscriptionResult,
) -> None:
    result = idea_extractor._format_segments(sample_transcription.segments)
    assert "El señor García" in result
    assert "dijo algo importante." in result


@pytest.mark.unit
def test_format_segments_one_line_per_segment(
    sample_transcription: transcriber.TranscriptionResult,
) -> None:
    result = idea_extractor._format_segments(sample_transcription.segments)
    assert len(result.splitlines()) == len(sample_transcription.segments)


@pytest.mark.unit
def test_format_segments_empty_transcription() -> None:
    assert idea_extractor._format_segments([]) == ""


# ---------------------------------------------------------------------------
# _chunk_segments (character-based splitting)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_chunk_segments_empty_returns_empty() -> None:
    assert idea_extractor._chunk_segments([], max_chars=100) == []


@pytest.mark.unit
def test_chunk_segments_fits_in_one_chunk() -> None:
    segments = [
        _make_segment(i, i * 10.0, i * 10.0 + 9.0, "text") for i in range(3)
    ]
    chunks = idea_extractor._chunk_segments(segments, max_chars=10_000)
    assert len(chunks) == 1
    assert chunks[0] == segments


@pytest.mark.unit
def test_chunk_segments_splits_on_chars() -> None:
    # Two segments whose combined formatted text exceeds max_chars
    segments = [
        _make_segment(0, 0.0, 1.0, "a" * 60),
        _make_segment(1, 1.0, 2.0, "b" * 60),
    ]
    chunks = idea_extractor._chunk_segments(segments, max_chars=70)
    assert len(chunks) == 2
    assert chunks[0] == [segments[0]]
    assert chunks[1] == [segments[1]]


@pytest.mark.unit
def test_chunk_segments_never_splits_a_segment() -> None:
    segments = [
        _make_segment(i, float(i), float(i) + 0.9, "x" * 10) for i in range(10)
    ]
    chunks = idea_extractor._chunk_segments(segments, max_chars=30)
    reassembled = [seg for chunk in chunks for seg in chunk]
    assert reassembled == segments


# ---------------------------------------------------------------------------
# extract_ideas
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extract_ideas_returns_list(
    sample_transcription: transcriber.TranscriptionResult,
    session_result: session_info_extractor.SessionResult,
    llm_payload: str,
) -> None:
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value=llm_payload,
    ):
        ideas = idea_extractor.extract_ideas(
            sample_transcription, "Pleno 2024-01-15", "fake-key", session_result
        )
    assert isinstance(ideas, list)


@pytest.mark.unit
def test_extract_ideas_injects_session(
    sample_transcription: transcriber.TranscriptionResult,
    session_result: session_info_extractor.SessionResult,
    llm_payload: str,
) -> None:
    session = "Pleno 2024-01-15"
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value=llm_payload,
    ):
        ideas = idea_extractor.extract_ideas(
            sample_transcription, session, "fake-key", session_result
        )
    assert all(idea["session"] == session for idea in ideas)


@pytest.mark.unit
def test_extract_ideas_parses_fields(
    sample_transcription: transcriber.TranscriptionResult,
    session_result: session_info_extractor.SessionResult,
    llm_payload: str,
) -> None:
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value=llm_payload,
    ):
        ideas = idea_extractor.extract_ideas(
            sample_transcription, "Pleno 2024-01-15", "fake-key", session_result
        )

    idea = ideas[0]
    assert idea["congressman_name"] == "García López"
    assert idea["quote"] == "dijo algo importante"
    assert idea["start"] == 10.0
    assert idea["end"] == 35.5
    assert idea["tags"] == ["economía", "presupuestos"]


@pytest.mark.unit
def test_extract_ideas_handles_empty_ideas_array(
    sample_transcription: transcriber.TranscriptionResult,
    session_result: session_info_extractor.SessionResult,
) -> None:
    payload = json.dumps({"ideas": []})
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value=payload,
    ):
        ideas = idea_extractor.extract_ideas(
            sample_transcription, "Pleno 2024-01-15", "fake-key", session_result
        )
    assert ideas == []


@pytest.mark.unit
def test_extract_ideas_passes_credentials_to_chat_completion(
    sample_transcription: transcriber.TranscriptionResult,
    session_result: session_info_extractor.SessionResult,
    llm_payload: str,
) -> None:
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value=llm_payload,
    ) as mock_fn:
        idea_extractor.extract_ideas(
            sample_transcription,
            "Pleno 2024-01-15",
            api_key="my-key",
            session_result=session_result,
            base_url="https://custom.api.com",
            model="deepseek-reasoner",
        )

    call_kwargs = mock_fn.call_args.kwargs
    assert call_kwargs["api_key"] == "my-key"
    assert call_kwargs["base_url"] == "https://custom.api.com"
    assert call_kwargs["model"] == "deepseek-reasoner"


@pytest.mark.unit
def test_extract_ideas_tags_default_to_empty_list(
    sample_transcription: transcriber.TranscriptionResult,
    session_result: session_info_extractor.SessionResult,
) -> None:
    payload = json.dumps(
        {
            "ideas": [
                {
                    "congressman_name": "X",
                    "quote": "Y",
                    "start": 1.0,
                    "end": 2.0,
                }
            ]
        }
    )
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value=payload,
    ):
        ideas = idea_extractor.extract_ideas(
            sample_transcription, "S1", "fake-key", session_result
        )
    assert ideas[0]["tags"] == []


@pytest.mark.unit
def test_extract_ideas_merges_results_across_chunks(
    session_result: session_info_extractor.SessionResult,
) -> None:
    # Two segments with large text force char-based splitting into separate chunks.
    # First chunk returns empty (no drop/rewind), second returns one idea.
    big_text = "x" * 60_000
    segments = [
        _make_segment(0, 0.0, 10.0, big_text),
        _make_segment(1, 10.0, 20.0, big_text),
    ]
    transcription = transcriber.TranscriptionResult(
        text="", segments=segments, language="es"
    )
    empty = json.dumps({"ideas": []})
    one_idea = json.dumps(
        {"ideas": [{"congressman_name": "García López", "quote": "q", "start": 10.0, "end": 20.0, "tags": []}]}
    )

    with mock.patch(
        "pipeline.deepseek.chat_completion",
        side_effect=[empty, one_idea],
    ) as mock_fn:
        ideas = idea_extractor.extract_ideas(
            transcription, "S1", "fake-key", session_result
        )

    assert mock_fn.call_count == 2
    assert len(ideas) == 1


# ---------------------------------------------------------------------------
# _process_segments — error-handling paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_process_segments_all_invalid_json_returns_empty() -> None:
    segments = [_make_segment(0, 0.0, 10.0, "texto")]
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value="not-json",
    ):
        result = idea_extractor._process_segments(
            segments, "S1", "k", "url", "m",
            known_participants=[], known_themes=[],
        )
    assert result == []


@pytest.mark.unit
def test_process_segments_ideas_not_a_list_returns_empty() -> None:
    payload = json.dumps({"ideas": "not-a-list"})
    segments = [_make_segment(0, 0.0, 10.0, "texto")]
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value=payload,
    ):
        result = idea_extractor._process_segments(
            segments, "S1", "k", "url", "m",
            known_participants=[], known_themes=[],
        )
    assert result == []


@pytest.mark.unit
def test_process_segments_partial_items_returns_best() -> None:
    payload = json.dumps(
        {
            "ideas": [
                {
                    "congressman_name": "García",
                    "quote": "válido",
                    "start": 1.0,
                    "end": 2.0,
                    "tags": [],
                },
                {"malformed": True},  # missing required fields
            ]
        }
    )
    segments = [_make_segment(0, 0.0, 10.0, "texto")]
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value=payload,
    ):
        result = idea_extractor._process_segments(
            segments, "S1", "k", "url", "m",
            known_participants=[], known_themes=[],
        )
    assert len(result) == 1
    assert result[0]["congressman_name"] == "García"


@pytest.mark.unit
def test_process_segments_recovers_on_later_attempt() -> None:
    good = json.dumps(
        {
            "ideas": [
                {
                    "congressman_name": "García",
                    "quote": "cita",
                    "start": 0.0,
                    "end": 5.0,
                    "tags": [],
                }
            ]
        }
    )
    segments = [_make_segment(0, 0.0, 10.0, "texto")]
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        side_effect=["not-json", good],
    ):
        result = idea_extractor._process_segments(
            segments, "S1", "k", "url", "m",
            known_participants=[], known_themes=[],
        )
    assert len(result) == 1
    assert result[0]["congressman_name"] == "García"
