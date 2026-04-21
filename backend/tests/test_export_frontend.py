"""Unit tests for export_frontend."""

import json
import pathlib
from unittest import mock

import pytest

from pipeline import export_frontend, idea_extractor, session_info_extractor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_result(
    session: str = "S1",
    date: str = "2026-01-01",
    summary: str = "Resumen.",
    participants: list[str] | None = None,
    themes: list[str] | None = None,
) -> session_info_extractor.SessionResult:
    return session_info_extractor.SessionResult(
        session=session,
        summary=summary,
        participants=participants or ["García López"],
        themes=themes or ["Economía"],
        youtube_url="https://youtube.com/watch?v=test",
        date=date,
    )


def _make_idea(
    congressman_name: str = "García López",
    session: str = "S1",
) -> idea_extractor.Idea:
    return idea_extractor.Idea(
        congressman_name=congressman_name,
        session=session,
        quote="Cita.",
        summary="Resumen.",
        start=10.0,
        end=30.0,
        tags=["Economía"],
        mentions=[],
        importance=0.5,
    )


def _write_session(
    base_dir: pathlib.Path,
    name: str,
    session_result: session_info_extractor.SessionResult,
    ideas: list[idea_extractor.Idea] | None = None,
) -> pathlib.Path:
    session_dir = base_dir / name
    session_dir.mkdir()
    (session_dir / "session_info.json").write_text(
        json.dumps(session_result), encoding="utf-8"
    )
    if ideas is not None:
        (session_dir / "ideas.json").write_text(
            json.dumps(ideas), encoding="utf-8"
        )
    return session_dir


# ---------------------------------------------------------------------------
# collect_sessions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_collect_sessions_loads_single_session(tmp_path: pathlib.Path) -> None:
    result = _make_session_result(session="S1")
    _write_session(tmp_path, "S1", result, ideas=[_make_idea()])

    sessions, ideas = export_frontend.collect_sessions(tmp_path)

    assert len(sessions) == 1
    assert sessions[0]["session"] == "S1"
    assert len(ideas) == 1


@pytest.mark.unit
def test_collect_sessions_skips_dirs_without_session_info(
    tmp_path: pathlib.Path,
) -> None:
    no_info_dir = tmp_path / "orphan"
    no_info_dir.mkdir()
    (no_info_dir / "ideas.json").write_text("[]", encoding="utf-8")

    sessions, ideas = export_frontend.collect_sessions(tmp_path)

    assert sessions == []
    assert ideas == []


@pytest.mark.unit
def test_collect_sessions_tolerates_missing_ideas_json(tmp_path: pathlib.Path) -> None:
    result = _make_session_result(session="S1")
    _write_session(tmp_path, "S1", result, ideas=None)

    sessions, ideas = export_frontend.collect_sessions(tmp_path)

    assert len(sessions) == 1
    assert ideas == []


@pytest.mark.unit
def test_collect_sessions_sorts_by_date_newest_first(tmp_path: pathlib.Path) -> None:
    _write_session(tmp_path, "old", _make_session_result(session="old", date="2024-01-01"))
    _write_session(tmp_path, "mid", _make_session_result(session="mid", date="2025-06-15"))
    _write_session(tmp_path, "new", _make_session_result(session="new", date="2026-04-20"))

    sessions, _ = export_frontend.collect_sessions(tmp_path)

    assert [s["session"] for s in sessions] == ["new", "mid", "old"]


@pytest.mark.unit
def test_collect_sessions_merges_ideas_from_all_sessions(
    tmp_path: pathlib.Path,
) -> None:
    _write_session(
        tmp_path, "S1", _make_session_result(session="S1"), ideas=[_make_idea(session="S1")]
    )
    _write_session(
        tmp_path, "S2", _make_session_result(session="S2"), ideas=[_make_idea(session="S2"), _make_idea(session="S2")]
    )

    _, ideas = export_frontend.collect_sessions(tmp_path)

    assert len(ideas) == 3


@pytest.mark.unit
def test_collect_sessions_skips_non_directories(tmp_path: pathlib.Path) -> None:
    (tmp_path / "random_file.txt").write_text("ignored", encoding="utf-8")
    _write_session(tmp_path, "S1", _make_session_result(session="S1"), ideas=[])

    sessions, _ = export_frontend.collect_sessions(tmp_path)

    assert len(sessions) == 1


# ---------------------------------------------------------------------------
# write_data_js
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_write_data_js_creates_file(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "data.js"
    export_frontend.write_data_js(
        [_make_session_result()], [_make_idea()], out
    )
    assert out.exists()


@pytest.mark.unit
def test_write_data_js_contains_sessions_export(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "data.js"
    export_frontend.write_data_js([_make_session_result(session="S-test")], [], out)
    content = out.read_text(encoding="utf-8")
    assert "export const SESSIONS" in content
    assert "S-test" in content


@pytest.mark.unit
def test_write_data_js_contains_ideas_export(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "data.js"
    export_frontend.write_data_js(
        [_make_session_result()], [_make_idea(congressman_name="Prueba")], out
    )
    content = out.read_text(encoding="utf-8")
    assert "export const IDEAS_DATA" in content
    assert "Prueba" in content


@pytest.mark.unit
def test_write_data_js_content_is_valid_after_stripping_exports(
    tmp_path: pathlib.Path,
) -> None:
    session = _make_session_result()
    idea = _make_idea()
    out = tmp_path / "data.js"
    export_frontend.write_data_js([session], [idea], out)

    content = out.read_text(encoding="utf-8")
    sessions_json = content.split("export const SESSIONS =")[1].split(";")[0].strip()
    json.loads(sessions_json)

    ideas_json = content.split("export const IDEAS_DATA =")[1].strip().rstrip(";").strip()
    json.loads(ideas_json)


@pytest.mark.unit
def test_write_data_js_overwrites_existing_file(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "data.js"
    out.write_text("old content", encoding="utf-8")
    export_frontend.write_data_js([_make_session_result()], [], out)
    assert "old content" not in out.read_text(encoding="utf-8")
