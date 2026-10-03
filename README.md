# Aparri coastal-erosion GIS — rebuilt, audited and documented

Support pack for the thesis **“Development of Construction Management Framework for Shoreline Protection Structures Based on Coastal Erosion Risk Levels in Aparri, Cagayan”** (CSU–Carig). The students own the thesis; everything here is a *draft for them to check, understand and defend*.

## Start here (open these first)
| What | Where |
|---|---|
| **Interactive map** (works offline; double-click) | `outputs/web/index.html` |
| **Table 4.2** (Excel / Word-ready) | `outputs/tables/Table_4_2_barangay_results.xlsx` · `.docx` |
| **Figures 4.1 / 4.2 / profile** (300 dpi) | `outputs/maps/Fig_4_1_v2_*.png` · `Fig_4_2_v2_*.png` · `Fig_4_3_*.png` |
| **GIS defense slides** | `outputs/defense/Aparri_GIS_defense_slides.pptx` |
| **Defense Q&A (25 questions)** | `docs/04_defense_qa.md` |
| **Memo for the adviser** | `docs/for_the_adviser.md` |
| **Edit list for the manuscript (38 items)** | `docs/03_thesis_revision_notes.md` |
| QGIS project | `outputs/layers/Aparri_v2.qgz` (see `README_QGIS.md`) |
| Technical annex for the appendix | `outputs/reports/Technical_Annex_GIS.docx` |

## What was found (short)
1. **The original GIS results cannot be used.** The risk polygons, the Earth Engine statistics and the raster change layers are inconsistent with each other and with the written method (`docs/01_data_audit.md`, `docs/01b_gee_audit.md`): 7 hand-drawn polygons carry every “Medium (2.59)” and “High” label, 96 % of the raster “accretion” is open sea, and the barangay statistics are 1 km circles around points.
2. **Rebuilt analysis** (cleaned shoreline lines → 415 transects every 50 m → EPR and LRR → the thesis’ own class limits): along the 18.8 km of classified open coast, 13.8 km is Low, 5.0 km Medium and **0.0 km High**. Median EPR -1.46 m/yr; the fastest barangay is Bulala Norte (-3.35 m/yr). **The old “High along Bulala” is replaced by Medium.**
3. **How sure?** An independent shoreline set gives the same class for 92 % of 253 transects. But a 30 m pixel is ±1.21 m/yr over 35 years, so Low-versus-Medium is uncertain for much of the coast; Bulala Norte is the clearest case. Class shares do not depend on technical choices (≤ 0.5 points) but do depend on the 2 and 5 m/yr limits themselves.
4. **Survey part:** Table 4.4 is arithmetically consistent (one 0.0001 rounding slip), the ranking is robust to criterion weights (96 % Seawall first), but the questionnaire has **no risk-level dimension**, so Objective 3 and Ho1 cannot be tested as written (`docs/06_survey_statistics.md`).

## What the students must supply (nothing here invents these)
Origin/dates/indicator of the shoreline lines · measured positional error and tide · raw survey responses and pilot α · a decision on Ho1/Objective 3 · field verification (form and 20 points provided) · checks of every `[VERIFY CITATION]` · the adviser’s agreement. Full list: `docs/decisions.md`.

## What was *not* done (and why)
Landsat re-derivation (no route to the satellite catalogues from the analysis environment; `scripts/gee_v2.js` is ready) · opening the QGIS project in QGIS (not installed) · exposure overlay and projections (see `docs/decisions.md` D-13) · any analysis of survey responses (none supplied) · field validation.

## Run it yourself
```
make setup && make test     # 85 automated tests
make all                    # rebuilds every table, map, document, the web map, deck and annex (~1 min)
```
All parameters: `config/config.yaml`. Raw data (`data/raw/`, read-only, SHA-256 manifest). Rules: `CLAUDE.md`. Decisions and open questions: `docs/decisions.md`. Changes: `docs/CHANGELOG.md`.

## Folder map
`config/` parameters · `src/aparri/` code · `tests/` tests (synthetic data only under `tests/fixtures/`) · `data/raw` inputs · `data/interim` cleaned shorelines + QGIS review package · `data/processed` transects and risk segments (per shoreline set) · `outputs/` tables, maps, layers, web, defense, field_validation, reports · `docs/` audit, method, drafts, Q&A · `scripts/gee_v2.js` · `data/templates/` blank survey and factors templates.
