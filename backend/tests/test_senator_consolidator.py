"""Unit tests for senator_consolidator."""

import json
import pathlib
from unittest import mock

import pytest

from pipeline import idea_extractor, senator_consolidator, session_info_extractor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_idea(
    congressman_name: str = "García López",
    session: str = "S1",
    summary: str = "El legislador expone su posición.",
    tags: list[str] | None = None,
    start: float = 10.0,
) -> idea_extractor.Idea:
    return idea_extractor.Idea(
        congressman_name=congressman_name,
        session=session,
        quote="Cita de prueba.",
        summary=summary,
        start=start,
        end=start + 60.0,
        tags=tags if tags is not None else ["Economía"],
        mentions=[],
        importance=0.5,
    )


def _make_session_result(
    session: str = "S1",
    date: str = "2026-01-01",
) -> session_info_extractor.SessionResult:
    return session_info_extractor.SessionResult(
        session=session,
        summary="Resumen de prueba.",
        participants=["García López"],
        themes=["Economía"],
        youtube_url="https://youtube.com/watch?v=test",
        date=date,
    )


def _llm_payload(
    summary: str = "El senador defiende la educación pública.",
    positions: list[str] | None = None,
    themes: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "consolidated_summary": summary,
            "key_positions": positions or ["Posición A.", "Posición B.", "Posición C."],
            "main_themes": themes or ["Educación", "Presupuesto"],
        }
    )


# ---------------------------------------------------------------------------
# _format_ideas
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_format_ideas_empty_returns_empty_string() -> None:
    assert senator_consolidator._format_ideas([]) == ""


@pytest.mark.unit
def test_format_ideas_contains_session_and_summary() -> None:
    idea = _make_idea(session="Abril-15-2026", summary="El legislador debate la reforma.")
    result = senator_consolidator._format_ideas([idea])
    assert "Abril-15-2026" in result
    assert "El legislador debate la reforma." in result


@pytest.mark.unit
def test_format_ideas_contains_tags() -> None:
    idea = _make_idea(tags=["Salud", "Presupuesto"])
    result = senator_consolidator._format_ideas([idea])
    assert "Salud" in result
    assert "Presupuesto" in result


@pytest.mark.unit
def test_format_ideas_no_tags_shows_fallback() -> None:
    idea = _make_idea(tags=[])
    result = senator_consolidator._format_ideas([idea])
    assert "sin etiquetas" in result


@pytest.mark.unit
def test_format_ideas_numbered_sequentially() -> None:
    ideas = [_make_idea(session=f"S{i}") for i in range(3)]
    result = senator_consolidator._format_ideas(ideas)
    assert "[1]" in result
    assert "[2]" in result
    assert "[3]" in result


# ---------------------------------------------------------------------------
# consolidate_senator_position
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_consolidate_senator_position_raises_on_empty_ideas() -> None:
    with pytest.raises(ValueError, match="No ideas"):
        senator_consolidator.consolidate_senator_position([], "García López", "k")


@pytest.mark.unit
def test_consolidate_senator_position_returns_senator_position() -> None:
    ideas = [_make_idea()]
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value=_llm_payload(),
    ):
        result = senator_consolidator.consolidate_senator_position(
            ideas, "García López", "fake-key"
        )
    assert isinstance(result, dict)
    assert result["congressman_name"] == "García López"


@pytest.mark.unit
def test_consolidate_senator_position_parses_all_fields() -> None:
    ideas = [_make_idea(session="S1"), _make_idea(session="S2")]
    payload = _llm_payload(
        summary="Narrativa del senador.",
        positions=["Defiende A.", "Critica B."],
        themes=["Educación", "Salud"],
    )
    with mock.patch("pipeline.deepseek.chat_completion", return_value=payload):
        result = senator_consolidator.consolidate_senator_position(
            ideas, "García López", "fake-key"
        )

    assert result["consolidated_summary"] == "Narrativa del senador."
    assert result["key_positions"] == ["Defiende A.", "Critica B."]
    assert result["main_themes"] == ["Educación", "Salud"]
    assert result["ideas_count"] == 2
    assert sorted(result["sessions"]) == ["S1", "S2"]


