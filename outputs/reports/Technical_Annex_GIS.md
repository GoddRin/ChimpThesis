# Technical Annex — GIS analysis of shoreline change, Aparri, Cagayan  [DRAFT – FOR STUDENT REVIEW]

*Generated 2026-10-03 by `make annex` from the repository. Purpose: let a reader repeat and check the GIS work.*

## 1. How to repeat the analysis
```
make setup        # creates .venv and installs the pinned requirements
make test         # 85 automated tests
make all          # audit, audit-gee, clean-lines, raster-lines, transects, risk, tables, maps, sensitivity, web
make priority qgis drafts annex survey
```
Every step reads `config/config.yaml` (all parameters, with comments) and writes `outputs/reports/run_<step>_<time>.json` (parameters, input checksums, software versions, counts, warnings).

## 2. Input data (read-only, checksums)
| file | sha256 (first 16) |
|---|---|
| ./Aparri/Aparri Barangays.shp | d480fdbfcbc965c5 |
| ./Aparri/Aparri_Brgy_Study.shp | f0ebd12de1e4b7f5 |
| ./gee_outputs/Aparri_Barangay_Erosion_Statistics_1990_2025.csv | c56dbeaf6ddc68be |
| ./gee_outputs/Aparri_EPR_1990_2025.tif | 75fd1e8a946019f3 |
| ./gee_outputs/Aparri_Shoreline_2025.tif | a7975099905dd5ee |
| ./gee_outputs/Code.docx | 132f58cc361a7e93 |
| ./risk_zip/Aparri_MultiTemporal_Erosion_Risk_1990_2025.shp | ea89db6ed9c50cfc |
| ./shoreline_changes/Shoreline Changes.shp | b1c498b74fd9bba9 |

All 65 files in `data/raw/` are listed with SHA-256 in `data/raw/MANIFEST.sha256`; the test suite fails if any raw file changes.

## 3. Software
| package | version |
|---|---|
| python | 3.11.15 |
| geopandas | 1.2.0 |
| shapely | 2.1.2 |
| pyproj | 3.7.2 |
| pandas | 3.0.6 |
| numpy | 2.4.6 |
| scipy | 1.17.1 |
| statsmodels | 0.15.0 |
| rasterio | 1.4.4 |
| scikit-image | 0.26.0 |
| matplotlib | 3.11.2 |
| openpyxl | 3.1.5 |
| python-docx | 1.2.0 |
| pyyaml | 6.0.3 |

## 4. Parameters used
| parameter | value |
|---|---|
| Working CRS | EPSG:32651 (WGS 84 / UTM 51N, metres) |
| Years | [1990, 2000, 2010, 2020, 2025] |
| Shoreline set (primary) | vector_clean |
| Baseline | 1990 open-coast shoreline, smoothed 200 m, offset landward by max excursion + 150 m |
| Transects | every 50 m, 600 m seaward / 600 m landward, multi-hit rule: nearest |
| Open-coast rule | within 350 m of the concave-hull outline (ratio 0.1); estuarine banks excluded |
| Cleaning | snap 5 m; loops < 50 m removed; duplicate stretches (80% within 60 m) removed |
| Class limits | Low < 2.0, Medium 2.0–5.0 (inclusive), High > 5.0 m/yr; accretion -> Low (tagged) |
| Hectare strip | 100 m |
| Barangay join tolerance | 500 m |
| Acquisition dates | NOT PROVIDED (EPR over 35 calendar years) |
| Positional uncertainty | NOT PROVIDED (what-if ±30 m only for the confidence label) |

## 5. Results
**Table 4.2** (kilometres of shoreline are in the extended table):

| Barangay | Mean EPR (m/year) | Minimum EPR (m/year) | Maximum EPR (m/year) | Low Risk (ha) | Medium Risk (ha) | High Risk (ha) |
|---|---|---|---|---|---|---|
| Dodan | -1.93 | -2.21 | -1.76 | 12.50 | 7.49 | 0.00 |
| Maura | -1.39 | -2.07 | -0.62 | 56.97 | 1.50 | 0.00 |
| Bulala Norte | -3.35 | -3.49 | -3.19 | 0.00 | 13.46 | 0.00 |
| San Antonio | -0.91 | -1.41 | -0.53 | 6.51 | 0.00 | 0.00 |
| Linao | -0.70 | -3.21 | 5.30 | 12.80 | 13.09 | 0.00 |
| Paddaya | -1.41 | -1.76 | -1.36 | 46.50 | 0.00 | 0.00 |
| Punta | 0.19 | -0.05 | 0.53 | 3.02 | 0.00 | 0.00 |
| Bulala Sur | -2.74 | -3.16 | -2.32 | 0.00 | 14.35 | 0.00 |

