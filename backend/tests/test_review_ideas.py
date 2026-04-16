"""Unit tests for review_ideas."""

import pathlib
from unittest import mock

import pytest

from pipeline import idea_extractor, review_ideas


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_idea(
    congressman_name: str = "García López",
    start: float = 10.0,
    end: float = 30.0,
    summary: str = "El legislador expone su posición.",
) -> idea_extractor.Idea:
    return idea_extractor.Idea(
        congressman_name=congressman_name,
        session="S1",
        quote="Cita de prueba.",
        summary=summary,
        start=start,
        end=end,
        tags=[],
        mentions=[],
        importance=0.5,
    )


# ---------------------------------------------------------------------------
# report_unknown_speakers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unknown_speakers_none(capsys: pytest.CaptureFixture[str]) -> None:
    ideas = [_make_idea("García López"), _make_idea("Pérez Rojas")]
    review_ideas.report_unknown_speakers(ideas)
    assert "ninguna" in capsys.readouterr().out


@pytest.mark.unit
def test_unknown_speakers_detected(capsys: pytest.CaptureFixture[str]) -> None:
    ideas = [_make_idea("Desconocido", start=60.0, end=120.0)]
    review_ideas.report_unknown_speakers(ideas)
    out = capsys.readouterr().out
    assert "60.0s" in out
    assert "120.0s" in out


@pytest.mark.unit
def test_unknown_speakers_count(capsys: pytest.CaptureFixture[str]) -> None:
    ideas = [_make_idea("Desconocido")] * 3 + [_make_idea("García López")]
    review_ideas.report_unknown_speakers(ideas)
    assert "3 ideas" in capsys.readouterr().out


@pytest.mark.unit
def test_unknown_speakers_exact_match_only(capsys: pytest.CaptureFixture[str]) -> None:
    # "Desconocido Fulano" should NOT be counted as unknown
    ideas = [_make_idea("Desconocido Fulano")]
    review_ideas.report_unknown_speakers(ideas)
    assert "ninguna" in capsys.readouterr().out


@pytest.mark.unit
def test_unknown_speakers_summary_truncated(capsys: pytest.CaptureFixture[str]) -> None:
    long_summary = "X" * 200
    ideas = [_make_idea("Desconocido", summary=long_summary)]
    review_ideas.report_unknown_speakers(ideas)
    out = capsys.readouterr().out
    assert "…" in out
    assert "X" * 200 not in out


# ---------------------------------------------------------------------------
# report_unrecognized_names
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unrecognized_names_all_match(capsys: pytest.CaptureFixture[str]) -> None:
    ideas = [_make_idea("García López"), _make_idea("Pérez Rojas")]
    senators = ["García López", "Pérez Rojas"]
    review_ideas.report_unrecognized_names(ideas, senators)
    assert "todos los nombres" in capsys.readouterr().out


@pytest.mark.unit
def test_unrecognized_names_detected(capsys: pytest.CaptureFixture[str]) -> None:
    ideas = [_make_idea("García López"), _make_idea("Fulano De Tal")]
    senators = ["García López"]
    review_ideas.report_unrecognized_names(ideas, senators)
    out = capsys.readouterr().out
    assert "Fulano De Tal" in out
    assert "García López" not in out


@pytest.mark.unit
def test_unrecognized_names_desconocido_excluded(capsys: pytest.CaptureFixture[str]) -> None:
    ideas = [_make_idea("Desconocido")]
    senators: list[str] = []
    review_ideas.report_unrecognized_names(ideas, senators)
    assert "Desconocido" not in capsys.readouterr().out


@pytest.mark.unit
def test_unrecognized_names_match_is_case_sensitive(capsys: pytest.CaptureFixture[str]) -> None:
    ideas = [_make_idea("garcía lópez")]
    senators = ["García López"]
    review_ideas.report_unrecognized_names(ideas, senators)
    # lowercase variant does not match — should appear as unrecognized
    assert "garcía lópez" in capsys.readouterr().out


@pytest.mark.unit
def test_unrecognized_names_count(capsys: pytest.CaptureFixture[str]) -> None:
    ideas = [_make_idea("Fulano De Tal")] * 4
    senators: list[str] = []
    review_ideas.report_unrecognized_names(ideas, senators)
    assert "4 ideas" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# review (integration of both checks)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_review_calls_both_reports(tmp_path: pathlib.Path) -> None:
    ideas = [_make_idea("Desconocido"), _make_idea("Fulano De Tal")]
    senators = ["García López"]
    ideas_path = tmp_path / "ideas.json"

    with (
        mock.patch("pipeline.review_ideas.idea_extractor.load_ideas", return_value=ideas),
        mock.patch("pipeline.review_ideas.senate_scraper.fetch_senators", return_value=senators),
        mock.patch("pipeline.review_ideas.report_unknown_speakers") as mock_unknown,
        mock.patch("pipeline.review_ideas.report_unrecognized_names") as mock_names,
    ):
        review_ideas.review(ideas_path)

    mock_unknown.assert_called_once_with(ideas)
    mock_names.assert_called_once_with(ideas, senators)


@pytest.mark.unit
def test_review_passes_senators_cache_path(tmp_path: pathlib.Path) -> None:
    cache = tmp_path / "senators.json"
    ideas_path = tmp_path / "ideas.json"

    with (
        mock.patch("pipeline.review_ideas.idea_extractor.load_ideas", return_value=[]),
        mock.patch("pipeline.review_ideas.senate_scraper.fetch_senators", return_value=[]) as mock_fetch,
        mock.patch("pipeline.review_ideas.report_unknown_speakers"),
        mock.patch("pipeline.review_ideas.report_unrecognized_names"),
    ):
        review_ideas.review(ideas_path, senators_cache_path=cache)

    mock_fetch.assert_called_once_with(cache_path=cache)
