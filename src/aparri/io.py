"""Input/output helpers: config, paths, hashing, vector/raster loading.

Why this module exists: every script must (a) read the same config, (b) treat
``data/raw`` as read-only, and (c) work in one metric CRS.  Keeping those three
rules in one place stops them from being re-implemented (and broken) elsewhere.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import geopandas as gpd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config" / "config.yaml"


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    """Read the YAML config. YAML turns int keys (years) into ints, which we keep."""
    with open(path or CONFIG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def repo_path(rel: str | Path) -> Path:
    """Resolve a config-relative path against the repository root."""
    p = Path(rel)
    return p if p.is_absolute() else REPO_ROOT / p


def sha256_file(path: Path | str, chunk: int = 1 << 20) -> str:
    """SHA-256 of a file (used for the run report and raw-data manifest)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def shapefile_parts(shp: Path | str) -> list[Path]:
    """All sidecar files of a shapefile (so hashing covers .dbf/.prj too)."""
    shp = Path(shp)
    return sorted(p for p in shp.parent.glob(shp.stem + ".*") if p.is_file())


def read_vector(path: Path | str, crs: int | None = None) -> gpd.GeoDataFrame:
    """Read a vector file; reproject to ``crs`` if given. Never writes."""
    gdf = gpd.read_file(repo_path(path))
    if crs is not None and gdf.crs is not None:
        gdf = gdf.to_crs(crs)
    return gdf


def ensure_dir(path: Path | str) -> Path:
    p = repo_path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def assert_not_raw(path: Path | str) -> None:
    """Hard guard: refuse to write anywhere under data/raw or docs/thesis."""
    p = repo_path(path).resolve()
    for forbidden in (REPO_ROOT / "data" / "raw", REPO_ROOT / "docs" / "thesis"):
        if forbidden in p.parents or p == forbidden:
            raise PermissionError(f"{p} is read-only (CLAUDE.md rule 1)")
