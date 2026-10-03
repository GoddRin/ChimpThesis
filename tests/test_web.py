"""Phase 8 tests: data files are valid GeoJSON in the right place, and (if node + Chromium exist) a headless smoke run passes."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from aparri.io import REPO_ROOT

WEB = REPO_ROOT / "outputs" / "web"


def load(name):
    t = (WEB / "data" / f"{name}.js").read_text(encoding="utf-8")
    key = f"window.APARRI.{name} = "
    return json.loads(t[t.index(key) + len(key):].rstrip().rstrip(";"))


@pytest.mark.parametrize("name,geom,required", [
    ("segments", {"LineString", "MultiLineString"}, ["transect_id", "barangay", "risk_class", "EPR_m_yr", "confidence", "unc_status"]),
    ("transects", {"LineString"}, ["transect_id"]),
    ("shorelines", {"LineString", "MultiLineString"}, ["year", "scope"]),
    ("barangays", {"Polygon", "MultiPolygon"}, ["name"]),
    ("legacy", {"Polygon", "MultiPolygon"}, ["risk"]),
])
def test_geojson_valid(name, geom, required):
    fc = load(name)
    assert fc["type"] == "FeatureCollection" and len(fc["features"]) > 0
    for f in fc["features"]:
        assert f["geometry"]["type"] in geom
        for k in required:
            assert k in f["properties"]
        flat = json.dumps(f["geometry"]["coordinates"])
        # WGS84 sanity: Aparri is near lon 121.6, lat 18.35
    c = fc["features"][0]["geometry"]["coordinates"]
    while isinstance(c[0], list):
        c = c[0]
    assert 121.4 < c[0] < 121.9 and 18.2 < c[1] < 18.5, c


def test_risk_classes_only_allowed_values():
    v = {f["properties"]["risk_class"] for f in load("segments")["features"]}
    assert v <= {"Low", "Medium", "High", None}
    assert {f["properties"]["confidence"] for f in load("segments")["features"]} <= {"high", "medium", "low"}


def test_meta_and_table():
    m = load("meta"); t = load("table42")
    assert m["thresholds"] == {"low_max": 2.0, "medium_max": 5.0} and m["order"][0] == "Dodan" and len(t["thesis"]) == 8


def test_offline_assets_present():
    for f in ("vendor/leaflet.js", "vendor/leaflet.css", "index.html", "app.js", "style.css", "README.md"):
        assert (WEB / f).exists(), f
    html = (WEB / "index.html").read_text()
    assert "Academic use" in html and "http://" not in html and "cdn" not in html.lower()      # no external dependency


@pytest.mark.skipif(shutil.which("node") is None or not Path("/opt/node22/lib/node_modules/playwright").exists(), reason="node/playwright not available")
def test_headless_smoke():
    r = subprocess.run(["node", str(REPO_ROOT / "tests" / "web_smoke.mjs")], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
