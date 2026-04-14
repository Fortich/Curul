"""Extracts key ideas from parliamentary transcriptions via an LLM."""

# ruff: noqa: E501 — long lines are LLM prompt content, not code

import json
import logging
import pathlib
from typing import TypedDict

from pipeline import deepseek, session_info_extractor, transcriber

logger = logging.getLogger(__name__)


class Mention(TypedDict):
    """A named entity referenced within an idea."""

    entity: str   # name or description of the person, body, bill, etc.
    type: str     # open label assigned by the LLM (e.g. "legislador", "ejecutivo", "ley", "organismo")


class Idea(TypedDict):
    """A single idea extracted from a parliamentary session."""

    congressman_name: str
    session: str
    quote: str
    summary: str
    start: float
    end: float
    tags: list[str]
    mentions: list[Mention]
    importance: float


_BASE_SYSTEM_PROMPT = """\
Eres un asistente especializado en análisis de transcripciones de sesiones legislativas.
Se te proporcionará la transcripción parcial o completa de una sesión parlamentaria con timestamps en segundos.

Tu tarea es identificar las distintas intervenciones de los legisladores y extraer las ideas relevantes.
Para cada idea debes:
- Identificar el nombre completo del legislador usando los patrones de presentación habituales
  del cuerpo legislativo (títulos honoríficos, presentaciones de la mesa, etc.)
- Extraer la cita textual exacta de lo que dijo
- Redactar un resumen conciso (1-2 oraciones) que sintetice la idea principal expresada por el legislador, en tercera persona y en español
- Registrar el timestamp de inicio y fin en segundos (float), tomados directamente de la transcripción
- Asignar entre 1 y 5 tags temáticos (ej: "economía", "salud", "educación", "presupuestos")
- Identificar todas las entidades mencionadas en la intervención (pueden ser cero) y clasificarlas con un tipo abierto. Ejemplos de tipos: "legislador", "ejecutivo", "ley", "proyecto de ley", "organismo", "partido", "institución". El tipo debe ser breve y en español.
- Asignar un puntaje de importancia entre 0.0 y 1.0 (float) según estos criterios orientativos:
  0.0-0.2 = intervención protocolar o de trámite (saludos, mociones de orden, lecturas de acta)
  0.2-0.4 = comentario breve sin propuesta concreta
  0.4-0.6 = posición o argumento relevante del legislador
  0.6-0.8 = propuesta concreta, proyecto de ley o enmienda
  0.8-1.0 = intervención de alto impacto: debate sustancial, votación clave o declaración pública importante

Responde ÚNICAMENTE con un JSON válido con esta estructura (sin texto adicional):
{
  "ideas": [
    {
      "congressman_name": "Nombre Apellido",
      "quote": "Texto exacto de la cita",
      "summary": "Resumen conciso de la idea en 1-2 oraciones.",
      "start": 123.4,
      "end": 456.7,
      "tags": ["tag1", "tag2"],
      "mentions": [
        {"entity": "Nombre o descripción", "type": "legislador"},
        {"entity": "Proyecto de Ley 123", "type": "proyecto de ley"}
      ],
      "importance": 0.6
    }
  ]
}"""


def _build_system_prompt(
    known_participants: list[str],
    known_themes: list[str],
) -> str:
    """Extends the base prompt with session context."""
    lines = [_BASE_SYSTEM_PROMPT, "\nContexto de la sesión:"]
    if known_participants:
        lines.append(
            "Participantes identificados (usa exactamente estos nombres en congressman_name;"
            " si el orador no aparece en la lista, usa \"Desconocido\"):"
        )
        lines.extend(f"  - {p}" for p in known_participants)
    if known_themes:
        lines.append(
            "\nTemas principales (prioriza estas etiquetas en tags;"
            " puedes agregar otras si el contenido lo justifica):"
        )
        lines.append("  " + ", ".join(known_themes))
    return "\n".join(lines)


_USER_PROMPT_TEMPLATE = """\
Sesión: {session}

Transcripción (formato [inicio_s - fin_s] texto):
{segments_text}"""


def _format_segments(segments: list[transcriber.Segment]) -> str:
    return "\n".join(
        f"[{seg.start:.1f}s - {seg.end:.1f}s] {seg.text.strip()}"
        for seg in segments
    )


_BASE_TEMPERATURE: float = 0.1
_RETRY_TEMP_DELTA: float = 0.15
_MAX_RETRIES: int = 3


