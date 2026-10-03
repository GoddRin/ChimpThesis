# Decisions log

Each entry: decision, options considered, who decided, date. **Open questions for the students** are at the end.

Context: on 2026-10-03 the project owner (IT helper to the thesis group) delegated *all* technical and design decisions to the analyst (Claude) and pre-approved changes needed to make the thesis defensible. Decisions below are therefore recorded as "analyst, delegated". The students must still understand, verify and own them.

| ID | Decision | Options considered | Decided by | Date |
|----|----------|--------------------|-----------|------|
| D-01 | Repository root = project root (`CLAUDE.md` §3 layout, without the `aparri-gis/` wrapper). Uploads moved to `data/raw/` (read-only, sha256 manifest) and `docs/thesis/`; original archives kept in `data/raw/_archives/`. | Keep flat uploads / wrapper folder | analyst (delegated) | 2026-10-03 |
| D-02 | Skip interactive "plan mode" for each phase because the owner is not available for approval rounds and pre-approved everything; each phase writes its plan in `docs/CHANGELOG.md` instead. | Ask per phase | analyst (delegated) | 2026-10-03 |
| D-03 | **Primary shoreline set = `vector_clean`.** It is the only set that covers all eight barangays and all five years with a continuous open coast; the raster-derived set (cleaned Earth Engine masks) misses Bulala Sur and the last ~3 km of Paddaya (outside the old box) and is noisy in 2020/2025 over open water. The raster set is kept as the *independent check*: on the same transects it agrees to EPR r = 0.89 and the same class for 92 % of transects. Landsat v2 not available (D-04). | vector / raster / landsat | analyst (delegated) | 2026-10-03 |
| D-04 | Phase 3C (Landsat re-derivation) cannot be run in this environment: the Landsat catalogues (Planetary Computer, Earth Search) are unreachable and no Earth Engine login exists. Code + a ready-to-run GEE v2 script are provided and unit-tested on synthetic data only; results are NOT claimed. | Fabricate / skip / write runnable code | analyst | 2026-10-03 |
| D-06 | **Scope = open sea-facing coast only** (`scope.include_estuarine_banks: false`). River-bank rates are dominated by floods/bars and their transects cross; included in a sensitivity run only. | include / exclude | analyst (delegated) | 2026-10-03 |
| D-07 | Accreting transects are Low and tagged `accreting`. | Low / separate class | analyst (delegated) | 2026-10-03 |
| D-08 | Hectares in Table 4.2 = km of shoreline x a **100 m strip** (`risk.strip_width_m`); kilometres are the primary measure. 100 m chosen as a typical setback/coastal-zone width for a first indication; students may change it. | km only / strip 50-200 m / barangay land area | analyst (delegated) | 2026-10-03 |
| D-09 | One measuring grid (baseline and transects) built from the vector set's 1990 shoreline and used for every set, so sets can be compared transect by transect. | per-set baselines | analyst (delegated) | 2026-10-03 |
| D-10 | Uncertainty values stay `null`; the confidence column uses a clearly labelled +-30 m what-if; empirical proposals (7-12 m per date) are reported in `docs/05_sensitivity_validation.md` but not applied. | invent / apply proposals / null | analyst | 2026-10-03 |
| D-05 | Tools installed beyond CLAUDE.md §5: none in the project env. (Recon used scratch tools `7zip`, `libarchive-tools`, `pypandoc`.) | — | analyst | 2026-10-03 |

## Open questions for the students
(Carried over from `docs/00_recon.md` §3; updated as phases finish.)