@pytest.mark.unit
def test_consolidate_senator_position_passes_credentials() -> None:
    ideas = [_make_idea()]
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value=_llm_payload(),
    ) as mock_fn:
        senator_consolidator.consolidate_senator_position(
            ideas,
            "García López",
            api_key="my-key",
            base_url="https://custom.api.com",
            model="deepseek-reasoner",
        )

    call_kwargs = mock_fn.call_args.kwargs
    assert call_kwargs["api_key"] == "my-key"
    assert call_kwargs["base_url"] == "https://custom.api.com"
    assert call_kwargs["model"] == "deepseek-reasoner"


@pytest.mark.unit
def test_consolidate_senator_position_retries_on_bad_json() -> None:
    ideas = [_make_idea()]
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        side_effect=["not-json", _llm_payload()],
    ) as mock_fn:
        result = senator_consolidator.consolidate_senator_position(
            ideas, "García López", "fake-key"
        )

    assert mock_fn.call_count == 2
    assert result["consolidated_summary"] != ""


@pytest.mark.unit
def test_consolidate_senator_position_raises_after_max_retries() -> None:
    ideas = [_make_idea()]
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        return_value="not-json",
    ):
        with pytest.raises(RuntimeError, match="failed after"):
            senator_consolidator.consolidate_senator_position(
                ideas, "García López", "fake-key"
            )


@pytest.mark.unit
def test_consolidate_senator_position_retries_on_incomplete_data() -> None:
    incomplete = json.dumps({"consolidated_summary": "Solo esto."})
    ideas = [_make_idea()]
    with mock.patch(
        "pipeline.deepseek.chat_completion",
        side_effect=[incomplete, _llm_payload()],
    ) as mock_fn:
        result = senator_consolidator.consolidate_senator_position(
            ideas, "García López", "fake-key"
        )

    assert mock_fn.call_count == 2
    assert result["key_positions"]


# ---------------------------------------------------------------------------
# save_senator_position / load_senator_position
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_save_and_load_senator_position_roundtrip(tmp_path: pathlib.Path) -> None:
    position = senator_consolidator.SenatorPosition(
        congressman_name="García López",
        consolidated_summary="Resumen de prueba.",
        key_positions=["Posición A.", "Posición B."],
        main_themes=["Educación", "Salud"],
        ideas_count=5,
        sessions=["S1", "S2"],
    )
    path = tmp_path / "position.json"
    senator_consolidator.save_senator_position(position, path)
    loaded = senator_consolidator.load_senator_position(path)

    assert loaded == position


