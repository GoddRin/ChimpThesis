# CLAUDE.md — Aparri Coastal Erosion: GIS Rebuild & Thesis Support

> Persistent context. Read this at the start of every session. Phase tasks come
> separately (see `PHASE_PROMPTS.md`). If a phase prompt conflicts with this file,
> stop and ask.

## 1. Mission

Support a 4th-year Civil Engineering thesis at Cagayan State University – Carig
Campus: **"Development of Construction Management Framework for Shoreline
Protection Structures"**, study area **Aparri, Cagayan, Philippines**
(barangays: Linao, Maura, Punta, San Antonio, Bulala Sur, Bulala Norte, Dodan,
Paddaya; shoreline 1990, 2000, 2010, 2020, 2025).

The GIS results in the manuscript were produced by a paid third party who can no
longer be contacted. The method is only partly documented (a Google Earth Engine
script, `Code.docx`, explains the raster part; the origin of the vector shoreline lines
and of the risk polygons is still unknown) and the numbers show signs of being
unreliable (see §4). Your job is to:

1. **Audit** the existing QGIS deliverables.
2. **Rebuild** the shoreline-change analysis in a transparent, reproducible,
   documented pipeline (Python, QGIS-compatible outputs).
3. **Fill the gaps** in the thesis (empty Table 4.2, statistics, survey analysis
   tooling, interactive defense map, revision notes).
4. **Never fabricate** data, results, citations, or conclusions.

The user (an IT graduate) is helping his girlfriend's civil-engineering thesis
group. The students own the thesis. You build tools and drafts; they must
understand, verify and defend everything. Prefer explainable methods over clever ones.

## 2. Hard rules (non-negotiable)

1. **Raw data is read-only.** Never modify, move or overwrite anything in `data/raw/`
   or `docs/thesis/`. Work on copies in `data/interim/` and `data/processed/`.
2. **No invented numbers.** If an input is missing (imagery dates, positional
   error, respondent-level survey data), say so, leave the config value `null`, and
   make the pipeline emit a loud warning. Synthetic data is allowed **only** under
   `tests/fixtures/`, must be labelled `SYNTHETIC`, and must never appear in
   `outputs/`.
3. **No invented citations.** Do not add references you cannot verify. Mark any
   literature suggestion `[VERIFY CITATION]`.
4. **Every change to data is logged** (what, why, how many features). Silent
   fixes are forbidden. Ambiguous cases go to a human-review list, not a guess.
5. **Units and CRS are explicit everywhere.** Compute in **EPSG:32651** (WGS 84 /
   UTM 51N, metres). Source data is EPSG:4326 (the GEE rasters too); the legacy QGIS project is EPSG:3857
   (do not measure in 3857 or in degrees).
6. **Sign convention (matches thesis):** shoreline change is positive seaward
   (accretion) and **negative landward (erosion)**, in metres / metres per year.
7. **Thesis thresholds** (Table 3.1): Low `< 2` m/yr, Medium `2–5` m/yr (inclusive),
   High `> 5` m/yr of *erosion* (landward) rate. Keep them in config, not hard-coded.
8. **Decision gates:** when a phase says STOP, stop, summarize, list open
   questions, and wait for the user.
9. **Draft text for the thesis is always labelled** `[DRAFT – FOR STUDENT REVIEW]`.
10. Ask before installing anything heavy, running network downloads, or deleting files.

## 3. Repository layout (create if missing)

