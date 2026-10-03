# Decisions log

Each entry: decision, options considered, who decided, date. **Open questions for the students** are at the end.

Context: on 2026-10-03 the project owner (IT helper to the thesis group) delegated *all* technical and design decisions to the analyst (Claude) and pre-approved changes needed to make the thesis defensible. Decisions below are therefore recorded as "analyst, delegated". The students must still understand, verify and own them.

| ID | Decision | Options considered | Decided by | Date |
|----|----------|--------------------|-----------|------|
| D-01 | Repository root = project root (`CLAUDE.md` §3 layout, without the `aparri-gis/` wrapper). Uploads moved to `data/raw/` (read-only, sha256 manifest) and `docs/thesis/`; original archives kept in `data/raw/_archives/`. | Keep flat uploads / wrapper folder | analyst (delegated) | 2026-10-03 |
| D-02 | Skip interactive "plan mode" for each phase because the owner is not available for approval rounds and pre-approved everything; each phase writes its plan in `docs/CHANGELOG.md` instead. | Ask per phase | analyst (delegated) | 2026-10-03 |
| D-03 | Primary shoreline set: **decided in Phase 3B/6** after the comparison (see entry below once made). Default in config until then: `vector_clean`. | vector / raster / landsat | analyst (delegated) | pending |
| D-04 | Phase 3C (Landsat re-derivation) cannot be run in this environment: the Landsat catalogues (Planetary Computer, Earth Search) are unreachable and no Earth Engine login exists. Code + a ready-to-run GEE v2 script are provided and unit-tested on synthetic data only; results are NOT claimed. | Fabricate / skip / write runnable code | analyst | 2026-10-03 |
| D-05 | Tools installed beyond CLAUDE.md §5: none in the project env. (Recon used scratch tools `7zip`, `libarchive-tools`, `pypandoc`.) | — | analyst | 2026-10-03 |

## Open questions for the students
(Carried over from `docs/00_recon.md` §3; updated as phases finish.)
