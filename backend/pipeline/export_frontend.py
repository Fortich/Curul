"""Exports session info and ideas from pipeline outputs to a frontend data.js file."""

import json
import logging
import pathlib

from pipeline import idea_extractor, session_info_extractor

logger = logging.getLogger(__name__)

_JS_TEMPLATE = """\
export const SESSIONS = {sessions};

export const IDEAS_DATA =
  {ideas};
"""


def collect_sessions(
    output_dir: pathlib.Path,
) -> tuple[list[session_info_extractor.SessionResult], list[idea_extractor.Idea]]:
    """Scans *output_dir* for session subdirectories and loads their data.

    Each subdirectory is expected to contain:
        - session_info.json  (required)
        - ideas.json         (optional)

    Sessions are sorted by the ``date`` field (ISO format), most recent first.
    Subdirectories missing ``session_info.json`` are skipped with a warning.

    Args:
        output_dir: Root directory containing one subdirectory per session.

    Returns:
        A tuple of (sessions, ideas) where sessions is a list of SessionResult
        and ideas is the flat list of all ideas from all sessions.
    """
    sessions: list[session_info_extractor.SessionResult] = []
    all_ideas: list[idea_extractor.Idea] = []

    for session_dir in sorted(output_dir.iterdir()):
        if not session_dir.is_dir():
            continue

        session_info_path = session_dir / "session_info.json"
        if not session_info_path.exists():
            logger.warning("Skipping %s — no session_info.json", session_dir.name)
            continue

        result = session_info_extractor.load_session_result(session_info_path)
        sessions.append(result)
        logger.info("Loaded session: %s", result["session"])

        ideas_path = session_dir / "ideas.json"
        if ideas_path.exists():
            ideas = idea_extractor.load_ideas(ideas_path)
            all_ideas.extend(ideas)
            logger.info("  + %d ideas", len(ideas))
        else:
            logger.warning("  No ideas.json in %s", session_dir.name)

    sessions.sort(key=lambda s: s.get("date", ""), reverse=True)
    return sessions, all_ideas


def write_data_js(
    sessions: list[session_info_extractor.SessionResult],
    ideas: list[idea_extractor.Idea],
    output_path: pathlib.Path,
) -> None:
    """Writes the frontend ``data.js`` file from sessions and ideas.

    Args:
        sessions: List of SessionResult objects (will be sorted by date, newest first).
        ideas: Flat list of all ideas across all sessions.
        output_path: Destination path for the generated ``data.js`` file.
    """
    sessions_json = json.dumps(sessions, ensure_ascii=False, indent=2)
    ideas_json = json.dumps(ideas, ensure_ascii=False, indent=2)

    content = _JS_TEMPLATE.format(sessions=sessions_json, ideas=ideas_json)
    output_path.write_text(content, encoding="utf-8")
    logger.info(
        "data.js written to %s (%d sessions, %d ideas)",
        output_path,
        len(sessions),
        len(ideas),
    )
