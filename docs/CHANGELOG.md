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

## Phase 3A/3B/3C (2026-10-03)
- `clean.py`: 20 legacy features -> 13 chains; "Hig" quarantined; 2010 doubled stretch (18.3 km) removed; open-coast vs river-bank tag; QGIS review package `data/interim/scope_review.gpkg`.
- `raster_shore.py`: edge masks -> skeleton -> lines; agrees with the vector set to a median 7-14 m on the open coast.
- `landsat.py` + `scripts/gee_v2.js`: written and unit-tested on synthetic data only (no route to Landsat in this sandbox).

## Phase 4 (2026-10-03)
- `transects.py`, `metrics.py`: DSAS-style engine, 10 synthetic-truth tests; 415 transects (50 m), 373 valid on the vector set.

## Phase 5 (2026-10-03)
- `risk.py`, `tables.py`, `maps.py`: classes, segments, Table 4.2 (xlsx/csv/docx), Figs 4.1/4.2 v2, EPR profile, legacy-vs-rebuilt; QGIS style file.

## Phase 6 (2026-10-03)
- `sensitivity.py`: 11 scenarios, EPR vs LRR, source agreement (92 % same class), empirical per-date error proposals (not applied), 20 field-verification points + form.

## Phase 7 (2026-10-03)
- `stats_survey.py`: schema, template, validator, alpha, weighted mean, Friedman/Wilcoxon-Holm, Kruskal-Wallis/Dunn-Holm, ranking by risk level (if data have it), weight sensitivity of the published means. 16 tests with hand computations; synthetic data refused for outputs/.

## Phase 8 (2026-10-03)
- `web.py`: offline Leaflet map (`outputs/web/index.html`), year slider/animation, popups, barangay zoom + Table 4.2 row, colour-blind palette, accessible table; headless smoke test.

## Phase 9 (2026-10-03)
- `docs/03_thesis_revision_notes.md` (38 items), `methods_draft.md`, `results_drafts.md`, `chapter5_skeleton.md`, `erosion_factors_plan.md`, `04_defense_qa.md` (25 Q&A), `for_the_adviser.md`.

## Phase 10 (2026-10-03)
- C `priority.py` (field-inspection ranking), D `qgis_project.py` (Aparri_v2.qgz; not opened in QGIS), E `annex.py` (Technical Annex docx/md), F `deck.py` (PPTX). A and B deliberately not done (D-13).
- Clean-clone check: `make setup && make test && make all` reproduces identical tables (md5 equal).
