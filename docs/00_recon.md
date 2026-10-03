# 00 — Reconnaissance report (read-only)

**Project:** Aparri coastal erosion — GIS rebuild & thesis support
**Date:** 2026-10-03  **Status:** recon only. No data was modified. This file is the only thing written to the repo.
**Labels used below:** **[CONFIRMED]** = I checked it with code or by reading the file. **[HYPOTHESIS]** = plausible but not proven. **[VERIFY CITATION]** = literature claim I could not check offline.

> **How this was produced.** The thesis `.docx` was converted with pandoc into a scratch folder (not the repo) and read end to end (Ch. I–V, appendices, all figures). Every archive was unpacked into the scratch folder and inspected with geopandas / rasterio. The `.qgz` was unzipped and its XML read. `Code.docx` was read line by line (§A.2).
> **Housekeeping to disclose.** To do this I installed small tools outside the repo (a Python venv in the scratch folder with geopandas, rasterio, pypandoc, matplotlib; `7zip` and `libarchive-tools` via apt, because the `.rar` files use RAR5). CLAUDE.md rule 10 says to ask before installing; these were light, but I should have asked. Nothing was downloaded from Earth Engine or any imagery service.
> **Note.** `PHASE_PROMPTS.md` (referenced by CLAUDE.md) was not among the files I received, so the phase plan in §4 is my proposal, not the official one.

---

## 1. Plain-English summary

### What the thesis says it did
Chapter III and IV say the students **digitized five shorelines** (1990, 2000, 2010, 2020, 2025) from satellite images, overlaid them (Fig. 4.1), and computed the **End Point Rate (EPR)**: the distance the shoreline moved between 1990 and 2025 (**NSM**, net shoreline movement, in metres) divided by 35 years. Negative = erosion, positive = accretion. Each shoreline segment was then classed Low (< 2 m/yr), Medium (2–5) or High (> 5), drawn as a risk map (Fig. 4.2), and summarised per barangay in Table 4.2 (mean/min/max EPR and hectares of Low/Medium/High). A 54-expert Likert survey then ranked five protection structures (Table 4.4), and a framework flowchart (Fig. 2) was drawn.

### What the files show was actually done
There are **three separate GIS products that were never reconciled**, and none of them matches the method written in the thesis:

| | Product | What it really is | Evidence |
|---|---|---|---|
| **A** | `Code.docx` + 9 GeoTIFFs + barangay CSV/SHP | A **Google Earth Engine** script: one **annual median Landsat composite** per year, water = **NDWI > 0**, "shoreline" = edge pixels of that water mask (30 m). Change is computed **between 1990 and 2025 only**. "NSM" is a pixel-distance approximation (the script itself says a transect method is "preferable for final research analysis"). | Script read in full; rasters inspected |
| **B** | `Shoreline Changes.shp` (20 lines) | **Vector lines of unknown origin.** Not made from the rasters (only 3.6 % of vertices sit on the 30 m pixel grid), so probably hand-drawn or contoured elsewhere. 3–6 fragments per year, wildly different vertex density per year, one feature with year = "Hig". | Vertex-grid test; attribute table |
| **C** | `Aparri Risk Ana.shp` = `…Risk_1990_2025.shp` (124 polygons) + `EPR Results.xlsx` | **Polygons of unknown origin.** 92 % of their vertices sit on the same 30 m pixel grid, so they were vectorised from some raster, but **not from the rasters we have**. Only three EPR values exist (0.857, 2.586, 5.726), i.e. class constants, not measurements. | Grid test; raster-vs-polygon overlay |