```
aparri-gis/
├── CLAUDE.md
├── PHASE_PROMPTS.md
├── Makefile                 # make setup | audit | clean | transects | risk | tables | maps | web | test | all
├── pyproject.toml           # pinned deps (use uv or venv)
├── config/config.yaml       # ALL parameters live here
├── docs/
│   ├── thesis/CE-Project-Manuscript-Format.docx   # READ-ONLY reference
│   ├── 00_recon.md  01_data_audit.md  02_method.md  03_thesis_revision_notes.md
│   ├── 04_defense_qa.md  decisions.md  CHANGELOG.md
├── data/
│   ├── raw/                 # READ-ONLY: Aparri/ (QGIS project), shoreline_changes/, risk_zip/,
│   │                        #   gee_outputs/ (Code.docx, *.tif, barangay stats csv/shp, xlsx, jpgs)
│   ├── interim/             # cleaned lines, transects
│   └── processed/           # final analysis layers
├── src/aparri/              # io.py clean.py transects.py metrics.py risk.py stats_survey.py maps.py web.py
├── tests/                   # unit tests + tests/fixtures/ (synthetic only)
└── outputs/
    ├── tables/  maps/  layers/  web/  reports/
```

## 4. What is already known (verify, don't trust)

Treat these as **hypotheses from a first-pass inspection**. Confirm each one with
code in Phases 2/2B and record the evidence. There are **three separate legacy products
that were never reconciled**:

**(A) Raster pipeline — Google Earth Engine (`data/raw/gee_outputs/Code.docx` + `*.tif`)**
- Landsat Collection 2 Level-2: L4/L5/L7 for years ≤ 2012, L8 for 2013–2020, L8+L9 for
  2021+. One **annual median composite** per year (Jan–Dec, all seasons and tides mixed).
  Only cloud/shadow masking from QA_PIXEL. Study box `[121.58–121.72 E, 18.33–18.39 N]`.
- Water = NDWI (Green–NIR) **> 0**, fixed threshold, no per-scene calibration.
  "Shoreline" = pixels where a 1-pixel focal max ≠ focal min (an edge-pixel mask), 30 m.
- Erosion/accretion = land↔water change between **1990 and 2025 only**; the intermediate
  years (2000/2010/2020) are not used in any rate. NSM = `distance-to-1990-shoreline × 30`
  (negative for eroded pixels) — the script's own comment calls it "a raster-distance
  approximation; a transect-based NSM is preferable for final research analysis".
  EPR = NSM / 35. Risk: accretion/stable → Low; erosion |EPR| < 2 Low, 2–5 Medium, > 5 High.
- **Barangay statistics use 1 km radius circles around single point coordinates**, not
  barangay boundaries (the script says "temporary… replace with official boundaries").
  Because "Low risk" includes all unchanged pixels (land and sea), `Low_Risk_ha` ≈ the
  circle area (~309 of ~314 ha) for most barangays: it is not a meaningful coastal area.
- Study box excludes the points of **Bulala Sur and Paddaya** (and clips Dodan): the exported
  statistics for those barangays are NaN/zero. Check this against Table 4.2 requirements.
- Rasters on disk: 521 × 223 px, EPSG:4326, ~28.5 m, `Shoreline_YYYY`, `NSM`, `EPR`,
  `Erosion_Accretion` (codes 0/1/2 — legend not documented; infer from the script),
  `Erosion_Risk` (1/2/3). Observed: 115,708 Low / 387 Medium / 88 High pixels; every
  non-zero EPR is quantised by pixels (smallest |EPR| = 0.857 = 30/35); a few extreme
  values (NSM down to −2,871 m, EPR down to −82 m/yr); shoreline edge-pixel counts per
  year ≈ 2.6k (1990), 2.7k (2000), 2.4k (2010), 7.4k (2020), 20.3k (2025) — the 2025 mask is
  far noisier/more fragmented, so the years are probably **not comparable**.

**(B) Vector shoreline lines (`Shoreline Changes.shp`, 20 lines, 1990–2025)**
- Extent (≈121.563–121.755 E) is **larger than the rasters**, so these lines were not
  derived from the GEE rasters. Origin (hand digitizing? which imagery? which dates?) is
  UNKNOWN. The thesis says "digitized". 3–6 fragments per year, an empty `id` column, one
  feature whose year value is `"Hig"`, inconsistent total length per year (≈35 km in 1990,
  ≈57 km in 2010, ≈36 km in 2020), river-mouth loops. The QGIS project also contains a
  Google Satellite XYZ basemap, which shows current imagery only — it cannot by itself
  explain 1990–2010 lines.

