"""Post-processing script to review extracted ideas for quality issues.

Two checks are performed:
1. Ideas with unknown speaker ("Desconocido"), showing their time range in seconds.
2. Congressman names not found in the official senators list, for manual verification.
"""

import pathlib
from collections import Counter

from pipeline import idea_extractor, senate_scraper


def report_unknown_speakers(ideas: list[idea_extractor.Idea]) -> None:
    """Prints ideas whose congressman_name is 'Desconocido'."""
    unknown = [i for i in ideas if i["congressman_name"] == "Desconocido"]
    print(f"\n{'='*60}")
    print(f"IDEAS CON INTERLOCUTOR DESCONOCIDO  ({len(unknown)} ideas)")
    print(f"{'='*60}")
    if not unknown:
        print("  (ninguna)")
        return
    for idx, idea in enumerate(unknown, start=1):
        summary = idea.get("summary", "").strip()
        short_summary = (summary[:100] + "…") if len(summary) > 100 else summary
        print(f"\n{idx:3d}. [{idea['start']:.1f}s – {idea['end']:.1f}s]  {short_summary}")


def report_unrecognized_names(
    ideas: list[idea_extractor.Idea],
    senators: list[str],
) -> None:
    """Prints names that don't appear exactly in the official senators list."""
    senator_set = set(senators)

    name_counts: Counter[str] = Counter()
    for idea in ideas:
        name = idea["congressman_name"]
        if name != "Desconocido":
            name_counts[name] += 1

    unrecognized = [
        (name, count)
        for name, count in name_counts.most_common()
        if name not in senator_set
    ]

    print(f"\n{'='*60}")
    print(f"NOMBRES NO ENCONTRADOS EN LISTA DE SENADORES  ({len(unrecognized)} nombres únicos)")
    print(f"{'='*60}")
    if not unrecognized:
        print("  (todos los nombres coinciden con la lista oficial)")
        return
    for name, count in unrecognized:
        print(f"  • {name!r}  ({count} idea{'s' if count != 1 else ''})")


def review(
    ideas_path: pathlib.Path,
    senators_cache_path: pathlib.Path | None = None,
) -> None:
    """Runs both review checks and prints a report to stdout."""
    ideas = idea_extractor.load_ideas(ideas_path)
    senators = senate_scraper.fetch_senators(cache_path=senators_cache_path)

    print(f"\nArchivo de ideas : {ideas_path}")
    print(f"Total de ideas   : {len(ideas)}")
    print(f"Total senadores  : {len(senators)}")

    report_unknown_speakers(ideas)
    report_unrecognized_names(ideas, senators)
    print()