### Why the numbers cannot be trusted (all **[CONFIRMED]**)
1. **The raster "accretion" is mostly open sea.** Of the changed pixels, 31,240 (≈ 2,650 ha) are "accretion" and only 2,052 (≈ 174 ha) are "erosion". The accretion forms one giant block in the north-east corner of the raster, which is open sea. Cause (in the script): clouds / no-data are `unmask(0)` = treated as *land*, and a single fixed NDWI cut-off on an all-seasons median is used. So the 2025 shoreline mask is mostly noise (20,321 edge pixels vs ≈ 2,400–2,700 in 1990/2000/2010). **The years are not comparable.**
2. **The polygons cannot be reproduced from the rasters.** Polygons labelled *High* sit on pixels whose raster EPR is between −3.09 and +0.86 — none is High. 227 of the 259 pixels under "High" polygons are Low in the raster.
3. **"Medium" polygons include EPR = 0.857**, below the 2 m/yr cut-off (48 polygons, 21 ha). All polygon EPR values are positive, which under the thesis sign convention means *accretion*.
4. **The barangay statistics are made from 1 km circles around single points**, not barangay boundaries (the script says "temporary"). Because "Low" includes every unchanged pixel (sea and inland too), `Low_Risk_ha` ≈ the circle area (≈ 309 of ≈ 314 ha) for most rows. **Bulala Sur and Paddaya are outside the study box → NaN**; Dodan is clipped (34 ha).
5. **Using the official barangay polygons on the shipped rasters, High-risk is tiny and not where the thesis says:** the 88 High pixels (≈ 7.5 ha) give only ≈ 1.4 ha inside the eight polygons (Linao 1.27 ha, Maura 0.17 ha) and **0 ha in Bulala Sur / Bulala Norte** (Phase 2B recomputation; this corrects an earlier mis-read of my first-pass table). Most High pixels are around the Cagayan River mouth, outside the barangay land polygons.
6. **The positional error was never considered.** Landsat pixels are ≈ 30 m. If each date is good to one pixel, a two-date rate has an uncertainty of about √2 × 30 / 35 ≈ **1.2 m/yr** — about 60 % of the Low/Medium cut-off. *(Illustration only — the real error is unknown, see §3.)*

### Bottom line
Table 4.2 is empty probably because the GEE statistics looked wrong (its empty row order — Dodan, Maura, Bulala Norte, San Antonio, Linao, Paddaya, Punta, Bulala Sur — is exactly the order of the GEE CSV **[CONFIRMED]**). Figures 4.1 and 4.2 came from products **B** and **C**, which have no demonstrated link to each other, to A, or to the written method. **The shoreline-change chapter has to be rebuilt, not repaired.** The survey part (Table 4.4) is internally consistent (§2), but it cannot answer Objective 3 or test Ho1 because the questionnaire never asks about risk levels.

---

## 2. Requirements matrix

Status key: **done** = exists and checks out · **suspicious** = exists but fails a check · **missing** = absent or empty · **unverifiable** = looks fine, but the raw data to check it was not supplied.

### 2.1 Objectives and hypothesis

| Item | Needs (GIS / statistics output) | Status | Notes |
|---|---|---|---|
| **Obj 1** Classify risk Low/Med/High | Shorelines at 5 dates → baseline + transects → NSM/EPR per transect → classify with Table 3.1 thresholds → map + per-barangay summary | **suspicious** | Only legacy products A/B/C exist; see §1. Needs rebuild |
| **Obj 2** Most suitable structures (efficiency & feasibility) | Respondent-level Likert data → weighted mean per structure × criterion; Cronbach's α | **unverifiable** | Table 4.4 present; I re-computed overall means = mean of the 6 criteria, all five match to 4 decimals, and all means are multiples of 1/54, consistent with n = 54. Raw responses not supplied |
| **Obj 3** Rank structures *per risk level* | Ratings given separately for Low / Medium / High sites, or a mapping rule from risk level → structure | **missing** | Questionnaire (Appendix B) has one block of 6 statements per structure and **no risk-level dimension**. Table 4.4 is one overall ranking |
| **Obj 4** Construction-management framework | Framework content for each risk level, linked to Obj 1–3 | **missing** | Fig. 2 is a generic 4-step flowchart. Ch. IV has no section for Obj 3, Obj 4 or the framework |
| **Ho1 / Ha1** Risk levels differ in perceived efficiency/feasibility | A test comparing ratings across risk levels | **missing** | Cannot be tested with the current instrument. Candidate re-framings are in §3 (Q-S4) |

### 2.2 Tables

