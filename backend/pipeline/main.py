"""Entry point for the processing pipeline."""

import json
import logging
import pathlib
import sys

from pipeline import (
    downloader,
    export_frontend,
    idea_extractor,
    review_ideas,
    review_session_info,
    senate_scraper,
    senator_consolidator,
    session_info_extractor,
    transcriber,
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Full pipeline: download -> transcribe -> session info -> ideas.

    Each step writes its output to disk before proceeding.
    If an output file already exists, that step is skipped (resume support).

    Usage: uv run python main.py <session> <url> <output_dir> <api_key>
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if len(sys.argv) < 5:
        print("Usage: uv run python main.py <session> <url> <output_dir> <api_key>")
        sys.exit(1)

    args = sys.argv[1:]

    backend = "whisper"
    if "--backend" in args:
        idx = args.index("--backend")
        if idx + 1 >= len(args):
            print("--backend requires a value (qwen3 or whisper)")
            sys.exit(1)
        backend = args.pop(idx + 1)
        args.pop(idx)

    session_name = args[0]
    url = args[1]
    session_dir = pathlib.Path(args[2]) / session_name
    api_key = args[3]

    session_dir.mkdir(parents=True, exist_ok=True)

    existing_audio = [f for f in session_dir.iterdir() if f.suffix == ".opus"]
    if existing_audio:
        audio_path = existing_audio[0]
        logger.info("Step 1/4 — Audio already downloaded: %s (skipping)", audio_path)
    else:
        logger.info("Step 1/4 — Downloading audio: %s", url)
        audio_path = downloader.download_audio(url, session_dir)
        logger.info("Audio saved to: %s", audio_path)

    transcription_path = session_dir / "transcription.json"
    if transcription_path.exists():
        logger.info("Step 2/4 — Transcription already exists: %s (skipping)", transcription_path)
        transcription = transcriber.load_transcription(transcription_path)
    else:
        logger.info("Step 2/4 — Transcribing: %s", audio_path)
        transcription = transcriber.transcribe(audio_path, backend=backend)
        transcriber.save_transcription(transcription, transcription_path)
        logger.info("Transcription saved to: %s", transcription_path)

    senators_cache_path = session_dir.parent / "senators_cache.json"
    senators = senate_scraper.fetch_senators(cache_path=senators_cache_path)

    session_info_path = session_dir / "session_info.json"
    if session_info_path.exists():
        logger.info("Step 3/4 — Session info already exists: %s (skipping)", session_info_path)
        session_result = session_info_extractor.load_session_result(session_info_path)
    else:
        logger.info("Step 3/4 — Extracting session info...")
        session_result = session_info_extractor.extract_session_info(
            transcription.segments, session_name, api_key, senators=senators,
            youtube_url=url,
        )
        session_info_extractor.save_session_result(session_result, session_info_path)
        logger.info("Session info saved to: %s", session_info_path)

    ideas_path = session_dir / "ideas.json"
    if ideas_path.exists():
        logger.info("Step 4/4 — Ideas already exist: %s (skipping)", ideas_path)
    else:
        logger.info("Step 4/4 — Extracting ideas...")
        ideas = idea_extractor.extract_ideas(
            transcription, session_name, api_key, session_result
        )
        idea_extractor.save_ideas(ideas, ideas_path)
        logger.info("Ideas saved to: %s", ideas_path)

    logger.info("Pipeline complete. Results in: %s", session_dir)
    review_session_info.review(session_info_path, senators_cache_path=senators_cache_path)
    review_ideas.review(ideas_path, senators_cache_path=senators_cache_path)

def download_cli() -> None:
    """Downloads audio from a URL to a local directory.

    Usage: uv run python main.py download <URL> <output_dir>
    """
    args = sys.argv[2:]

    if len(args) < 2:
        print("Usage: uv run python main.py download <URL> <output_dir>")
        sys.exit(1)

    url = args[0]
    output_dir = pathlib.Path(args[1])
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading audio from: {url}")
    audio_path = downloader.download_audio(url, output_dir)
    print(f"Audio saved to: {audio_path}")

def transcribe_file() -> None:
    """Transcribes a local audio file with optional output path.

    Usage: uv run python main.py transcribe <audio_file> [--output <file.json>]
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = sys.argv[2:]

    if not args:
        logger.error(
            "Usage: uv run python main.py transcribe <audio_file>"
            " [--output <file.json>]"
        )
        sys.exit(1)

    output_path = None

    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 >= len(args):
            logger.error("--output requires a file path")
            sys.exit(1)
        output_path = pathlib.Path(args.pop(idx + 1))
        args.pop(idx)

    backend = "whisper"
    if "--backend" in args:
        idx = args.index("--backend")
        if idx + 1 >= len(args):
            logger.error("--backend requires a value (qwen3 or whisper)")
            sys.exit(1)
        backend = args.pop(idx + 1)
        args.pop(idx)

    audio_path = pathlib.Path(args[0])

    logger.info("Transcribing: %s", audio_path)
    result = transcriber.transcribe(audio_path, backend=backend)

    if output_path:
        transcriber.save_transcription(result, output_path)
    else:
        print(result.text)


def extract_ideas_cli() -> None:
    """Extracts ideas from a transcription JSON file via an LLM.

    Usage: uv run python main.py extract-ideas <transcription.json>
        <session> <api_key> --session-info result.json [--output ideas.json]
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = sys.argv[2:]

    if len(args) < 3:
        logger.error(
            "Usage: uv run python main.py extract-ideas"
            " <transcription.json> <session> <api_key>"
            " --session-info result.json [--output ideas.json]"
        )
        sys.exit(1)

    output_path: pathlib.Path | None = None

    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 >= len(args):
            logger.error("--output requires a file path")
            sys.exit(1)
        output_path = pathlib.Path(args.pop(idx + 1))
        args.pop(idx)

    if "--session-info" not in args:
        logger.error("--session-info is required")
        sys.exit(1)

    idx = args.index("--session-info")
    if idx + 1 >= len(args):
        logger.error("--session-info requires a file path")
        sys.exit(1)
    session_info_path = pathlib.Path(args.pop(idx + 1))
    args.pop(idx)

    transcription_path = pathlib.Path(args[0])
    session_name = args[1]
    api_key = args[2]

    session_result = session_info_extractor.load_session_result(session_info_path)
    transcription = transcriber.load_transcription(transcription_path)
    ideas = idea_extractor.extract_ideas(
        transcription, session_name, api_key, session_result
    )

    if output_path:
        idea_extractor.save_ideas(ideas, output_path)
    else:
        print(json.dumps(ideas, ensure_ascii=False, indent=2))


def extract_session_info_cli() -> None:
    """Extracts participants, themes, and summary from a transcription JSON file.

    Usage: uv run python main.py extract-session-info <transcription.json>
        <session> <api_key> [--output result.json]
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = sys.argv[2:]

    if len(args) < 3:
        logger.error(
            "Usage: uv run python main.py extract-session-info"
            " <transcription.json> <session> <api_key>"
            " [--output result.json]"
        )
        sys.exit(1)

    output_path: pathlib.Path | None = None

    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 >= len(args):
            logger.error("--output requires a file path")
            sys.exit(1)
        output_path = pathlib.Path(args.pop(idx + 1))
        args.pop(idx)

    transcription_path = pathlib.Path(args[0])
    session_name = args[1]
    api_key = args[2]

    transcription = transcriber.load_transcription(transcription_path)
    result = session_info_extractor.extract_session_info(
        transcription.segments, session_name, api_key
    )

    if output_path:
        session_info_extractor.save_session_result(result, output_path)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def review_session_info_cli() -> None:
    """Reviews session info for date format, YouTube URL, and participant names.

    Usage: uv run python main.py review-session-info <session_info.json>
        [--senators <senators_cache.json>]
    """
    args = sys.argv[2:]

    if not args or args[0] in ("-h", "--help"):
        print(
            "Usage: uv run python main.py review-session-info <session_info.json>"
            " [--senators <senators_cache.json>]"
        )
        sys.exit(0)

    senators_cache: pathlib.Path | None = None
    if "--senators" in args:
        idx = args.index("--senators")
        if idx + 1 >= len(args):
            logger.error("--senators requires a file path")
            sys.exit(1)
        senators_cache = pathlib.Path(args.pop(idx + 1))
        args.pop(idx)

    session_info_path = pathlib.Path(args[0])
    if not session_info_path.exists():
        logger.error("File not found: %s", session_info_path)
        sys.exit(1)

    review_session_info.review(session_info_path, senators_cache_path=senators_cache)


def review_ideas_cli() -> None:
    """Reviews extracted ideas for unknown speakers and unrecognized names.

    Usage: uv run python main.py review-ideas <ideas.json>
        [--senators <senators_cache.json>]
    """
    args = sys.argv[2:]

    if not args or args[0] in ("-h", "--help"):
        print(
            "Usage: uv run python main.py review-ideas <ideas.json>"
            " [--senators <senators_cache.json>]"
        )
        sys.exit(0)

    senators_cache: pathlib.Path | None = None
    if "--senators" in args:
        idx = args.index("--senators")
        if idx + 1 >= len(args):
            logger.error("--senators requires a file path")
            sys.exit(1)
        senators_cache = pathlib.Path(args.pop(idx + 1))
        args.pop(idx)

    ideas_path = pathlib.Path(args[0])
    if not ideas_path.exists():
        logger.error("File not found: %s", ideas_path)
        sys.exit(1)

    review_ideas.review(ideas_path, senators_cache_path=senators_cache)


def scrape_senators_cli() -> None:
    """Fetches the active senator list from senado.gov.co and prints it.

    Usage: uv run python main.py scrape-senators [--output senators.json]
        [--refresh]

    Options:
        --output FILE   Write results to FILE (also used as cache).
        --refresh       Ignore existing cache and re-fetch from the web.
    """
    args = sys.argv[2:]

    output_path: pathlib.Path | None = None
    refresh = "--refresh" in args
    if refresh:
        args.remove("--refresh")

    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 >= len(args):
            logger.error("--output requires a file path")
            sys.exit(1)
        output_path = pathlib.Path(args.pop(idx + 1))
        args.pop(idx)

    if refresh and output_path is not None and output_path.exists():
        output_path.unlink()

    senators = senate_scraper.fetch_senators(cache_path=output_path)
    print(json.dumps(senators, ensure_ascii=False, indent=2))


def export_frontend_cli() -> None:
    """Exports session info and ideas from pipeline outputs to a frontend data.js file.

    Scans all subdirectories of <output_dir> for session_info.json and ideas.json,
    then writes a data.js file ready to be used by the frontend.

    Usage: uv run python main.py export-frontend <output_dir> <data_js_path>
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = sys.argv[2:]

    if len(args) < 2 or args[0] in ("-h", "--help"):
        print(
            "Usage: uv run python main.py export-frontend"
            " <output_dir> <data_js_path>"
        )
        sys.exit(0)

    output_dir = pathlib.Path(args[0])
    data_js_path = pathlib.Path(args[1])

    if not output_dir.is_dir():
        logger.error("Directory not found: %s", output_dir)
        sys.exit(1)

    sessions, ideas = export_frontend.collect_sessions(output_dir)

    if not sessions:
        logger.error("No sessions found in %s", output_dir)
        sys.exit(1)

    export_frontend.write_data_js(sessions, ideas, data_js_path)


def consolidate_senator_cli() -> None:
    """Consolidates a senator's position from ideas across one or more sessions.

    Reads ideas from <ideas_dir> (a directory with ideas.json files in subdirectories
    or a single ideas.json), filters by <congressman_name>, and outputs a JSON summary.

    Usage: uv run python main.py consolidate-senator <ideas_dir> <congressman_name>
        <api_key> [--output position.json]
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = sys.argv[2:]

    if len(args) < 3 or args[0] in ("-h", "--help"):
        print(
            "Usage: uv run python main.py consolidate-senator"
            " <ideas_dir> <congressman_name> <api_key>"
            " [--output position.json]"
        )
        sys.exit(0)

    output_path: pathlib.Path | None = None
    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 >= len(args):
            logger.error("--output requires a file path")
            sys.exit(1)
        output_path = pathlib.Path(args.pop(idx + 1))
        args.pop(idx)

    ideas_dir = pathlib.Path(args[0])
    congressman_name = args[1]
    api_key = args[2]

    ideas: list[idea_extractor.Idea] = []

    if ideas_dir.is_file():
        ideas = idea_extractor.load_ideas(ideas_dir)
    elif ideas_dir.is_dir():
        for ideas_path in sorted(ideas_dir.rglob("ideas.json")):
            ideas.extend(idea_extractor.load_ideas(ideas_path))
    else:
        logger.error("Path not found: %s", ideas_dir)
        sys.exit(1)

    filtered = [i for i in ideas if i["congressman_name"] == congressman_name]
    logger.info(
        "Found %d idea(s) for '%s' (out of %d total)",
        len(filtered), congressman_name, len(ideas),
    )

    if not filtered:
        logger.error("No ideas found for '%s'", congressman_name)
        sys.exit(1)

    result = senator_consolidator.consolidate_senator_position(
        filtered, congressman_name, api_key
    )

    if output_path:
        senator_consolidator.save_senator_position(result, output_path)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def consolidate_all_senators_cli() -> None:
    """Consolidates positions for all senators that have at least one idea.

    Scans <output_dir> for sessions, loads ideas, and generates a SenatorPosition
    for each senator in the cache that has at least one idea.

    Usage: uv run python main.py consolidate-all-senators <output_dir> <api_key>
        [--senators <senators_cache.json>] [--output <positions.json>]
        [--max-ideas N]
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = sys.argv[2:]

    if len(args) < 2 or args[0] in ("-h", "--help"):
        print(
            "Usage: uv run python main.py consolidate-all-senators"
            " <output_dir> <api_key>"
            " [--senators <senators_cache.json>] [--output <positions.json>]"
            " [--max-ideas N]"
        )
        sys.exit(0)

    output_path: pathlib.Path | None = None
    if "--output" in args:
        idx = args.index("--output")
        if idx + 1 >= len(args):
            logger.error("--output requires a file path")
            sys.exit(1)
        output_path = pathlib.Path(args.pop(idx + 1))
        args.pop(idx)

    senators_cache_path: pathlib.Path | None = None
    if "--senators" in args:
        idx = args.index("--senators")
        if idx + 1 >= len(args):
            logger.error("--senators requires a file path")
            sys.exit(1)
        senators_cache_path = pathlib.Path(args.pop(idx + 1))
        args.pop(idx)

    max_ideas = 50
    if "--max-ideas" in args:
        idx = args.index("--max-ideas")
        if idx + 1 >= len(args):
            logger.error("--max-ideas requires an integer value")
            sys.exit(1)
        max_ideas = int(args.pop(idx + 1))
        args.pop(idx)

    output_dir = pathlib.Path(args[0])
    api_key = args[1]

    if not output_dir.is_dir():
        logger.error("Directory not found: %s", output_dir)
        sys.exit(1)

    if senators_cache_path is None:
        senators_cache_path = output_dir / "senators_cache.json"

    senators = senate_scraper.fetch_senators(cache_path=senators_cache_path)
    logger.info("Loaded %d senators from cache", len(senators))

    results = senator_consolidator.consolidate_all_senators(
        output_dir, senators, api_key, max_ideas=max_ideas
    )

    serializable = {name: dict(pos) for name, pos in results.items()}

    if output_path:
        output_path.write_text(
            json.dumps(serializable, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Positions written to: %s", output_path)
    else:
        print(json.dumps(serializable, ensure_ascii=False, indent=2))


COMMANDS = {
    "download": download_cli,
    "transcribe": transcribe_file,
    "extract-ideas": extract_ideas_cli,
    "extract-session-info": extract_session_info_cli,
    "scrape-senators": scrape_senators_cli,
    "review-session-info": review_session_info_cli,
    "review-ideas": review_ideas_cli,
    "export-frontend": export_frontend_cli,
    "consolidate-senator": consolidate_senator_cli,
    "consolidate-all-senators": consolidate_all_senators_cli,
}


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] in COMMANDS:
        COMMANDS[sys.argv[1]]()
    else:
        main()