**(C) Risk polygons (`Aparri Risk Ana.shp` = `Aparri_MultiTemporal_Erosion_Risk_1990_2025.shp`, 124 polygons)**
- Only **three distinct EPR values** (0.857143, 2.5864, 5.72642) vs 127 distinct values in the
  EPR raster — the polygon EPR is a class constant, not a measured rate. 48 polygons
  labelled "Med" carry 0.857 (< thesis cutoff). Labels inconsistent (`LOW`, `Med`, `Hig`,
  `High`). All EPR positive, contradicting "negative = erosion". `EPR Results.xlsx` = same
  attributes. Extent also larger than the rasters ⇒ origin unexplained.
- Thesis Fig. 4.2 (the risk map) comes from (C); Fig. 4.1 (five shorelines) from (B).
  They have no demonstrated link to each other, or to the GEE rasters in (A).

**Cross-checks and manuscript defects**
- A plain intersection of risk polygons with study-barangay polygons gives **no Bulala Sur**
  row; use nearest-join with a tolerance and report unmatched features.
- Thesis text says High risk is in Bulala Sur/Norte and Low in Linao; the legacy overlay
  puts ~13 ha of "High" in Linao. Verify per barangay.
- Manuscript: Table numbers duplicated (4.1 and 4.2 each appear twice); "Figure 4.2" cited
  where 4.1 is meant; broken sentence "analyzed using the to determine the average";
  garbled "shoreliSelectin e rates"; threshold source differs between Table 3.1 and Table 4.1;
  "GIS ... visualize future shoreline projections" promised but never done; "coastal erosion
  factors" in the conceptual framework with no results section; Ho1/Ha1 stated but no test;
  Table 4.2 empty; Chapter V is the blank template; the methodology never mentions
  Landsat, NDWI, Google Earth Engine, image dates or resolution.

## 5. Tech stack & conventions

- Python ≥ 3.11. Core: `geopandas`, `shapely>=2`, `pyproj`, `pandas`, `numpy`, `scipy`,
  `statsmodels`, `matplotlib`, `openpyxl`, `pyyaml`, `rasterio` (required: the .tif files exist), `scikit-image` (sub-pixel contours),
  `python-docx` (read/draft only), `pytest`. Optional: `contextily`, `pingouin` / `scikit-posthocs`, `earthengine-api` or `pystac-client` + `planetary-computer` (only if the students approve re-deriving shorelines from Landsat; ask before authenticating anything).
- Outputs must open cleanly in **QGIS 3.x**: GeoPackage (`.gpkg`) preferred, plus a
  `.qml` style file for the risk layer.
- Code style: type hints, docstrings that explain *why*, small pure functions, no
  hidden globals, deterministic output (fixed seeds, sorted IDs).
- Every script reads `config/config.yaml`; every run writes a `outputs/reports/run_<timestamp>.json`
  with parameters, input hashes (sha256), counts and warnings.
- Commit after each phase: `phase-N: <summary>`. Update `docs/CHANGELOG.md` and
  `docs/decisions.md` (decision, options considered, who decided, date).
- Maps: consistent with the thesis look (green Low / orange Medium / red High, legend,
  2.5 km scale bar, north arrow, title like the original Figs. 4.1 and 4.2), 300 dpi.
- Plain English in all docs. The reader is a civil-engineering student, not a GIS
  specialist: define terms (EPR, LRR, NSM, transect, baseline) on first use.

## 6. Working agreement

- Start every phase in **plan mode**: show the plan, wait for approval.
- Run `make test` before declaring a phase done. Show the evidence (numbers, plots), not just "done".
- Report uncertainty honestly. "I could not verify X because Y" is a good answer.
- If a result looks too clean or too surprising, investigate before reporting it.
- Keep a running list in `docs/decisions.md` titled **Open questions for the students**.