| Table | Needs | Status | Notes |
|---|---|---|---|
| 3.1 Risk thresholds | Config values | **done / inconsistent** | Source differs: Table 3.1 says "adapted from coastal geomorphology studies"; Table 4.1 cites Osondu et al. 2025 (Nigeria). Ch. II credits Luijendijk 2018 for ">5 m/yr" **[VERIFY CITATION]**. Boundary wording: "2–5" vs. GEE inclusive [2, 5] |
| 3.2 Decision-matrix template | — | **done** | Filled as Table 4.4 |
| 4.1 (a) Risk classification table | — | **done**, number **duplicated** | Same title as Table 3.1 |
| **4.2 (a) Barangay EPR & risk areas** | Per barangay: mean/min/max EPR (m/yr), ha Low/Med/High, from transects + proper barangay attribution | **missing** (headers + one row only) | 8 rows required incl. Bulala Sur and Paddaya, which the GEE box excludes. "Hectares" of a *shoreline* class needs a defined buffer/zone — open design choice (Q-G9) |
| 4.1 (b) Professional background | Survey data | **unverifiable** | 21+18+12+1+2 = 54; percentages re-computed OK. Number clashes with 4.1 (a) |
| 4.2 (b) Years of experience | Survey data | **unverifiable** | 29+16+6+3 = 54, OK. Number clashes with 4.2 (a). 53.7 % have < 5 years' experience |
| 4.3 Experience/familiarity/training | Survey data | **unverifiable** | Only 15/54 (27.8 %) ever worked on or supervised a shoreline structure — a validity point to address in the text |
| 4.4 Weighted-mean decision matrix | Survey data; interpretation scale | **unverifiable (arithmetic OK)** | Scale bands 4.21/3.41/2.61/1.81 match the text; all interpretation labels re-checked. No SD, no significance test. All five structures score ≥ 3.6, so little discrimination |
| Cronbach's α | Pilot (and final) responses | **missing** | Method says α ≥ 0.70 and a pilot test; no value reported anywhere |

### 2.3 Figures

| Figure | Needs | Status | Notes |
|---|---|---|---|
| Conceptual framework | — | **suspicious** | Lists "Google Earth Pro" and "QGIS" as inputs; the real pipeline used Landsat via Earth Engine. "Field observation" and "pilot testing" appear but no results exist |
| Fig. 1 Study area | Barangay polygons | **done** | Same as `Study Map.jpeg`. Scale bar on the thesis exports (2.5 km) and the later QGIS exports (5 km) differ |
| Fig. 2 Framework flowchart | — | **done (generic)** | Not risk-level specific |
| **Fig. 4.1** Five shorelines | Cleaned, comparable lines | **suspicious** | From product B (unknown origin). Text says "According to Figure 4.2" where 4.1 is meant |
| **Fig. 4.2** Risk map | Classified shoreline segments | **suspicious** | From product C. The newer QGIS exports in the project folder (`Erosion Risk Map.jpeg`, `Multi Temporal Risk.jpeg`) show **only green (Low) cells and are mis-titled**, so the figure in the manuscript cannot be regenerated from the saved project as it stands |
| (missing) | Uncertainty, rate profile along the coast, survey charts | **missing** | Not promised, but a defense panel will ask |

### 2.4 Other manuscript requirements

| Item | Status | Notes |
|---|---|---|
| Methodology describes the real GIS workflow | **missing** | No mention of Landsat, NDWI, Earth Engine, image dates, resolution, transects, baseline, tide, error. Says shorelines were "digitized" |
| "Future shoreline projections" (Definition of GIS) | **missing** | Promised, never done |
| "Coastal erosion factors" (framework, title, definitions) | **missing** | No data or results section; field checklist results absent |
| Chapter V (Summary, Conclusion, Recommendations) | **missing** | Still the blank template text |
| Abstract / Proposal Summary | **outdated** | Written as a proposal ("will"); needs results |
| Wording errors | **to fix** | Table numbers 4.1/4.2 used twice; "Figure 4.2" for 4.1; "analyzed using the to determine…"; "shoreliSelectin e rates"; mixed future/past tense |
| Citation integrity | **to verify** | In-text claims that do not obviously match the listed titles **[VERIFY CITATION]**: *Nerves et al. 2024* is described as a river-delta study with "150+ m in 30 years" but the reference is a DSAS study in New Washington, Aklan; *Calapini et al. 2025* is cited for sea-level-rise rates but the reference is a flood-hazard model; "Ouyang & Wang, 2024" does not match the listed "Zhang, Ouyang, …, 2024" |
| Approval sheet | **ask** | Says "recommended for proposal defense" (dated 29 April 2026) yet Ch. IV has results. Which defense is next? |