@pytest.mark.unit
def test_save_senator_position_writes_valid_json(tmp_path: pathlib.Path) -> None:
    position = senator_consolidator.SenatorPosition(
        congressman_name="García López",
        consolidated_summary="Resumen.",
        key_positions=["Pos A."],
        main_themes=["Economía"],
        ideas_count=1,
        sessions=["S1"],
    )
    path = tmp_path / "position.json"
    senator_consolidator.save_senator_position(position, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["congressman_name"] == "García López"


# ---------------------------------------------------------------------------
# consolidate_all_senators
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_consolidate_all_senators_skips_senators_with_no_ideas(
    tmp_path: pathlib.Path,
) -> None:
    senators = ["García López", "Pérez Rojas"]
    ideas = [_make_idea(congressman_name="García López")]
    sessions = [_make_session_result(session="S1", date="2026-01-01")]

    with (
        mock.patch(
            "pipeline.senator_consolidator.export_frontend.collect_sessions",
            return_value=(sessions, ideas),
        ),
        mock.patch(
            "pipeline.deepseek.chat_completion",
            return_value=_llm_payload(),
        ),
    ):
        results = senator_consolidator.consolidate_all_senators(tmp_path, senators, "k")

    assert "García López" in results
    assert "Pérez Rojas" not in results


@pytest.mark.unit
def test_consolidate_all_senators_returns_position_per_senator(
    tmp_path: pathlib.Path,
) -> None:
    senators = ["García López", "Pérez Rojas"]
    ideas = [
        _make_idea(congressman_name="García López", session="S1"),
        _make_idea(congressman_name="Pérez Rojas", session="S1"),
    ]
    sessions = [_make_session_result(session="S1", date="2026-01-01")]

    with (
        mock.patch(
            "pipeline.senator_consolidator.export_frontend.collect_sessions",
            return_value=(sessions, ideas),
        ),
        mock.patch(
            "pipeline.deepseek.chat_completion",
            return_value=_llm_payload(),
        ),
    ):
        results = senator_consolidator.consolidate_all_senators(tmp_path, senators, "k")

    assert len(results) == 2


@pytest.mark.unit
def test_consolidate_all_senators_respects_max_ideas(tmp_path: pathlib.Path) -> None:
    senators = ["García López"]
    ideas = [
        _make_idea(congressman_name="García López", session="S1", start=float(i))
        for i in range(10)
    ]
    sessions = [_make_session_result(session="S1", date="2026-01-01")]

    captured: list[list[idea_extractor.Idea]] = []

    def _spy_consolidate(
        ideas_arg: list[idea_extractor.Idea],
        congressman_name: str,
        api_key: str,
        **kwargs: object,
    ) -> senator_consolidator.SenatorPosition:
        captured.append(ideas_arg)
        return senator_consolidator.SenatorPosition(
            congressman_name=congressman_name,
            consolidated_summary="Test.",
            key_positions=["P1."],
            main_themes=["T1"],
            ideas_count=len(ideas_arg),
            sessions=["S1"],
        )

    with (
        mock.patch(
            "pipeline.senator_consolidator.export_frontend.collect_sessions",
            return_value=(sessions, ideas),
        ),
        mock.patch(
            "pipeline.senator_consolidator.consolidate_senator_position",
            side_effect=_spy_consolidate,
        ),
    ):
        senator_consolidator.consolidate_all_senators(tmp_path, senators, "k", max_ideas=3)

    assert len(captured[0]) == 3


@pytest.mark.unit
def test_consolidate_all_senators_selects_most_recent_ideas(
    tmp_path: pathlib.Path,
) -> None:
    senators = ["García López"]
    old_idea = _make_idea(congressman_name="García López", session="S-old", start=0.0)
    new_idea = _make_idea(congressman_name="García López", session="S-new", start=0.0)
    sessions = [
        _make_session_result(session="S-old", date="2025-01-01"),
        _make_session_result(session="S-new", date="2026-06-01"),
    ]

    captured: list[list[idea_extractor.Idea]] = []

    def _spy_consolidate(
        ideas_arg: list[idea_extractor.Idea],
        congressman_name: str,
        api_key: str,
        **kwargs: object,
    ) -> senator_consolidator.SenatorPosition:
        captured.append(ideas_arg)
        return senator_consolidator.SenatorPosition(
            congressman_name=congressman_name,
            consolidated_summary="Test.",
            key_positions=["P1."],
            main_themes=["T1"],
            ideas_count=len(ideas_arg),
            sessions=[i["session"] for i in ideas_arg],
        )

    with (
        mock.patch(
            "pipeline.senator_consolidator.export_frontend.collect_sessions",
            return_value=(sessions, [old_idea, new_idea]),
        ),
        mock.patch(
            "pipeline.senator_consolidator.consolidate_senator_position",
            side_effect=_spy_consolidate,
        ),
    ):
        senator_consolidator.consolidate_all_senators(
            tmp_path, senators, "k", max_ideas=1
        )

    assert captured[0][0]["session"] == "S-new"


@pytest.mark.unit
def test_consolidate_all_senators_continues_on_llm_failure(
    tmp_path: pathlib.Path,
) -> None:
    senators = ["García López", "Pérez Rojas"]
    ideas = [
        _make_idea(congressman_name="García López", session="S1"),
        _make_idea(congressman_name="Pérez Rojas", session="S1"),
    ]
    sessions = [_make_session_result(session="S1", date="2026-01-01")]

    call_count = 0

    def _fail_first(
        ideas_arg: list[idea_extractor.Idea],
        congressman_name: str,
        api_key: str,
        **kwargs: object,
    ) -> senator_consolidator.SenatorPosition:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("LLM failure")
        return senator_consolidator.SenatorPosition(
            congressman_name=congressman_name,
            consolidated_summary="OK.",
            key_positions=["P1."],
            main_themes=["T1"],
            ideas_count=1,
            sessions=["S1"],
        )

    with (
        mock.patch(
            "pipeline.senator_consolidator.export_frontend.collect_sessions",
            return_value=(sessions, ideas),
        ),
        mock.patch(
            "pipeline.senator_consolidator.consolidate_senator_position",
            side_effect=_fail_first,
        ),
    ):
        results = senator_consolidator.consolidate_all_senators(tmp_path, senators, "k")

    assert len(results) == 1
