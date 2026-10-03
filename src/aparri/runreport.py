"""Run report: parameters, input hashes, versions, counts and warnings (CLAUDE.md §5).

Every pipeline step opens a ``RunReport``, registers its inputs (hashed), adds counts
and warnings as it goes, and writes ``outputs/reports/run_<step>_<timestamp>.json``.
Warnings are also printed loudly so a missing input (e.g. acquisition dates) can
never be overlooked.
"""
from __future__ import annotations

import datetime as _dt
import json
import platform
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from .io import REPO_ROOT, ensure_dir, load_config, repo_path, sha256_file, shapefile_parts

_PKGS = ["geopandas", "shapely", "pyproj", "pandas", "numpy", "scipy", "statsmodels",
         "rasterio", "scikit-image", "matplotlib", "openpyxl", "python-docx", "pyyaml"]


def _versions() -> dict[str, str]:
    out = {"python": platform.python_version()}
    for p in _PKGS:
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = "not installed"
    return out


class RunReport:
    """Collects everything needed to reproduce (and defend) one pipeline run."""

    def __init__(self, step: str, config: dict[str, Any] | None = None):
        self.step = step
        self.config = config if config is not None else load_config()
        self.started = _dt.datetime.now(_dt.timezone.utc)
        self.inputs: dict[str, str] = {}
        self.counts: dict[str, Any] = {}
        self.warnings: list[str] = []
        self.outputs: list[str] = []

    def add_input(self, path: Path | str) -> None:
        """Hash a file (all shapefile sidecars if it is a .shp)."""
        p = repo_path(path)
        files = shapefile_parts(p) if p.suffix == ".shp" else [p]
        for f in files:
            if f.exists():
                self.inputs[str(f.relative_to(REPO_ROOT))] = sha256_file(f)

    def add_output(self, path: Path | str) -> None:
        self.outputs.append(str(Path(path).resolve().relative_to(REPO_ROOT)))

    def count(self, key: str, value: Any) -> None:
        self.counts[key] = value

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"WARNING [{self.step}]: {message}", file=sys.stderr)

    def warn_if_null(self, params: dict[str, Any], label: str) -> None:
        """Loudly flag every null parameter (rule 2: never invent values)."""
        for k, v in params.items():
            if v is None:
                self.warn(f"{label}.{k} is null (NOT PROVIDED) - results depending on it are withheld/flagged")

    def write(self) -> Path:
        ended = _dt.datetime.now(_dt.timezone.utc)
        out_dir = ensure_dir(self.config["paths"]["outputs"] + "/reports")
        name = f"run_{self.step}_{self.started.strftime('%Y%m%dT%H%M%SZ')}.json"
        payload = {
            "step": self.step,
            "started_utc": self.started.isoformat(),
            "ended_utc": ended.isoformat(),
            "versions": _versions(),
            "parameters": self.config,
            "input_sha256": dict(sorted(self.inputs.items())),
            "counts": self.counts,
            "outputs": sorted(self.outputs),
            "warnings": self.warnings,
        }
        path = out_dir / name
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return path