---

## 3. Missing inputs and open questions for the students

**G = GIS · S = survey/statistics · M = manuscript.** Priority: **A** blocks the rebuild, **B** needed before final numbers, **C** can wait.

### GIS (shoreline) — priority A first
| # | Question | Why it matters |
|---|---|---|
| **Q-G1 (A)** | **Who produced the 20 shoreline lines (product B) and how?** Hand-digitized, auto-contoured, or exported from somewhere? From which imagery and which dates? Is there a file called **`Shoreline Changes 1990-2025.shp`**? (the QGIS project points to that name; the file supplied is `Shoreline Changes.shp`) | Determines whether B can be used at all |
| **Q-G2 (A)** | **Who produced the 124 risk polygons (product C)?** Which script/run/AOI? They cover x 121.563–121.754, wider than the shipped rasters (121.580–121.720). Is there another GEE run or export? (The QGIS project mentions two different export folders: `Final_Aparri_Erosion_Assessment` and `Aparri_Erosion_Assessment-20260917…`.) | Explains why polygons ≠ rasters |
| **Q-G3 (A)** | **Imagery source and exact acquisition dates** for each of the five years. Were Landsat scenes used for all five? Which sensors? Any higher-resolution imagery (Google Earth Pro, per the conceptual framework)? | Needed for tide / season / comparability and for the methodology text |
| **Q-G4 (A)** | **Shoreline indicator**: waterline, vegetation line, high-water line, wet/dry sand line? Which one does each product use? | EPR is meaningless if the indicator changes between years |
| **Q-G5 (B)** | Who wrote `Code.docx`? (It contains the phrase "the coordinates you previously provided", which reads like a chat-assistant output.) Was it ever run end to end by the students, and with what image counts per year (`IMAGE COUNT` printout)? | Authorship matters for defense; image counts show how thin 1990/2000 are |
| **Q-G6 (B)** | **Field data**: GPS shoreline points, photos, observation checklists, interviews with LGU/MDRRMO/DPWH? Any historical maps or protection-structure inventory (locations of existing seawalls etc.)? | Only independent check on the satellite shorelines; also needed for "coastal erosion factors" |
| **Q-G7 (B)** | **Positional error**: any estimate of georeferencing / digitizing error per date? | Needed for EPR uncertainty and for deciding whether a 2 m/yr threshold is even resolvable |
| **Q-G8 (B)** | Source of the barangay boundaries (`Aparri Barangays.shp`: 45 polygons, PSA-style PCODE fields, "UPDATED 2017-12-31") and agreement with the LGU's boundaries | Table 4.2 depends on them |
| **Q-G9 (B)** | What is "area in hectares of Low/Medium/High" supposed to mean for a *shoreline*? A buffer (e.g. 100 m) behind each classified segment? Land area per barangay? | Defines the Table 4.2 columns; the GEE version measured pixels in a circle |
| **Q-G10 (B)** | Should the Cagayan River mouth / estuary banks and sandbars be inside the analysis? The legacy lines include river-mouth loops | Estuary shorelines move for different reasons and dominate the largest "changes" |
| **Q-G11 (C)** | Were 2000/2010/2020 shorelines meant to feed a rate (LRR / WLR over all five dates) or only be displayed? Thesis says display-only EPR (1990→2025) | With five dates a regression rate is possible and much more robust |

### Survey / statistics
| # | Question | Why it matters |
|---|---|---|
| **Q-S1 (A)** | **Respondent-level data** (54 rows × 30 Likert items + profile questions), in Excel/CSV | Needed to verify Table 4.4, compute SD, α, and any test |
| **Q-S2 (A)** | **Pilot-test results** — sample size and Cronbach's α. Was the pilot done? | Method promises α ≥ 0.70; nothing reported |
| **Q-S3 (B)** | How were the 54 respondents chosen (purposive)? Response rate? Any exclusion? Consent forms? | Defense panel will question 54 respondents, 53.7 % with < 5 yrs experience, 72 % never on a shoreline project |
| **Q-S4 (A)** | **Per-risk-level ratings**: did anyone rate structures for Low / Medium / High sites? If not, how should Obj 3 and Ho1 be handled? Options: (a) re-survey with risk-level items; (b) a defensible rule-based mapping from the overall criteria scores to risk levels, clearly labelled as the students' framework logic; (c) re-word Ho1 to "perceived suitability differs among the five structures" and test that (Friedman / ANOVA) | The current Ho1 cannot be tested. This is a research-design decision for the students and adviser |
| **Q-S5 (C)** | The "Cost" criterion: is a higher score = cheaper (statement is "cost-effective solution") — and do all six statements point the same way (e.g. "maintenance is manageable")? | Averaging only makes sense if all items are scored in the same direction |

