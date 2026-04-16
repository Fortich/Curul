"""Extracts session-level metadata (participants, themes) and summary."""

# ruff: noqa: E501 — long lines are LLM prompt content, not code

import json
import logging
import pathlib
from typing import TypedDict

from pipeline import deepseek, transcriber

logger = logging.getLogger(__name__)

_MAX_RETRIES: int = 3


class SessionResult(TypedDict):
    """Session-level result: identifier, executive summary, participants, themes, URL, and date."""

    session: str
    summary: str
    participants: list[str]
    themes: list[str]
    youtube_url: str
    date: str


_SYSTEM_PROMPT_BASE = """\
Eres un asistente especializado en análisis de sesiones legislativas colombianas.
Se te proporcionará la transcripción {scope} de una sesión parlamentaria.

Tu tarea es identificar:
1. participants: todos los legisladores o funcionarios que toman la palabra. Usa el nombre completo sin títulos honoríficos (sin "Senador", "Representante", "Honorable", "doctor", etc.). Omite a quienes no puedas identificar con nombre completo.
2. themes: entre 5 y 15 etiquetas temáticas que cubran los temas principales debatidos. Deben ser concisas (1-3 palabras, en español) y con mayúscula inicial (ej: "Fuerza pública", "Política exterior", "Presupuesto militar").
3. summary: un resumen ejecutivo en español (entre 3 y 6 oraciones) con tono analítico-periodístico. Debe identificar los ejes de debate más relevantes, las posiciones en conflicto, las propuestas concretas que emergieron y el clima político de la sesión. Evita listar temas; construye una narrativa coherente.

Responde ÚNICAMENTE con un JSON válido (sin texto adicional):
{{
  "participants": ["Nombre Apellido", ...],
  "themes": ["tema1", "tema2", ...],
  "summary": "Texto del resumen..."
}}"""

_SYNTHESIS_SYSTEM_PROMPT = """\
Eres un asistente especializado en análisis de sesiones legislativas colombianas.
Se te proporcionarán varios resúmenes parciales de distintas partes de una sesión parlamentaria.

Tu tarea es redactar un único resumen ejecutivo en español (entre 3 y 6 oraciones) con tono analítico-periodístico \
que integre de forma coherente los ejes de debate más relevantes, las posiciones en conflicto, \
las propuestas concretas que emergieron y el clima político de la sesión. \
Evita listar temas; construye una narrativa coherente.

Responde ÚNICAMENTE con el texto del resumen, sin JSON ni ningún otro formato."""

_SENATORS_SECTION = """\

Lista de senadores actuales (formato oficial «Apellido(s) Nombre(s)»):
{senator_list}

Cuando identifiques un participante que coincida (aunque sea aproximadamente,
considerando errores de transcripción) con algún senador de la lista anterior,
usa el formato oficial «Apellido(s) Nombre(s)» como string en "participants"."""


_MAX_CHARS_PER_CHUNK: int = 200_000


def _build_system_prompt(senators: list[str] | None, *, partial: bool = False) -> str:
    """Returns the system prompt, optionally with the senators reference list."""
    scope = "parcial" if partial else "completa"
    base = _SYSTEM_PROMPT_BASE.format(scope=scope)
    if not senators:
        return base
    senator_list = "\n".join(f"- {s}" for s in senators)
    return base + _SENATORS_SECTION.format(senator_list=senator_list)


def _format_text(segments: list[transcriber.Segment]) -> str:
    """Joins segment texts into plain prose, without timestamps."""
    return "\n".join(seg.text.strip() for seg in segments)


def _chunk_segments(
    segments: list[transcriber.Segment],
    max_chars: int = _MAX_CHARS_PER_CHUNK,
) -> list[list[transcriber.Segment]]:
    """Splits segments into chunks whose plain text stays within *max_chars*."""
    chunks: list[list[transcriber.Segment]] = []
    current: list[transcriber.Segment] = []
    current_chars = 0
    for seg in segments:
        line = seg.text.strip() + "\n"
        if current and current_chars + len(line) > max_chars:
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(seg)
        current_chars += len(line)
    if current:
        chunks.append(current)
    return chunks


