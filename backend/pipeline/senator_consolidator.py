"""Consolidates a senator's position across a set of extracted ideas."""

# ruff: noqa: E501 — long lines are LLM prompt content, not code

import json
import logging
import pathlib
from typing import TypedDict

from pipeline import deepseek, export_frontend, idea_extractor

logger = logging.getLogger(__name__)

_MAX_RETRIES: int = 3


class SenatorPosition(TypedDict):
    """Consolidated position of a senator across a given set of ideas."""

    congressman_name: str
    consolidated_summary: str
    key_positions: list[str]
    main_themes: list[str]
    ideas_count: int
    sessions: list[str]


_SYSTEM_PROMPT = """\
Eres un asistente especializado en análisis legislativo colombiano.
Se te proporcionará un conjunto de intervenciones resumidas de un senador extraídas de sesiones parlamentarias.

Tu tarea es sintetizar la posición global del senador a partir de esas intervenciones:

1. consolidated_summary: un párrafo analítico-periodístico (3 a 5 oraciones) que describa la postura \
política general del senador según las ideas dadas. Identifica sus prioridades, los ejes de debate en \
que participa activamente, sus posiciones en conflicto con otros actores y el tono general de sus intervenciones. \
Construye una narrativa coherente; no listes temas mecánicamente.

2. key_positions: entre 3 y 7 posiciones concretas del senador, cada una expresada en una oración \
concisa. Deben representar sus posturas más claras o frecuentes dentro del conjunto dado.

3. main_themes: entre 3 y 8 etiquetas temáticas (1-3 palabras, en español, con mayúscula inicial) \
que cubran los temas en los que el senador concentra sus intervenciones.

Responde ÚNICAMENTE con un JSON válido (sin texto adicional):
{
  "consolidated_summary": "Texto del resumen...",
  "key_positions": ["Posición 1.", "Posición 2.", ...],
  "main_themes": ["Tema1", "Tema2", ...]
}"""


def _format_ideas(ideas: list[idea_extractor.Idea]) -> str:
    """Formats a list of ideas into a text block suitable for the LLM prompt."""
    lines: list[str] = []
    for i, idea in enumerate(ideas, start=1):
        tags = ", ".join(idea["tags"]) if idea["tags"] else "sin etiquetas"
        lines.append(
            f"[{i}] Sesión: {idea['session']} | Temas: {tags}\n"
            f"    {idea['summary']}"
        )
    return "\n\n".join(lines)


def consolidate_senator_position(
    ideas: list[idea_extractor.Idea],
    congressman_name: str,
    api_key: str,
    base_url: str = deepseek.BASE_URL,
    model: str = deepseek.MODEL,
) -> SenatorPosition:
    """Summarizes the political position of a senator from a list of their ideas.

    Args:
        ideas: Ideas attributed to the senator (already filtered by caller).
        congressman_name: Display name for the senator in the result.
        api_key: Authentication key for the LLM API.
        base_url: Base URL of the OpenAI-compatible API.
        model: Model identifier (defaults to the fast model).

    Returns:
        A SenatorPosition with summary, key positions, and themes.

    Raises:
        ValueError: If the ideas list is empty.
        RuntimeError: If the LLM fails to return valid data after all retries.
    """
    if not ideas:
        raise ValueError(f"No ideas provided for senator '{congressman_name}'")

    sessions = sorted({idea["session"] for idea in ideas})
    formatted = _format_ideas(ideas)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Senador: {congressman_name}\n"
                f"Número de intervenciones: {len(ideas)}\n"
                f"Sesiones: {', '.join(sessions)}\n\n"
                f"Intervenciones:\n\n{formatted}"
            ),
        },
    ]

    for attempt in range(1, _MAX_RETRIES + 1):
        raw = deepseek.chat_completion(
            messages=messages,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.1,
        )
        try:
            data = json.loads(raw)
            consolidated_summary = str(data.get("consolidated_summary", "")).strip()
            key_positions = [str(p) for p in data.get("key_positions", []) if str(p).strip()]
            main_themes = [str(t) for t in data.get("main_themes", []) if str(t).strip()]
            if consolidated_summary and key_positions and main_themes:
                logger.info(
                    "consolidate_senator_position: attempt %d/%d succeeded for '%s'",
                    attempt, _MAX_RETRIES, congressman_name,
                )
                return SenatorPosition(
                    congressman_name=congressman_name,
                    consolidated_summary=consolidated_summary,
                    key_positions=key_positions,
                    main_themes=main_themes,
                    ideas_count=len(ideas),
                    sessions=sessions,
                )
            raise ValueError(f"Incomplete data: {data}")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "consolidate_senator_position: attempt %d/%d failed: %s",
                attempt, _MAX_RETRIES, exc,
            )

    raise RuntimeError(
        f"consolidate_senator_position: failed after {_MAX_RETRIES} attempts for '{congressman_name}'"
    )