### Manuscript / process
| # | Question | Why it matters |
|---|---|---|
| **Q-M1 (A)** | Which defense is next, and the deadline? | Sets how much can be rebuilt |
| **Q-M2 (A)** | Is the adviser aware the GIS results came from a third party, and does the department accept a corrected method chapter? | Students must be able to defend any change in method |
| **Q-M3 (B)** | Are the students willing to re-derive shorelines from Landsat (requires internet access to Earth Engine or a public STAC catalogue; possibly an Earth Engine login)? Or must we only work with files in hand? | Decides Phase 3 route |
| **Q-M4 (C)** | Who holds the original `.docx`, figures and the questionnaire forms? Is the version in this repo the latest? | Avoid editing a stale copy |

---

## 4. Proposed work plan (Phases 1–10)

*Titles are my proposal, aligned with the Makefile targets and Phase 2/2B mentioned in CLAUDE.md. Each phase starts in plan mode, ends with `make test` and a STOP.*

| # | Phase | Main outputs | Key risks / flags | Gate |
|---|---|---|---|---|
| **1** | **Scaffold & intake** — create the layout from CLAUDE.md §3, `config/config.yaml` (thresholds, years, CRS, nulls for unknown values), `pyproject.toml`, Makefile, sha256 manifest. Move the uploaded archives into `data/raw/` (read-only) and the manuscript into `docs/thesis/`. | Empty-but-runnable pipeline; `docs/decisions.md` with the §3 questions | **The repo currently has every upload at its root and no `data/raw/`** — moving files needs approval. No CLAUDE.md in the repo yet | STOP |
| **2** | **Data audit** — turn every finding in this report into code that prints evidence; `docs/01_data_audit.md` | Reproducible audit; list of defects with counts | Easy to over-claim: keep the [CONFIRMED]/[HYPOTHESIS] split | STOP |
| **2B** | **Reconcile A / B / C** — where do the lines and polygons come from; map overlaps; decide what is reusable | Reconciliation note; decision on reuse | May conclude "none reusable" | **STOP — students decide route (Q-M3)** |
| **3** | **Shoreline rebuild** — one consistent shoreline indicator for 5 dates. Preferred route (explainable): Landsat Collection 2 scenes, per-year *dry-season* multi-scene composites with valid-pixel masks, NDWI with a per-year threshold (Otsu), sub-pixel contour (scikit-image), then visual QC in QGIS. Alternative: students digitize on imagery in QGIS (matches the thesis wording, but 1990 high-resolution imagery is unlikely to exist) | `data/interim/shorelines_<year>.gpkg`, QC log, human-review list | **Biggest risk.** Needs imagery/Earth Engine access; 1990 and 2000 Landsat coverage for Aparri may be sparse/cloudy; tide state and river discharge unknown; estuary vs open coast behave differently. **Never** treat masked pixels as land | STOP |
| **4** | **Baseline, transects, metrics** — baseline, transects every N m (config), NSM, EPR (1990→2025) as in the thesis, plus LRR/WLR over all five dates, with uncertainty | `transects.gpkg`, per-transect table, uncertainty column | Uncertainty may be about as large as the 2 m/yr class boundary → many segments will be statistically indistinguishable from "Low"; the students must be ready to say so. All math in EPSG:32651 | STOP |
| **5** | **Risk classification & barangay attribution** — classify transects with Table 3.1; assign to barangays with a nearest-join + tolerance (plain intersection loses Bulala Sur); fill Table 4.2; threshold-sensitivity table | Risk layer `.gpkg` + `.qml`, Table 4.2 (CSV/XLSX) | "Hectares" definition (Q-G9); inclusive/exclusive boundary at exactly 2 and 5; river-mouth treatment (Q-G10) | STOP |
| **6** | **Survey statistics tooling** — weighted mean, SD, Cronbach's α, ranking, profile tables, chosen test for Ho1 | `stats_survey.py`, tables regenerated from raw responses | **Blocked until respondent data arrive (Q-S1).** Tooling can be tested on SYNTHETIC fixtures only, labelled and kept out of `outputs/`. Ho1 decision (Q-S4) belongs to the students | STOP |
| **7** | **Maps & tables** — redraw Fig. 4.1 and 4.2 in the thesis style (300 dpi, 2.5 km scale bar, north arrow), plus an uncertainty figure and a rate-along-the-coast chart | `outputs/maps/*.png`, `outputs/tables/*` | Style consistency with the existing figures; no basemap licensing issue if using OSM/Esri tiles — check attribution | STOP |
| **8** | **Interactive defense map** — static HTML (Leaflet/MapLibre) with layers, popups, transect profiles | `outputs/web/` | Must work offline on a defense laptop; keep file sizes small | STOP |
| **9** | **Thesis revision notes & draft text** — `docs/03_thesis_revision_notes.md` with exact replacement text for Ch. III method, Ch. IV results, Ch. V, plus the numbering/typo fixes in §2.4 | All drafts labelled `[DRAFT – FOR STUDENT REVIEW]` | Do not invent citations; mark `[VERIFY CITATION]`. Students must be able to defend every sentence | STOP |
| **10** | **Defense pack & hand-over** — `docs/04_defense_qa.md` (likely panel questions with honest answers, incl. "why did the numbers change?"), reproducibility check from a clean checkout, CHANGELOG | Q&A, `make all` from scratch, run report with hashes | The "numbers changed" story needs adviser buy-in (Q-M2) | Final STOP |

