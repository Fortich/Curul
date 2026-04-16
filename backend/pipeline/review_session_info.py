"""Post-processing script to review extracted session info for quality issues.

Three checks are performed:
1. Date field is present and in valid ISO 8601 format (YYYY-MM-DD).
2. YouTube URL is present and non-empty.
3. Participant names against the official senators list, for manual verification.
"""

import pathlib
from datetime import date

from pipeline import senate_scraper, session_info_extractor


def report_date(result: session_info_extractor.SessionResult) -> None:
    """Prints whether the date field is present and in valid ISO 8601 format."""
    print(f"\n{'='*60}")
    print("FECHA DE LA SESIÓN")
    print(f"{'='*60}")
    raw = result.get("date", "")
    if not raw:
        print("  ERROR: campo 'date' ausente o vacío.")
        return
    try:
        parsed = date.fromisoformat(raw)
        print(f"  OK — {parsed.isoformat()}")
    except ValueError:
        print(f"  ERROR: '{raw}' no es una fecha ISO 8601 válida (esperado YYYY-MM-DD).")


def report_youtube_url(result: session_info_extractor.SessionResult) -> None:
    """Prints whether the youtube_url field is present and non-empty."""
    print(f"\n{'='*60}")
    print("ENLACE DE YOUTUBE")
    print(f"{'='*60}")
    url = result.get("youtube_url", "")
    if url:
        print(f"  OK — {url}")
    else:
        print("  ERROR: campo 'youtube_url' ausente o vacío.")


def report_unrecognized_participants(
    result: session_info_extractor.SessionResult,
    senators: list[str],
) -> None:
    """Prints participant names not found in the official senators list."""
    senator_set = set(senators)
    participants = result.get("participants", [])

    recognized = [p for p in participants if p in senator_set]
    unrecognized = [p for p in participants if p not in senator_set]

    print(f"\n{'='*60}")
    print(
        f"PARTICIPANTES — {len(recognized)} reconocidos, "
        f"{len(unrecognized)} no encontrados en lista oficial"
    )
    print(f"{'='*60}")

    if recognized:
        print(f"\n  Reconocidos ({len(recognized)}):")
        for name in recognized:
            print(f"    ✓ {name}")

    if unrecognized:
        print(f"\n  No encontrados en lista oficial ({len(unrecognized)}):")
        for name in unrecognized:
            print(f"    • {name!r}")
    elif participants:
        print("\n  (todos los participantes coinciden con la lista oficial)")


def review(
    session_info_path: pathlib.Path,
    senators_cache_path: pathlib.Path | None = None,
) -> None:
    """Runs all review checks and prints a report to stdout."""
    result = session_info_extractor.load_session_result(session_info_path)
    senators = senate_scraper.fetch_senators(cache_path=senators_cache_path)

    print(f"\nArchivo session info : {session_info_path}")
    print(f"Sesión               : {result['session']}")
    print(f"Total participantes  : {len(result.get('participants', []))}")
    print(f"Total senadores      : {len(senators)}")

    report_date(result)
    report_youtube_url(result)
    report_unrecognized_participants(result, senators)
    print()
