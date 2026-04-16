"""Unit tests for review_session_info."""

import pathlib
from unittest import mock

import pytest

from pipeline import review_session_info, session_info_extractor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    date: str = "2026-04-15",
    youtube_url: str = "https://www.youtube.com/watch?v=abc123",
    participants: list[str] | None = None,
) -> session_info_extractor.SessionResult:
    return session_info_extractor.SessionResult(
        session="S1",
        summary="Resumen de prueba.",
        participants=participants if participants is not None else [],
        themes=["Tema1"],
        youtube_url=youtube_url,
        date=date,
    )


# ---------------------------------------------------------------------------
# report_date
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_date_valid(capsys: pytest.CaptureFixture[str]) -> None:
    review_session_info.report_date(_make_result(date="2026-04-15"))
    assert "OK" in capsys.readouterr().out


@pytest.mark.unit
def test_date_valid_shows_iso(capsys: pytest.CaptureFixture[str]) -> None:
    review_session_info.report_date(_make_result(date="2026-01-01"))
    assert "2026-01-01" in capsys.readouterr().out


@pytest.mark.unit
def test_date_empty(capsys: pytest.CaptureFixture[str]) -> None:
    review_session_info.report_date(_make_result(date=""))
    assert "ERROR" in capsys.readouterr().out


@pytest.mark.unit
def test_date_invalid_format(capsys: pytest.CaptureFixture[str]) -> None:
    review_session_info.report_date(_make_result(date="15-04-2026"))
    out = capsys.readouterr().out
    assert "ERROR" in out
    assert "15-04-2026" in out


@pytest.mark.unit
def test_date_invalid_text(capsys: pytest.CaptureFixture[str]) -> None:
    review_session_info.report_date(_make_result(date="Abril 15 de 2026"))
    assert "ERROR" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# report_youtube_url
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_youtube_url_present(capsys: pytest.CaptureFixture[str]) -> None:
    review_session_info.report_youtube_url(
        _make_result(youtube_url="https://www.youtube.com/watch?v=abc123")
    )
    out = capsys.readouterr().out
    assert "OK" in out
    assert "abc123" in out


@pytest.mark.unit
def test_youtube_url_empty(capsys: pytest.CaptureFixture[str]) -> None:
    review_session_info.report_youtube_url(_make_result(youtube_url=""))
    assert "ERROR" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# report_unrecognized_participants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_participants_all_recognized(capsys: pytest.CaptureFixture[str]) -> None:
    result = _make_result(participants=["García López", "Pérez Rojas"])
    senators = ["García López", "Pérez Rojas", "Otro Senador"]
    review_session_info.report_unrecognized_participants(result, senators)
    assert "todos los participantes" in capsys.readouterr().out


@pytest.mark.unit
def test_participants_some_unrecognized(capsys: pytest.CaptureFixture[str]) -> None:
    result = _make_result(participants=["García López", "Fulano De Tal"])
    senators = ["García López"]
    review_session_info.report_unrecognized_participants(result, senators)
    out = capsys.readouterr().out
    assert "Fulano De Tal" in out
    assert "García López" not in out or "✓" in out


@pytest.mark.unit
def test_participants_recognized_marked_with_checkmark(capsys: pytest.CaptureFixture[str]) -> None:
    result = _make_result(participants=["García López"])
    senators = ["García López"]
    review_session_info.report_unrecognized_participants(result, senators)
    assert "✓" in capsys.readouterr().out


@pytest.mark.unit
def test_participants_none_in_list(capsys: pytest.CaptureFixture[str]) -> None:
    result = _make_result(participants=[])
    senators = ["García López"]
    review_session_info.report_unrecognized_participants(result, senators)
    # No names to show — should not crash and should not print any name
    out = capsys.readouterr().out
    assert "García López" not in out


@pytest.mark.unit
def test_participants_match_is_case_sensitive(capsys: pytest.CaptureFixture[str]) -> None:
    result = _make_result(participants=["garcía lópez"])
    senators = ["García López"]
    review_session_info.report_unrecognized_participants(result, senators)
    # Lowercase variant should appear as unrecognized
    assert "garcía lópez" in capsys.readouterr().out


@pytest.mark.unit
def test_participants_counts_in_header(capsys: pytest.CaptureFixture[str]) -> None:
    result = _make_result(participants=["García López", "Fulano De Tal", "Mengano"])
    senators = ["García López"]
    review_session_info.report_unrecognized_participants(result, senators)
    out = capsys.readouterr().out
    assert "1 reconocidos" in out
    assert "2 no encontrados" in out


# ---------------------------------------------------------------------------
# review (integration of all checks)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_review_calls_all_reports(tmp_path: pathlib.Path) -> None:
    result = _make_result()
    senators = ["García López"]
    session_info_path = tmp_path / "session_info.json"

    with (
        mock.patch(
            "pipeline.review_session_info.session_info_extractor.load_session_result",
            return_value=result,
        ),
        mock.patch(
            "pipeline.review_session_info.senate_scraper.fetch_senators",
            return_value=senators,
        ),
        mock.patch("pipeline.review_session_info.report_date") as mock_date,
        mock.patch("pipeline.review_session_info.report_youtube_url") as mock_url,
        mock.patch(
            "pipeline.review_session_info.report_unrecognized_participants"
        ) as mock_participants,
    ):
        review_session_info.review(session_info_path)

    mock_date.assert_called_once_with(result)
    mock_url.assert_called_once_with(result)
    mock_participants.assert_called_once_with(result, senators)


@pytest.mark.unit
def test_review_passes_senators_cache_path(tmp_path: pathlib.Path) -> None:
    cache = tmp_path / "senators.json"
    session_info_path = tmp_path / "session_info.json"

    with (
        mock.patch(
            "pipeline.review_session_info.session_info_extractor.load_session_result",
            return_value=_make_result(),
        ),
        mock.patch(
            "pipeline.review_session_info.senate_scraper.fetch_senators",
            return_value=[],
        ) as mock_fetch,
        mock.patch("pipeline.review_session_info.report_date"),
        mock.patch("pipeline.review_session_info.report_youtube_url"),
        mock.patch("pipeline.review_session_info.report_unrecognized_participants"),
    ):
        review_session_info.review(session_info_path, senators_cache_path=cache)

    mock_fetch.assert_called_once_with(cache_path=cache)