def _extract_chunk(
    segments: list[transcriber.Segment],
    session: str,
    api_key: str,
    base_url: str,
    model: str,
    senators: list[str] | None,
    chunk_index: int,
    total_chunks: int,
) -> tuple[list[str], list[str], str]:
    """Runs one LLM call for a chunk of segments.

    Returns:
        A (participants, themes, summary) tuple for that chunk.
    """
    partial = total_chunks > 1
    text = _format_text(segments)
    chunk_note = (
        f"(Parte {chunk_index} de {total_chunks} de la sesión)\n\n" if partial else ""
    )
    messages = [
        {"role": "system", "content": _build_system_prompt(senators, partial=partial)},
        {
            "role": "user",
            "content": f"Sesión: {session}\n\n{chunk_note}Transcripción:\n{text}",
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
            participants = [str(p) for p in data.get("participants", []) if str(p).strip()]
            themes = [str(t) for t in data.get("themes", []) if str(t).strip()]
            summary = str(data.get("summary", "")).strip()
            if participants and themes and summary:
                logger.info(
                    "Chunk %d/%d attempt %d/%d worked, summary: %s",
                    chunk_index, total_chunks, attempt, _MAX_RETRIES, summary,
                )
                return participants, themes, summary
            raise ValueError(f"Incomplete data: {data}")
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Chunk %d/%d attempt %d/%d failed: %s",
                chunk_index, total_chunks, attempt, _MAX_RETRIES, exc,
            )
    raise RuntimeError(
        f"extract_session_info: chunk {chunk_index}/{total_chunks} failed after {_MAX_RETRIES} attempts"
    )


def _synthesize_summary(
    partial_summaries: list[str],
    session: str,
    api_key: str,
    base_url: str,
    model: str,
) -> str:
    """Merges partial summaries into a single coherent executive summary via LLM."""
    parts = "\n\n".join(
        f"Parte {i}:\n{s}" for i, s in enumerate(partial_summaries, start=1)
    )
    messages = [
        {"role": "system", "content": _SYNTHESIS_SYSTEM_PROMPT},
        {"role": "user", "content": f"Sesión: {session}\n\n{parts}"},
    ]
    raw = deepseek.chat_completion(
        messages=messages,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0.1,
        response_format="text",
    )
    logger.info("Sumarized summaries %s", raw)
    return raw.strip()


def extract_session_info(
    segments: list[transcriber.Segment],
    session: str,
    api_key: str,
    base_url: str = deepseek.BASE_URL,
    model: str = deepseek.MODEL,
    senators: list[str] | None = None,
    youtube_url: str = "",
    date: str = "",
) -> SessionResult:
    """Extracts participants, themes, and executive summary in a single LLM call.

    Retries up to _MAX_RETRIES times. Raises RuntimeError if all attempts fail
    or return incomplete data.

    Args:
        segments: All segments from the transcription.
        session: Session identifier stored in the result.
        api_key: Authentication key for the LLM API.
        base_url: Base URL of the OpenAI-compatible API.
        model: Model identifier (defaults to the fast model).
        senators: Optional canonical list of senator names in
            «Apellido(s) Nombre(s)» format used to normalize participant
            names extracted from the transcription.
        youtube_url: YouTube URL of the session recording.
        date: Date of the session (ISO format recommended, e.g. "2025-03-15").

    Returns:
        A SessionResult with non-empty participants, themes, and summary.

    Raises:
        RuntimeError: If the LLM fails to return valid data after all retries.
    """
    chunks = _chunk_segments(segments)
    total = len(chunks)
    logger.info(
        "extract_session_info: %d segment(s), %d chunk(s)", len(segments), total
    )

    all_participants: list[str] = []
    all_themes: list[str] = []
    partial_summaries: list[str] = []

    for i, chunk in enumerate(chunks, start=1):
        logger.info("Processing chunk %d/%d", i, total)
        p, t, s = _extract_chunk(
            chunk, session, api_key, base_url, model, senators,
            chunk_index=i, total_chunks=total,
        )
        all_participants.extend(p)
        all_themes.extend(t)
        partial_summaries.append(s)

    participants = list(set(all_participants))
    themes = list(set(all_themes))

    if total == 1:
        summary = partial_summaries[0]
    else:
        logger.info("Synthesizing summary from %d partial summaries", total)
        summary = _synthesize_summary(
            partial_summaries, session, api_key, base_url, model
        )

    logger.info(
        "extract_session_info: %d participant(s), %d topic(s)",
        len(participants),
        len(themes),
    )
    return SessionResult(
        session=session,
        summary=summary,
        participants=participants,
        themes=themes,
        youtube_url=youtube_url,
        date=date,
    )


def save_session_result(result: SessionResult, output_path: pathlib.Path) -> None:
    """Saves a SessionResult to a JSON file.

    Args:
        result: The session result to serialize.
        output_path: Path where the JSON file will be written.
    """
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("SessionResult saved to: %s", output_path)


def load_session_result(input_path: pathlib.Path) -> SessionResult:
    """Loads a SessionResult from a JSON file written by save_session_result.

    Args:
        input_path: Path to the JSON file to read.

    Returns:
        The deserialized SessionResult.
    """
    data = json.loads(input_path.read_text(encoding="utf-8"))
    logger.info("SessionResult loaded from: %s", input_path)
    return SessionResult(
        session=data["session"],
        summary=data["summary"],
        participants=data["participants"],
        themes=data["themes"],
        youtube_url=data.get("youtube_url", ""),
        date=data.get("date", ""),
    )