| Barangay | Low risk (km) | Medium risk (km) | High risk (km) | Unclassified (km) | n transects | n valid | n flagged | % eroding | % classes that may flip |
|---|---|---|---|---|---|---|---|---|---|
| Dodan | 1.25 | 0.75 | 0.00 | 0.00 | 40 | 40 | 0 | 100.00 | 100.00 |
| Maura | 5.70 | 0.15 | 0.00 | 0.00 | 117 | 117 | 0 | 100.00 | 94.02 |
| Bulala Norte | 0.00 | 1.35 | 0.00 | 0.00 | 27 | 27 | 0 | 100.00 | 3.70 |
| San Antonio | 0.65 | 0.00 | 0.00 | 0.00 | 13 | 13 | 0 | 100.00 | 53.85 |
| Linao | 1.28 | 1.31 | 0.00 | 0.65 | 77 | 48 | 34 | 62.50 | 58.33 |
| Paddaya | 4.65 | 0.00 | 0.00 | 0.00 | 93 | 93 | 0 | 100.00 | 100.00 |
| Punta | 0.30 | 0.00 | 0.00 | 0.75 | 19 | 6 | 13 | 33.33 | 0.00 |
| Bulala Sur | 0.00 | 1.44 | 0.00 | 0.00 | 29 | 29 | 1 | 100.00 | 100.00 |

Figures: `outputs/maps/Fig_4_1_v2_multitemporal_shorelines.png`, `Fig_4_2_v2_erosion_risk_map.png`, `Fig_4_3_epr_profile_along_coast.png`, `Fig_legacy_vs_rebuilt.png`.

Field-inspection priority (erosion information only; weights in config):

| Barangay | mean_erosion_rate_m_yr | km_medium_or_high | share_class_not_sensitive | priority_score | rank |
|---|---|---|---|---|---|
| Bulala Norte | 3.35 | 1.35 | 0.96 | 0.97 | 1 |
| Bulala Sur | 2.74 | 1.44 | 0.00 | 0.91 | 2 |
| Linao | 1.65 | 1.31 | 0.42 | 0.70 | 3 |
| Dodan | 1.93 | 0.75 | 0.00 | 0.55 | 4 |
| Maura | 1.39 | 0.15 | 0.06 | 0.26 | 5 |
| Paddaya | 1.41 | 0.00 | 0.00 | 0.21 | 6 |
| San Antonio | 0.91 | 0.00 | 0.46 | 0.13 | 7 |
| Punta | 0.01 | 0.00 | 1.00 | 0.00 | 8 |

## 6. Quality assurance
* Automated tests: 85 automated tests — synthetic coasts of known change (straight 2.000 m/yr retreat, 1.500 m/yr advance, circular arcs, missing years, loops, mirrored orientation), cleaning rules, class boundaries (exactly 2.0 and 5.0 are Medium), survey statistics against hand computations, web-map smoke test.
* Sensitivity (share of valid transects, %):

| scenario | description | pct_Low | pct_Medium | pct_High |
|---|---|---|---|---|
| base | base run | 73.2 | 26.8 | 0.0 |
| spacing_25 | transect spacing 25 m | 73.7 | 26.3 | 0.0 |
| spacing_100 | transect spacing 100 m | 73.3 | 26.7 | 0.0 |
| smooth_100 | baseline smoothing 100 m | 73.1 | 26.9 | 0.0 |
| smooth_400 | baseline smoothing 400 m | 72.8 | 26.9 | 0.3 |
| multihit_farthest | multi-hit rule: farthest crossing | 73.2 | 26.8 | 0.0 |
| with_estuarine | include estuarine banks | 73.9 | 21.3 | 4.8 |
| thr_-0.5 | thresholds shifted -0.5 m/yr | 52.0 | 48.0 | 0.0 |
| thr_+0.5 | thresholds shifted +0.5 m/yr | 81.2 | 18.8 | 0.0 |
| classify_by_LRR | classify with LRR instead of EPR | 81.8 | 18.2 | 0.0 |
| offset_landward_300 | baseline offset 300 m instead of 150 m | 72.9 | 27.1 | 0.0 |

* Stability of the barangay classes across runs:

| barangay | base_dominant | base_worst | runs | pct_runs_same_dominant | pct_runs_same_worst | robust | classes_seen |
|---|---|---|---|---|---|---|---|
| Dodan | Low | Medium | 10 | 90 | 80 | False | Low,Medium |
| Maura | Low | Low | 10 | 100 | 90 | True | Low |
| Bulala Norte | Medium | Medium | 10 | 100 | 100 | True | Medium |
| San Antonio | Low | Low | 10 | 100 | 100 | True | Low |
| Linao | Medium | Medium | 10 | 70 | 90 | False | Low,Medium |
| Paddaya | Low | Low | 10 | 100 | 90 | True | Low |
| Punta | Low | Low | 10 | 90 | 90 | True | Low,no data |
| Bulala Sur | Medium | Medium | 10 | 100 | 100 | True | Medium |

## 7. Findings about the legacy outputs (summary; full text in `docs/01_data_audit.md`, `docs/01b_gee_audit.md`)
The supplied risk polygons, Earth Engine barangay statistics and raster change layers could not be reproduced or were not valid for the thesis purpose; they were not used in any result.

## 8. Limitations
See `docs/02_method.md` §7: erosion rate only; 30 m imagery with no recorded dates, tide or measured error; river mouth excluded; no field verification yet.

## 9. File index
`config/` parameters · `src/aparri/` code · `data/raw/` inputs (read-only) · `data/interim/` cleaned shorelines + review package · `data/processed/` transects and segments · `outputs/tables|maps|layers|web|field_validation|reports/` results · `docs/` audit, method, drafts, Q&A.