**Cross-cutting risks**
1. The rebuilt numbers will probably differ materially from Fig. 4.2 and from the thesis narrative (High at Bulala Sur/Norte, Low at Linao). The students need to hear this early.
2. Landsat's 30 m pixel is coarse for a 2 m/yr threshold (see §1, point 6). A plain statement of uncertainty is more defensible than a falsely precise map.
3. No field data, no tide records, no imagery dates: every time one is missing the pipeline must carry `null` and a loud warning, never a guess (rule 2).
4. Survey objectives 3–4 are a research-design issue, not a software one; I can build tools but cannot decide the design.

---

## 5. Decisions I need from you

1. Approve the file layout move in Phase 1 (everything is currently flat at the repo root).
2. Confirm that the Phase 3 route may use the internet (Earth Engine or a public Landsat catalogue), or tell me to stay with local files.
3. Share `PHASE_PROMPTS.md` if it differs from the plan above, and forward the §3 questions (especially Q-G1–G4, Q-S1, Q-S4, Q-M1) to the students.

---

## Appendix A — Inventory of what was supplied

All archives were extracted to scratch. Duplicates: `Aparri.rar` inside the Drive zip is byte-identical to the repo-root `Aparri.rar`; the shapefile inside `Aparri_MultiTemporal_Erosion_Risk_1990_2025.zip` is byte-identical (same sha256) to `Aparri Risk Ana.shp` inside `Aparri.rar`; `CE-Project-Manuscript-Format.docx` is identical in repo and upload.

