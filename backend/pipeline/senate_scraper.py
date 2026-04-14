"""Scrapes the list of active senators from senado.gov.co."""

import json
import logging
import pathlib
import urllib.request
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

_SENATORS_URL = (
    "https://www.senado.gov.co/index.php/el-senado/senadores"
    "?lastletter=Todos"
)
_USER_AGENT = "Mozilla/5.0 (compatible; curul-pipeline/1.0)"


class _H3Parser(HTMLParser):
    """Collects text content from <h3> tags."""

    def __init__(self) -> None:
        super().__init__()
        self._in_h3: bool = False
        self._current: list[str] = []
        self._raw: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Track entry into <h3> tags."""
        if tag == "h3":
            self._in_h3 = True
            self._current = []

    def handle_endtag(self, tag: str) -> None:
        """Collect accumulated text when exiting <h3>."""
        if tag == "h3":
            self._in_h3 = False
            text = "".join(self._current).strip()
            if text:
                self._raw.append(text)

    def handle_data(self, data: str) -> None:
        """Accumulate character data inside <h3>."""
        if self._in_h3:
            self._current.append(data)

    @property
    def names(self) -> list[str]:
        """Deduplicated names in the order first encountered."""
        seen: set[str] = set()
        result: list[str] = []
        for name in self._raw:
            if name not in seen:
                seen.add(name)
                result.append(name)
        return result


def _parse_names(html: str) -> list[str]:
    """Extracts unique senator names from the page HTML.

    The page renders each senator twice (two CSS layout variants).
    Names are in «Apellido(s) Nombre(s)» order as published on the site.

    Args:
        html: Raw HTML of the senators directory page.

    Returns:
        Deduplicated list of senator names preserving first-seen order.
    """
    parser = _H3Parser()
    parser.feed(html)
    return parser.names


def _fetch_html(url: str) -> str:
    """Downloads a URL and returns its content as a string."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_senators(cache_path: pathlib.Path | None = None) -> list[str]:
    """Returns the canonical list of active senators from senado.gov.co.

    Names are in «Apellido(s) Nombre(s)» format, sorted alphabetically,
    exactly as published on the official site.

    If *cache_path* is provided and the file already exists, the cached
    list is returned without hitting the network.  On a cache miss the
    live page is fetched and the result is written to *cache_path*.

    Args:
        cache_path: Optional path to a JSON cache file.

    Returns:
        Sorted list of canonical senator name strings.
    """
    if cache_path is not None and cache_path.exists():
        names: list[str] = json.loads(
            cache_path.read_text(encoding="utf-8")
        )
        logger.info(
            "senate_scraper: %d senators loaded from cache", len(names)
        )
        return names

    logger.info("senate_scraper: downloading senators from %s", _SENATORS_URL)
    html = _fetch_html(_SENATORS_URL)
    names = sorted(_parse_names(html))

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(names, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("senate_scraper: cache saved to %s", cache_path)

    logger.info("senate_scraper: %d senators found", len(names))
    return names
