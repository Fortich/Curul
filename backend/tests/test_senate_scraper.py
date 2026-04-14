import json

import pytest

from pipeline.senate_scraper import _parse_names, fetch_senators

# Minimal HTML that replicates the real page structure:
# each senator appears in two layout divs (<h3> duplicated).
_SAMPLE_HTML = """\
<html><body>
  <div class="modazdirectory__row">
    <div class="modazdirectory__result modazdirectory__layout-misc_off">
      <h3>García López Ana María</h3>
    </div>
    <div class="modazdirectory__result modazdirectory__layout-misc_on">
      <h3>García López Ana María</h3>
    </div>
  </div>
  <div class="modazdirectory__row">
    <div class="modazdirectory__result modazdirectory__layout-misc_off">
      <h3>Pérez Rodríguez Juan Carlos</h3>
    </div>
    <div class="modazdirectory__result modazdirectory__layout-misc_on">
      <h3>Pérez Rodríguez Juan Carlos</h3>
    </div>
  </div>
</body></html>
"""


@pytest.mark.unit
def test_parse_names_deduplicates():
    names = _parse_names(_SAMPLE_HTML)
    assert names == ["García López Ana María", "Pérez Rodríguez Juan Carlos"]


@pytest.mark.unit
def test_parse_names_empty_html():
    assert _parse_names("<html><body></body></html>") == []


@pytest.mark.unit
def test_parse_names_ignores_blank_h3():
    html = "<html><body><h3>   </h3><h3>Válido Nombre</h3></body></html>"
    assert _parse_names(html) == ["Válido Nombre"]


@pytest.mark.unit
def test_fetch_senators_loads_from_cache(tmp_path):
    cache = tmp_path / "senators.json"
    expected = ["Pérez Juan", "García Ana"]
    cache.write_text(json.dumps(expected), encoding="utf-8")

    result = fetch_senators(cache_path=cache)
    assert result == expected


@pytest.mark.unit
def test_fetch_senators_writes_cache(tmp_path, monkeypatch):
    cache = tmp_path / "senators.json"

    monkeypatch.setattr(
        "pipeline.senate_scraper._fetch_html",
        lambda url: _SAMPLE_HTML,
    )

    result = fetch_senators(cache_path=cache)

    assert cache.exists()
    cached = json.loads(cache.read_text(encoding="utf-8"))
    # fetch_senators returns sorted names
    assert result == sorted(["García López Ana María", "Pérez Rodríguez Juan Carlos"])
    assert cached == result


@pytest.mark.unit
def test_fetch_senators_no_cache(monkeypatch):
    monkeypatch.setattr(
        "pipeline.senate_scraper._fetch_html",
        lambda url: _SAMPLE_HTML,
    )

    result = fetch_senators(cache_path=None)
    assert "García López Ana María" in result
    assert "Pérez Rodríguez Juan Carlos" in result