### A.1 Vector data (all EPSG:4326; none in a metric CRS)
| File | Type | Size | Features | Columns | Notes |
|---|---|---|---|---|---|
| `Shoreline Changes.shp` | LineString | 29 kB | 20 | `id` (all empty), `1990` (text, 80) | Column is literally named "1990" and holds the year; values 1990×3, 2000×3, 2010×4, 2020×3, 2025×6, **"Hig"×1**. Extent 121.5628–121.7547 E, 18.3194–18.3920 N. Length per year (UTM 51N): 1990 35.4 km (142 vertices), 2000 41.1 km (328), 2010 56.7 km (670), 2020 35.5 km (337), 2025 40.8 km (262). Fragments never joined; QGIS project expects `Shoreline Changes 1990-2025.shp` (not supplied) |
| `Aparri Risk Ana.shp` ≡ `Aparri_MultiTemporal_Erosion_Risk_1990_2025.shp` | Polygon (102) / MultiPolygon (22) | 29 kB | 124 | `Risk_Level` (text **width 3**), `EPR_90_25`, `count`, `Risk_Code`, `label` | `Risk_Level` values **LOW 69 / Med 53 / Hig 2**; "Hig" and "Med" are **dbf truncations** (3-character field). `Risk_Code` and `label` are **1 in every row** (useless). 3 invalid geometries. Areas (UTM): High 35.7 ha, Medium 48.5 ha (of which 21.0 ha at EPR 0.857), Low 84.6 ha. `count` (1252) is not the pixel count of the polygons (≈ 1,717 px covered) — meaning unknown |
| `Aparri_Brgy_Study.shp` | Polygon | 2 kB | 8 | PSA-style admin fields | The eight study barangays. Areas (ha): Paddaya 1733, Dodan 625, Linao 409, Maura 399, Bulala Sur 219, Bulala Norte 139, Punta 42, San Antonio 17 |
| `Aparri Barangays.shp` | Polygon | 10 kB | 45 | same | All Aparri barangays, "UPDATED 2017-12-31" |
| `Aparri_Barangay_Erosion_Statistics_1990_2025.shp/.csv` | Polygon (circles) | 4 kB | 8 | `Mean/Min/Max_EPR`, `…NSM`, `Low/Medium/High_Risk_ha`, `Erosion/Accretion_Area_ha` | 1 km-radius circles around points (≈ 314 ha). Low ha: Maura 309.4, San Antonio 309.1, Punta 309.2, Linao 308.4, Bulala Norte 115.0, Dodan 34.2, **Paddaya 0, Bulala Sur 0 (EPR = NaN)**. High ha: only Linao 0.42. Shapefile truncates field names (e.g. `Medium_Ris`) |

### A.2 Rasters (GEE exports) — all EPSG:4326, 521 × 223 px, 1 band, no nodata value
Bounds 121.5798–121.7202 E, 18.3299–18.3900 N. Pixel 0.00026949° ≈ 28.5 m E-W × 29.8 m N-S (not square in metres; ≈ 0.085 ha).
| File | dtype | Values |
|---|---|---|
| `Aparri_Shoreline_{1990,2000,2010,2020,2025}.tif` | uint8 | 0/1; edge-pixel counts 2,589 / 2,711 / 2,367 / 7,433 / **20,321** |
| `Aparri_Erosion_Accretion_1990_2025.tif` | uint8 | **0 = none (82,891), 1 = erosion (2,052), 2 = accretion (31,240)** — legend inferred from the script (§14–15, §37) |
| `Aparri_NSM_1990_2025.tif` | float32 | −2,871.2 … +517.9 m; smallest non-zero |value| = 30 m (pixel multiples) |
| `Aparri_EPR_1990_2025.tif` | float32 | −82.04 … +14.80 m/yr; 128 distinct values; smallest non-zero 0.857 (= 30/35) |
| `Aparri_Erosion_Risk_1990_2025.tif` | uint8 | **1 Low 115,708 · 2 Medium 387 · 3 High 88** |

### A.3 QGIS project `Aparr_Project.qgz` (QGIS 3.44.11, saved by "Admin" 2026-10-01)
Project CRS **EPSG:3857** (do not measure in it). Layers: Shoreline Changes 1990-2025 (**broken link**, categorized on field `1990`), five `Aparri_Shoreline_YYYY.tif` (**broken**, `../../../Downloads/Final_Aparri_Erosion_Assessment/`), Risk (**broken**, `Downloads/Aparri_Erosion_Assessment-20260917T050811Z-1-001/…`, categorized on `Risk_Level` = LOW / Med / Hig), Aparri_Brgy_Study and Aparri Barangays (local, OK), basemaps: Esri Light Gray, ESRI OSM Standard (vector tiles), Google Satellite (XYZ). Only Risk, Brgy_Study and OSM are ticked. Also supplied: 3 print-layout templates (`.qpt`) and exported maps. The 4 JPEGs in the rar differ from the thesis figures (thesis versions are 1968 px re-encodes; `Erosion Risk Map.jpeg` and `Multi Temporal Risk.jpeg` show only green cells and look like drafts).