def save_senator_position(result: SenatorPosition, output_path: pathlib.Path) -> None:
    """Saves a SenatorPosition to a JSON file."""
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("SenatorPosition saved to: %s", output_path)


def load_senator_position(input_path: pathlib.Path) -> SenatorPosition:
    """Loads a SenatorPosition from a JSON file."""
    data = json.loads(input_path.read_text(encoding="utf-8"))
    logger.info("SenatorPosition loaded from: %s", input_path)
    return SenatorPosition(
        congressman_name=data["congressman_name"],
        consolidated_summary=data["consolidated_summary"],
        key_positions=data["key_positions"],
        main_themes=data["main_themes"],
        ideas_count=data["ideas_count"],
        sessions=data["sessions"],
    )


_MAX_IDEAS_PER_SENATOR: int = 50


def consolidate_all_senators(
    output_dir: pathlib.Path,
    senators: list[str],
    api_key: str,
    base_url: str = deepseek.BASE_URL,
    model: str = deepseek.MODEL,
    max_ideas: int = _MAX_IDEAS_PER_SENATOR,
) -> dict[str, SenatorPosition]:
    """Consolidates positions for every senator in *senators* that has at least one idea.

    Loads all sessions and ideas from *output_dir*, selects the most recent
    ideas (up to *max_ideas*) per senator, and calls consolidate_senator_position
    for each senator with at least one idea.

    Ideas are ordered by session date (most recent first) then by start timestamp
    descending before the per-senator limit is applied.

    Args:
        output_dir: Root directory containing one subdirectory per session,
            each with session_info.json and ideas.json.
        senators: Canonical senator names in «Apellido(s) Nombre(s)» format,
            typically loaded from senators_cache.json.
        api_key: Authentication key for the LLM API.
        base_url: Base URL of the OpenAI-compatible API.
        model: Model identifier.
        max_ideas: Maximum number of ideas (most recent) to send per senator.

    Returns:
        A dict mapping congressman_name → SenatorPosition for every senator
        with at least one idea in *output_dir*.
    """
    sessions, all_ideas = export_frontend.collect_sessions(output_dir)

    session_date: dict[str, str] = {s["session"]: s.get("date", "") for s in sessions}

    ideas_by_senator: dict[str, list[idea_extractor.Idea]] = {}
    for idea in all_ideas:
        name = idea["congressman_name"]
        ideas_by_senator.setdefault(name, []).append(idea)

    senator_set = set(senators)
    results: dict[str, SenatorPosition] = {}

    for senator in senators:
        raw_ideas = ideas_by_senator.get(senator)
        if not raw_ideas:
            logger.debug("No ideas found for senator '%s', skipping", senator)
            continue

        sorted_ideas = sorted(
            raw_ideas,
            key=lambda i: (session_date.get(i["session"], ""), i["start"]),
            reverse=True,
        )
        selected = sorted_ideas[:max_ideas]

        logger.info(
            "Consolidating '%s': %d idea(s) selected (out of %d)",
            senator, len(selected), len(raw_ideas),
        )
        try:
            results[senator] = consolidate_senator_position(
                selected, senator, api_key, base_url=base_url, model=model
            )
        except RuntimeError as exc:
            logger.error("Failed to consolidate '%s': %s", senator, exc)

    unknown_with_ideas = {
        name for name in ideas_by_senator if name not in senator_set and ideas_by_senator[name]
    }
    if unknown_with_ideas:
        logger.warning(
            "%d name(s) with ideas are not in the senator list: %s",
            len(unknown_with_ideas),
            ", ".join(sorted(unknown_with_ideas)),
        )

    logger.info(
        "consolidate_all_senators: %d/%d senators consolidated",
        len(results), len(senators),
    )
    return results
