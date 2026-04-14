from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def short_audio() -> Path:
    """Return the path to the committed Spanish audio fixture.

    The file was generated once with:
        say -v Mónica -o tests/fixtures/test_clip.aiff "Hola, buenos días."

    It is committed to the repo so tests run identically on any OS.
    """
    return FIXTURES_DIR / "test_clip.aiff"