### A.4 Other
`EPR Results.xlsx` — two versions: Drive copy has 124 rows with `High / LOW / Med`; the copy inside `Aparri.rar` is identical except 5 Medium rows have blank `count/Risk_Code/label`. Same content as the risk-polygon attribute table (totals differ by one count in Medium; row order differs from the shapefile). The xlsx says "High" where the shapefile has "Hig".

### A.5 Google Earth Engine script (`Code.docx`) — what each block does, with the problems
| Block | Does | Problem |
|---|---|---|
| §1 | AOI box 121.58–121.72 E, 18.33–18.39 N | Excludes Bulala Sur (121.566) and Paddaya (18.310); clips Dodan (18.324) |
| §2 | NDWI threshold 0.0, SCALE 30, years 1990–2025 (35 y) | Fixed threshold, no calibration, no tide |
| §3–5 | Landsat 4/5/7/8/9 Collection 2 L2; QA_PIXEL masks (fill, dilated cloud, cloud, shadow; cirrus for OLI) | No snow/water-confidence handling; **Landsat 7 SLC-off stripes** enter the 2010 composite |
| §6 | Sensor rule: year ≤ 2012 → L4+L5+L7; ≤ 2020 → L8; else L8+L9. **Median of the whole calendar year**, clipped to AOI | Mixes all seasons, tides and river stages; image count only printed, never saved |
| §7–9 | NDWI = (Green−NIR)/(Green+NIR) > 0 → water mask (`selfMask`) | Masked/cloud pixels become "not water" |
| §11 | Shoreline = `focalMax ≠ focalMin` of `water.unmask(0)` (3×3 edge) | A **two-pixel-wide edge band**, not a line; any noisy speckle creates "shoreline" (hence 20k px in 2025) |
| §13–15 | Erosion = old land & new water; accretion = old water & new land (**only 1990 vs 2025**) | 2000/2010/2020 never used in any rate; cloud holes = "land" |
| §17–19 | Distance to 1990 (erosion) or 2025 (accretion) shoreline × 30; EPR = NSM / 35 | Raster-distance approximation (script admits it); distance measured from the edge band, assigned to every changed pixel; ×30 ignores the real 28.5/29.8 m pixel; transform clamped at 256 px (reaching −2,871 m) |
| §22–24 | Risk: default 1 (Low); `EPR < 0` and 2 ≤ \|EPR\| ≤ 5 → 2; `EPR < 0` and \|EPR\| > 5 → 3 | Header comment says "\|EPR\|" but code requires erosion; accretion, stable *and open sea* are all "Low" |
| §26–27 | Total erosion / accretion area | Printed only; values not saved |
| §28–31 | 8 points → **1 km buffers**; mean/min/max EPR & NSM; ha of Low/Medium/High/Erosion/Accretion | Script says "TEMPORARY… replace with official boundaries". Means include all zero pixels, so Mean EPR ≈ 0 by construction |
| §32–38 | Exports CSV, SHP, six single-band GeoTIFFs | No CRS argument (→ EPSG:4326), no metadata saved; `reduceToVectors` polygons are **not** produced by this script |

*Nothing in the script produces the vector shorelines, the risk polygons, or `EPR Results.xlsx`.*

---

## Appendix B — Evidence snapshots (re-runnable in Phase 2)

* Vertex-on-grid test (tolerance 2 % of a pixel): shoreline lines 3.6 % / 3.9 % (x / y) → not raster-derived; risk polygons 93.0 % / 92.6 % → raster-derived.
* Raster classes under the risk polygons (pixels): *Low* polygons cover raster Low 605 / Med 319 / High 72; *Med* polygons cover 450 / 10 / 2; *High* polygons cover 227 / 32 / 0. Of the 88 raster-High pixels, 74 lie inside some polygon, 72 of those inside *Low* polygons.
* Raster EPR under the *High* polygons: min −3.09, median 0.0, max +0.86 m/yr.
* Official study polygons vs. rasters: Bulala Sur 0 % inside the raster; Paddaya 32 of 1,733 ha; Dodan 179 of 625 ha; Bulala Norte 45 of 139 ha; the other four are covered. Risk-polygon overlay with the 8 polygons: no Bulala Sur row (nearest polygon is 5.3 m away → needs a tolerance join); 53 of 124 risk polygons (62 ha, mostly Low) lie outside every study barangay.
* Table 4.4: overall mean = average of the six criteria for all five structures (differences < 0.00005).
