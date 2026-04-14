"""Unit tests for idea_extractor."""

import json
from unittest import mock

import pytest

from pipeline import idea_extractor, transcriber

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_segment(
    id: int, start: float, end: float, text: str
) -> transcriber.Segment:
    return transcriber.Segment(
        id=id,
        seek=0,
        start=start,
        end=end,
        text=text,
        tokens=[],
        temperature=0.0,
        avg_logprob=-0.3,
        compression_ratio=1.0,
        no_speech_prob=0.01,
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
# _chunk_segments
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_chunk_segments_empty_returns_empty() -> None:
    assert idea_extractor._chunk_segments([], 600.0) == []


@pytest.mark.unit
def test_chunk_segments_fits_in_one_chunk() -> None:
    segments = [
        _make_segment(i, i * 10.0, i * 10.0 + 9.0, "text") for i in range(3)
    ]
    chunks = idea_extractor._chunk_segments(segments, 600.0)
    assert len(chunks) == 1
    assert chunks[0] == segments


@pytest.mark.unit
def test_chunk_segments_splits_on_duration() -> None:
    # 3 segments: 0-10s, 10-20s, 700-710s — the third exceeds a 600s window
    segments = [
        _make_segment(0, 0.0, 10.0, "a"),
        _make_segment(1, 10.0, 20.0, "b"),
        _make_segment(2, 700.0, 710.0, "c"),
    ]
    chunks = idea_extractor._chunk_segments(segments, 600.0)
    assert len(chunks) == 2
    assert chunks[0] == segments[:2]
    assert chunks[1] == segments[2:]


@pytest.mark.unit
def test_chunk_segments_never_splits_a_segment() -> None:
    segments = [
        _make_segment(i, i * 100.0, i * 100.0 + 90.0, "text") for i in range(10)
    ]
    chunks = idea_extractor._chunk_segments(segments, 150.0)
    reassembled = [seg for chunk in chunks for seg in chunk]
    assert reassembled == segments


# ---------------------------------------------------------------------------
# extract_ideas
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extract_ideas_returns_list(
    sample_transcription: transcriber.TranscriptionResult,
    llm_payload: str,
) -> None:
    with mock.patch(
        "pipeline.idea_extractor._chat_completion",
        return_value=llm_payload,
    ):
        ideas = idea_extractor.extract_ideas(
            sample_transcription, "Pleno 2024-01-15", "fake-key"
        )
    assert isinstance(ideas, list)


@pytest.mark.unit
def test_extract_ideas_injects_session(
    sample_transcription: transcriber.TranscriptionResult,
    llm_payload: str,
) -> None:
    session = "Pleno 2024-01-15"
    with mock.patch(
        "pipeline.idea_extractor._chat_completion",
        return_value=llm_payload,
    ):
        ideas = idea_extractor.extract_ideas(
            sample_transcription, session, "fake-key"
        )
    assert all(idea["session"] == session for idea in ideas)


@pytest.mark.unit
def test_extract_ideas_parses_fields(
    sample_transcription: transcriber.TranscriptionResult,
    llm_payload: str,
) -> None:
    with mock.patch(
        "pipeline.idea_extractor._chat_completion",
        return_value=llm_payload,
    ):
        ideas = idea_extractor.extract_ideas(
            sample_transcription, "Pleno 2024-01-15", "fake-key"
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
) -> None:
    payload = json.dumps({"ideas": []})
    with mock.patch(
        "pipeline.idea_extractor._chat_completion",
        return_value=payload,
    ):
        ideas = idea_extractor.extract_ideas(
            sample_transcription, "Pleno 2024-01-15", "fake-key"
        )
    assert ideas == []


@pytest.mark.unit
def test_extract_ideas_passes_credentials_to_chat_completion(
    sample_transcription: transcriber.TranscriptionResult,
    llm_payload: str,
) -> None:
    with mock.patch(
        "pipeline.idea_extractor._chat_completion",
        return_value=llm_payload,
    ) as mock_fn:
        idea_extractor.extract_ideas(
            sample_transcription,
            "Pleno 2024-01-15",
            api_key="my-key",
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
        "pipeline.idea_extractor._chat_completion",
        return_value=payload,
    ):
        ideas = idea_extractor.extract_ideas(
            sample_transcription, "S1", "fake-key"
        )
    assert ideas[0]["tags"] == []


@pytest.mark.unit
def test_extract_ideas_merges_results_across_chunks(
    llm_payload: str,
) -> None:
    # Two chunks separated by > 20 min: _chat_completion called twice,
    # results merged into one list.
    segments = [
        _make_segment(0, 0.0, 10.0, "primer chunk"),
        _make_segment(1, 2000.0, 2010.0, "segundo chunk"),
    ]
    transcription = transcriber.TranscriptionResult(
        text="", segments=segments, language="es"
    )

    with mock.patch(
        "pipeline.idea_extractor._chat_completion",
        return_value=llm_payload,
    ) as mock_fn:
        ideas = idea_extractor.extract_ideas(transcription, "S1", "fake-key")

    assert mock_fn.call_count == 2
    assert len(ideas) == 2  # one idea per chunk call


# ---------------------------------------------------------------------------
# _process_chunk — error-handling paths
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_process_chunk_all_invalid_json_returns_empty() -> None:
    segments = [_make_segment(0, 0.0, 10.0, "texto")]
    with mock.patch(
        "pipeline.idea_extractor._chat_completion",
        return_value="not-json",
    ):
        result = idea_extractor._process_chunk(
            segments, "S1", 1, 1, "k", "url", "m"
        )
    assert result == []


@pytest.mark.unit
def test_process_chunk_ideas_not_a_list_returns_empty() -> None:
    payload = json.dumps({"ideas": "not-a-list"})
    segments = [_make_segment(0, 0.0, 10.0, "texto")]
    with mock.patch(
        "pipeline.idea_extractor._chat_completion",
        return_value=payload,
    ):
        result = idea_extractor._process_chunk(
            segments, "S1", 1, 1, "k", "url", "m"
        )
    assert result == []


@pytest.mark.unit
def test_process_chunk_partial_items_returns_best() -> None:
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
        "pipeline.idea_extractor._chat_completion",
        return_value=payload,
    ):
        result = idea_extractor._process_chunk(
            segments, "S1", 1, 1, "k", "url", "m"
        )
    assert len(result) == 1
    assert result[0]["congressman_name"] == "García"


@pytest.mark.unit
def test_process_chunk_recovers_on_later_attempt() -> None:
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
        "pipeline.idea_extractor._chat_completion",
        side_effect=["not-json", good],
    ):
        result = idea_extractor._process_chunk(
            segments, "S1", 1, 1, "k", "url", "m"
        )
    assert len(result) == 1
    assert result[0]["congressman_name"] == "García"
