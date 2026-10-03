# Draft — Chapter III, "Data and GIS Procedure"  [DRAFT – FOR STUDENT REVIEW]

*This text describes only what the reproducible pipeline in this repository did. Words in **[STUDENTS: …]** are facts that the files do not contain; fill them in from your own records or delete the sentence. Tense: past (the work has been done). Replace the sentence in the current manuscript that says the shorelines "will be digitized and overlaid" (Risk Assessment Method, p. 39).*

## 3.x Shoreline data

Shoreline positions for the years 1990, 2000, 2010, 2020 and 2025 were represented as polylines in a Geographic Information System (QGIS; Python/GeoPandas for the computations). **[STUDENTS: choose ONE of the two paragraphs below and delete the other.]**

**Option A — if the lines came from Landsat via Google Earth Engine:** The shorelines were derived from Landsat Collection 2 Level-2 surface-reflectance imagery (Landsat **[4/5/7/8/9 — list the sensors you used for each year]**, 30 m pixels) processed in Google Earth Engine. For each year a median composite of the cloud-masked scenes was computed **[STUDENTS: state the date range, number of scenes and acquisition dates per year]**, the Normalized Difference Water Index, NDWI = (Green − NIR)/(Green + NIR), was calculated and pixels with NDWI > 0 were classed as water. The land–water boundary was taken as the shoreline **[STUDENTS: say how the boundary was converted to lines and by whom]**.

**Option B — if the lines were digitized by hand:** The shorelines were digitized on-screen in QGIS from **[STUDENTS: imagery source, date and resolution for each year]** following the **[STUDENTS: shoreline indicator, e.g. instantaneous waterline / wet-dry line / vegetation line]**, by **[STUDENTS: who digitized, at what map scale]**.

Whichever option applies, state the **shoreline indicator** and note that tide level and season at the time of each image were **[not recorded / recorded as …]**.

## 3.y Preparation of the shoreline lines

All data were transformed to WGS 84 / UTM zone 51N (EPSG:32651) so that distances and areas are in metres. The digitized lines arrived as 19 loose fragments for the five years (3–6 per year). A scripted, logged procedure (`src/aparri/clean.py`) (i) removed stretches that had been digitized twice within a year (2010: 18.3 km), (ii) joined fragment end points closer than 5 m, (iii) removed self-crossing loops shorter than 50 m, and (iv) set aside one feature whose year attribute was not a number, which was not analyzed. Every action is recorded in a cleaning log. The cleaned lines were then divided into the **open, sea-facing coast** and the **river banks** of the Cagayan River mouth with a fixed geometric rule (distance of 350 m from the outer envelope of all shorelines). Only the open coast (about 20.5 km per year) was classified, because river-bank shorelines respond to river discharge and bar migration rather than to wave action alone.

## 3.z Baseline, transects and shoreline change rates

A baseline was constructed on land behind all shorelines by smoothing the 1990 open-coast shoreline with a 200 m moving average and shifting it landward by the largest landward excursion of any year plus 150 m. The side of the line that is land was decided by testing points on both sides against the municipal barangay polygons. Transects were generated perpendicular to the baseline every 50 m, giving 415 transects of which 373 were valid (both 1990 and 2025 shorelines crossed, no transect crossing another). Following the Digital Shoreline Analysis System approach (Thieler et al., 2009 **[VERIFY CITATION]**) the distance from the baseline to each year's shoreline was measured along every transect and the following were computed:

- **Net Shoreline Movement (NSM)** = distance₂₀₂₅ − distance₁₉₉₀ (m);
- **End Point Rate (EPR)** = NSM ÷ T, with T = 35 years **[STUDENTS: replace by the exact time between the two image dates if known]**;
- **Linear Regression Rate (LRR)**, the slope of the least-squares line through all available years (reported alongside EPR; at least three dates required).

Negative values denote landward movement (erosion) and positive values seaward movement (accretion).

## 3.w Uncertainty

The imagery has a nominal pixel size of 30 m. If each shoreline is uncertain by one pixel, the uncertainty of a 35-year end-point rate is √2 × 30 ÷ 35 = 1.21 m/yr. **[STUDENTS: replace with measured values for georeferencing, digitizing/extraction and tidal error if you obtain them — config.uncertainty_m.]** Because no measured positional error was available, the ±30 m figure was used only as a what-if to label the confidence of each class, and the classification itself was not adjusted for uncertainty.

## 3.v Classification and barangay summary

Each transect was assigned to a class from its erosion rate (the magnitude of a negative EPR): Low, < 2 m/yr; Medium, 2–5 m/yr (inclusive); High, > 5 m/yr (Table 3.1). Transects with positive EPR (accretion) were counted as Low and flagged as accreting. Transects that cross neighbouring transects (near the river mouth) were left unclassified. The 2025 shoreline was divided into segments at the mid-points between transects; each segment took the class of its transect. Segments were attributed to the nearest study barangay within 500 m. For each barangay the mean, minimum and maximum EPR and the length (km) of shoreline in each class were computed; areas in hectares were obtained as length × a 100 m coastal strip **[STUDENTS: justify the strip width or report kilometres only]**.

## 3.u Checks

The procedure was verified with synthetic shorelines of known change (a straight coast retreating 2.000 m/yr and advancing 1.500 m/yr, concentric circular arcs, missing years, loops, mirrored land/sea orientation) in an automated test suite. A second shoreline data set traced from the Earth Engine edge-pixel masks was measured on the same transects: for 253 transects the two sets gave EPR correlation r = 0.89, an RMSE of 0.69 m/yr and the same class for 92 % of transects. The sensitivity of the class shares to transect spacing, smoothing, multi-hit rule and baseline offset was ≤ 0.5 percentage points, whereas shifting both class limits by ±0.5 m/yr changed the Medium share from 27 % to 48 % / 19 % (`docs/05_sensitivity_validation.md`).

## 3.t Limitations to state in the text

1. Classification uses erosion rate only; exposure and vulnerability were not assessed (as already stated on p. 41).
2. Positional error and acquisition dates/tides were not available; a 30 m pixel is coarse relative to the 2 m/yr class limit.
3. The river-mouth shorelines were not classified.
4. No field verification has yet been carried out (template: `docs/field_validation_form.md`).
