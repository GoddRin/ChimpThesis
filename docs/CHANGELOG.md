# Changelog

## Phase 1 — scaffolding (2026-10-03)
- Repo laid out per CLAUDE.md §3; raw uploads moved to `data/raw/` (read-only) with `MANIFEST.sha256`; manuscript to `docs/thesis/`.
- `pyproject.toml`, `config/config.yaml` (every parameter commented; unknowns are `null`), `Makefile`, `.gitignore`.
- `src/aparri/` package stubs, `io.py`, `runreport.py` (parameters, input sha256, versions, warnings).
- Smoke tests (imports, config sanity, raw-data protection, manifest integrity).

## Phase 2 — data audit (2026-10-03)
- `src/aparri/audit.py` (+ `audit_report.py`) -> `docs/01_data_audit.md`, `outputs/tables/audit_*.csv`, `outputs/maps/audit_*.png`.
- Key finding beyond the recon: 117 of 124 risk polygons are vectorised 30 m pixels (area = count x pixel area, 100 % on the pixel lattice); the 7 that carry all the Medium(2.59)/High labels are few-vertex, off-lattice, i.e. hand-drawn. 2010 lines contain a doubled stretch (56.7 km listed, ~39 km unique).
- Correction to `00_recon.md`: High pixels inside the eight official barangay polygons are ~1.4 ha (Linao 1.27, Maura 0.17), not 0 ha as first stated (I had mis-read a column in my first-pass table). The thesis claim "High in Bulala Sur/Norte" is supported only by the 2 hand-drawn polygons, not by the raster.

## Phase 2B — Earth Engine audit (2026-10-03)
- `src/aparri/audit_gee.py`, `scope.py` (open-coast rule via concave hull) -> `docs/01b_gee_audit.md`, `gee_*` tables/maps.
- 96 % of "accretion" pixels are open sea; 2025 edge mask 7.8x 1990 and 83 % in open water; no High pixel near an open-coast line; barangay CSV reproduced from 1 km circles.