def _process_segments(
    segments: list[transcriber.Segment],
    session: str,
    api_key: str,
    base_url: str,
    model: str,
    known_participants: list[str],
    known_themes: list[str],
) -> list[Idea]:
    """Extracts ideas from segments, retrying with higher temperature on parse errors.

    On each failure the temperature is raised by *_RETRY_TEMP_DELTA*. If any
    attempt produces partial results (some items parsed, some malformed), the
    attempt with the most valid ideas is returned rather than an empty list.
    """
    messages = [
        {"role": "system", "content": _build_system_prompt(known_participants, known_themes)},
        {
            "role": "user",
            "content": _USER_PROMPT_TEMPLATE.format(
                session=session, segments_text=_format_segments(segments)
            ),
        },
    ]

    best: list[Idea] = []
    for attempt in range(1, _MAX_RETRIES + 1):
        temperature = _BASE_TEMPERATURE + (attempt - 1) * _RETRY_TEMP_DELTA
        if attempt > 1:
            logger.info(
                "Retry %d/%d (temperature=%.2f)",
                attempt,
                _MAX_RETRIES,
                temperature,
            )

        raw = deepseek.chat_completion(
            messages=messages,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
        )

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Attempt %d: invalid JSON (%s)", attempt, exc)
            continue

        items = data.get("ideas", [])
        if not isinstance(items, list):
            logger.warning(
                "Attempt %d: 'ideas' is not a list (%s)", attempt, type(items).__name__
            )
            continue

        ideas: list[Idea] = []
        skipped = 0
        for item in items:
            try:
                raw_mentions = item.get("mentions", [])
                mentions: list[Mention] = [
                    Mention(
                        entity=str(m["entity"]),
                        type=str(m["type"]),
                    )
                    for m in raw_mentions
                    if isinstance(m, dict) and "entity" in m and "type" in m
                ]
                ideas.append(
                    Idea(
                        congressman_name=item["congressman_name"],
                        session=session,
                        quote=item["quote"],
                        summary=item.get("summary", ""),
                        start=float(item["start"]),
                        end=float(item["end"]),
                        tags=item.get("tags", []),
                        mentions=mentions,
                        importance=max(0.0, min(1.0, float(item.get("importance", 0.5)))),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Attempt %d: malformed item (%s): %r", attempt, exc, item
                )
                skipped += 1

        if not skipped:
            return ideas  # perfect parse — no need to retry

        if len(ideas) > len(best):
            best = ideas

        if attempt < _MAX_RETRIES:
            logger.warning(
                "Attempt %d: %d malformed item(s), retrying", attempt, skipped
            )

    if best:
        logger.warning(
            "Returning best partial result (%d idea(s)) after %d attempts",
            len(best),
            _MAX_RETRIES,
        )
        return best

    logger.error("All %d attempts failed", _MAX_RETRIES)
    return []


def extract_ideas(
    transcription: transcriber.TranscriptionResult,
    session: str,
    api_key: str,
    session_result: session_info_extractor.SessionResult,
    base_url: str = deepseek.BASE_URL,
    model: str = deepseek.MODEL,
) -> list[Idea]:
    """Extracts ideas from a parliamentary transcription using an LLM.

    Args:
        transcription: The transcription result with timed segments.
        session: Identifier for the parliamentary session.
        api_key: Authentication key for the LLM API.
        session_result: Previously saved session metadata; its participants and
            themes are injected into the prompt.
        base_url: Base URL of the OpenAI-compatible API.
        model: Model identifier to use for extraction.

    Returns:
        A list of ideas extracted from the transcription.
    """
    logger.info(
        "Extracting ideas from %d segments via %s",
        len(transcription.segments),
        model,
    )

    ideas = _process_segments(
        transcription.segments, session, api_key, base_url, model,
        known_participants=session_result["participants"],
        known_themes=session_result["themes"],
    )

    logger.info("Extracted %d ideas total", len(ideas))
    return ideas


def save_ideas(ideas: list[Idea], output_path: pathlib.Path) -> None:
    """Saves a list of ideas to a JSON file.

    Args:
        ideas: The list of ideas to serialize.
        output_path: pathlib.Path where the JSON file will be written.
    """
    output_path.write_text(
        json.dumps(ideas, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Ideas saved to: %s", output_path)


def load_ideas(input_path: pathlib.Path) -> list[Idea]:
    """Loads a list of ideas from a JSON file.

    The file must have been written by save_ideas.

    Args:
        input_path: pathlib.Path to the JSON file to read.

    Returns:
        The deserialized list of ideas.
    """
    data = json.loads(input_path.read_text(encoding="utf-8"))
    logger.info("Ideas loaded from: %s", input_path)
    return [Idea(**item) for item in data]
