"""Smoke tests: package imports, config is complete, raw data is protected."""
import importlib
import json

import pytest

from aparri import io as aio
from aparri.runreport import RunReport

MODULES = ["audit", "audit_gee", "clean", "raster_shore", "landsat", "compare", "transects",
           "metrics", "risk", "tables", "maps", "sensitivity", "stats_survey", "web", "annex"]


@pytest.mark.parametrize("name", MODULES)
def test_modules_import(name):
    importlib.import_module(f"aparri.{name}")


def test_config_has_required_keys():
    cfg = aio.load_config()
    assert cfg["crs_work"] == 32651 and cfg["crs_source"] == 4326
    assert cfg["years"] == [1990, 2000, 2010, 2020, 2025]
    assert cfg["risk"]["low_max"] == 2.0 and cfg["risk"]["medium_max"] == 5.0
    assert len(cfg["study_barangays"]) == 8
    assert all(v is None for v in cfg["acquisition_dates"].values()), "dates must stay null until supplied"
    assert all(v is None for v in cfg["uncertainty_m"].values()), "uncertainty must stay null until supplied"


def test_raw_is_protected():
    with pytest.raises(PermissionError):
        aio.assert_not_raw("data/raw/anything.txt")
    with pytest.raises(PermissionError):
        aio.assert_not_raw("docs/thesis/x.docx")
    aio.assert_not_raw("data/interim/x.gpkg")  # allowed


def test_run_report_roundtrip(tmp_path):
    cfg = aio.load_config()
    cfg = {**cfg, "paths": {**cfg["paths"], "outputs": str(tmp_path)}}
    rep = RunReport("smoke", cfg)
    rep.add_input("config/config.yaml")
    rep.count("n", 3)
    rep.warn("example warning")
    path = rep.write()
    data = json.loads(path.read_text())
    assert data["counts"] == {"n": 3} and data["warnings"] == ["example warning"]
    assert data["input_sha256"]["config/config.yaml"]
    assert "geopandas" in data["versions"]


def test_raw_manifest_matches_disk():
    """Raw data must be byte-identical to the manifest written at intake."""
    root = aio.REPO_ROOT / "data" / "raw"
    for line in (root / "MANIFEST.sha256").read_text().splitlines():
        digest, rel = line.split("  ", 1)
        assert aio.sha256_file(root / rel) == digest, rel
