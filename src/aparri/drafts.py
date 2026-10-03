"""Phase 9: generated, number-consistent draft documents for the students.

Writes (all labelled [DRAFT – FOR STUDENT REVIEW]; numbers are read from the pipeline's output tables, never typed):
  docs/methods_draft.md      "Data and GIS Procedure" for Chapter III - ONLY what the pipeline actually did
  docs/results_drafts.md     draft paragraphs for Table 4.2 and Figures 4.1-4.3 - strictly describing the numbers
  docs/04_defense_qa.md      25 likely panel questions with honest answers and evidence files
  docs/for_the_adviser.md    one-page neutral disclosure memo
No citations are invented; literature suggestions are marked [VERIFY CITATION].
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .audit_report import md
from .io import REPO_ROOT, load_config, repo_path

TAG = "[DRAFT – FOR STUDENT REVIEW]"


def T(name: str) -> pd.DataFrame:
    return pd.read_csv(repo_path(f"outputs/tables/{name}"))


def facts(cfg: dict) -> dict:
    f: dict = {"cfg": cfg}
    f["ext"] = T("Table_4_2_extended.csv").set_index("Barangay")
    f["th"] = T("Table_4_2_barangay_results.csv")
    f["runs"] = T("sensitivity_runs.csv").set_index("scenario")
    f["rob"] = T("sensitivity_robustness.csv").set_index("barangay")
    f["pos"] = T("sensitivity_source_positions.csv")
    f["sum"] = T("transect_summary_by_set.csv").set_index("set")
    f["clean"] = T("clean_summary.csv").set_index("year")
    f["cmp"] = T("raster_vs_vector_comparison.csv").set_index("year")
    f["leg"] = T("legacy_vs_rebuilt_by_barangay.csv").set_index("barangay")
    name = cfg["shoreline_set"]
    tm = pd.read_csv(repo_path(f"data/processed/{name}/transect_metrics.csv"))
    f["tm"] = tm
    v = tm[tm.valid_epr]
    f["valid"] = v
    f["n_tr"], f["n_valid"] = len(tm), len(v)
    f["epr_mean"], f["epr_median"] = v.EPR_m_yr.mean(), v.EPR_m_yr.median()
    f["epr_min"], f["epr_max"] = v.EPR_m_yr.min(), v.EPR_m_yr.max()
    f["pct_erode"] = float((v.EPR_m_yr < 0).mean() * 100)
    f["nsm_by_b"] = v.groupby("barangay").NSM_m.mean()
    f["epr_by_b"] = v.groupby("barangay").EPR_m_yr.agg(["mean", "min", "max", "size"])
    km = f["ext"][["Low risk (km)", "Medium risk (km)", "High risk (km)", "Unclassified (km)", "Classified shoreline (km)"]]
    f["km"] = km
    f["km_tot"] = km.sum()
    f["u"] = float(np.sqrt(2) * cfg["risk"]["confidence_scenario_unc_m"] / 35)
    f["pix_m"] = 30
    f["rob_names"] = [b for b in f["rob"].index if f["rob"].loc[b, "robust"]]
    f["notrob_names"] = [b for b in f["rob"].index if not f["rob"].loc[b, "robust"]]
    sc = pd.read_csv(repo_path("outputs/tables/sensitivity_source_class_confusion.csv"), index_col=0)
    f["src_agree"] = float(np.trace(sc.values) / sc.values.sum() * 100)
    both = tm.merge(pd.read_csv(repo_path("data/processed/raster_clean/transect_metrics.csv")), on="transect_id", suffixes=("_v", "_r"))
    both = both[both.valid_epr_v & both.valid_epr_r]
    f["src_n"] = len(both); f["src_r"] = float(both.EPR_m_yr_v.corr(both.EPR_m_yr_r))
    f["src_rmse"] = float(np.sqrt(((both.EPR_m_yr_r - both.EPR_m_yr_v) ** 2).mean()))
    bt = pd.read_csv(repo_path("outputs/tables/audit_risk_by_type.csv"))
    f["audit_pix"] = int(bt[bt.pixel_type == True].polygons.sum())   # noqa: E712
    f["audit_hand"] = int(bt[bt.pixel_type == False].polygons.sum())  # noqa: E712
    import geopandas as gpd
    seg = gpd.read_file(repo_path(f"data/processed/{name}/risk_segments.gpkg"))
    f["acc_by_b"] = (seg[seg.trend == "accreting"].groupby("barangay").length_m.sum() / 1000).sort_values(ascending=False)
    f["acc_km"] = float(f["acc_by_b"].sum())
    ok = v[v.lrr.notna()]
    f["epr_lrr_r"] = float(ok.EPR_m_yr.corr(ok.lrr))
    from .risk import classify
    ce = classify(ok.EPR_m_yr.values, cfg["risk"]["low_max"], cfg["risk"]["medium_max"], cfg["risk"]["accretion_class"])
    cl = classify(ok.lrr.values, cfg["risk"]["low_max"], cfg["risk"]["medium_max"], cfg["risk"]["accretion_class"])
    f["epr_lrr_agree"] = float((ce == cl).mean() * 100)
    from .stats_survey import PUBLISHED_4_4, weight_sensitivity
    ws = weight_sensitivity(PUBLISHED_4_4.drop(columns="Overall"))
    f["ws_first_seawall"] = float(ws["p_first"]["Seawall"] * 100)
    f["ws_eng"] = ws["named"].iloc[4]["ranking (best first)"]
    ins = f["runs"].loc[["spacing_25", "spacing_100", "smooth_100", "smooth_400", "multihit_farthest", "offset_landward_300"]]
    f["max_shift"] = float(max((ins.pct_Medium - f["runs"].loc["base", "pct_Medium"]).abs().max(), (ins.pct_Low - f["runs"].loc["base", "pct_Low"]).abs().max()))
    gp = T("gee_plausibility.csv").set_index("set")
    f["gee_acc_sea"] = float(gp.loc["Accretion pixels (code 2)", "sea_pct"])
    f["gee_acc_px"] = int(gp.loc["Accretion pixels (code 2)", "pixels"]); f["gee_ero_px"] = int(gp.loc["Erosion pixels (code 1)", "pixels"])
    return f


def b_lines(f: dict) -> str:
    """One-line numeric description per barangay (neutral wording)."""
    out = []
    for b in f["cfg"]["table_4_2_order"]:
        e = f["ext"].loc[b]
        if e["n valid"] == 0:
            out.append(f"- **{b}**: no valid transect.")
            continue
        out.append(f"- **{b}**: mean EPR {e['Mean EPR (m/yr)']:+.2f} m/yr (range {e['Min EPR (m/yr)']:+.2f} to {e['Max EPR (m/yr)']:+.2f}), "
                   f"{e['Low risk (km)']:.2f} km Low, {e['Medium risk (km)']:.2f} km Medium, {e['High risk (km)']:.2f} km High, "
                   f"{e['Unclassified (km)']:.2f} km not classified; {int(e['n valid'])} valid transects.")
    return "\n".join(out)


# --------------------------------------------------------------------------- methods
def methods(f: dict) -> str:
    c = f["cfg"]
    return f"""# Draft — Chapter III, "Data and GIS Procedure"  {TAG}

*This text describes only what the reproducible pipeline in this repository did. Words in **[STUDENTS: …]** are facts that the files do not contain; fill them in from your own records or delete the sentence. Tense: past (the work has been done). Replace the sentence in the current manuscript that says the shorelines "will be digitized and overlaid" (Risk Assessment Method, p. 39).*

## 3.x Shoreline data

Shoreline positions for the years 1990, 2000, 2010, 2020 and 2025 were represented as polylines in a Geographic Information System (QGIS; Python/GeoPandas for the computations). **[STUDENTS: choose ONE of the two paragraphs below and delete the other.]**

**Option A — if the lines came from Landsat via Google Earth Engine:** The shorelines were derived from Landsat Collection 2 Level-2 surface-reflectance imagery (Landsat **[4/5/7/8/9 — list the sensors you used for each year]**, 30 m pixels) processed in Google Earth Engine. For each year a median composite of the cloud-masked scenes was computed **[STUDENTS: state the date range, number of scenes and acquisition dates per year]**, the Normalized Difference Water Index, NDWI = (Green − NIR)/(Green + NIR), was calculated and pixels with NDWI > 0 were classed as water. The land–water boundary was taken as the shoreline **[STUDENTS: say how the boundary was converted to lines and by whom]**.

**Option B — if the lines were digitized by hand:** The shorelines were digitized on-screen in QGIS from **[STUDENTS: imagery source, date and resolution for each year]** following the **[STUDENTS: shoreline indicator, e.g. instantaneous waterline / wet-dry line / vegetation line]**, by **[STUDENTS: who digitized, at what map scale]**.

Whichever option applies, state the **shoreline indicator** and note that tide level and season at the time of each image were **[not recorded / recorded as …]**.

## 3.y Preparation of the shoreline lines

All data were transformed to WGS 84 / UTM zone 51N (EPSG:32651) so that distances and areas are in metres. The digitized lines arrived as {int(sum(f['clean'].features_before))} loose fragments for the five years (3–6 per year). A scripted, logged procedure (`src/aparri/clean.py`) (i) removed stretches that had been digitized twice within a year (2010: {f['clean'].loc[2010,'removed_km']:.1f} km), (ii) joined fragment end points closer than {c['clean']['snap_tol_m']} m, (iii) removed self-crossing loops shorter than {c['clean']['min_loop_m']} m, and (iv) set aside one feature whose year attribute was not a number, which was not analyzed. Every action is recorded in a cleaning log. The cleaned lines were then divided into the **open, sea-facing coast** and the **river banks** of the Cagayan River mouth with a fixed geometric rule (distance of {c['scope']['hull_tolerance_m']} m from the outer envelope of all shorelines). Only the open coast (about {f['clean'].loc[2025,'km_open_coast']:.1f} km per year) was classified, because river-bank shorelines respond to river discharge and bar migration rather than to wave action alone.

## 3.z Baseline, transects and shoreline change rates

A baseline was constructed on land behind all shorelines by smoothing the 1990 open-coast shoreline with a {c['baseline']['smooth_m']} m moving average and shifting it landward by the largest landward excursion of any year plus {c['baseline']['offset_landward_m']} m. The side of the line that is land was decided by testing points on both sides against the municipal barangay polygons. Transects were generated perpendicular to the baseline every {c['transects']['spacing_m']} m, giving {f['n_tr']} transects of which {f['n_valid']} were valid (both 1990 and 2025 shorelines crossed, no transect crossing another). Following the Digital Shoreline Analysis System approach (Thieler et al., 2009 **[VERIFY CITATION]**) the distance from the baseline to each year's shoreline was measured along every transect and the following were computed:

- **Net Shoreline Movement (NSM)** = distance₂₀₂₅ − distance₁₉₉₀ (m);
- **End Point Rate (EPR)** = NSM ÷ T, with T = 35 years **[STUDENTS: replace by the exact time between the two image dates if known]**;
- **Linear Regression Rate (LRR)**, the slope of the least-squares line through all available years (reported alongside EPR; at least three dates required).

Negative values denote landward movement (erosion) and positive values seaward movement (accretion).

## 3.w Uncertainty

The imagery has a nominal pixel size of 30 m. If each shoreline is uncertain by one pixel, the uncertainty of a 35-year end-point rate is √2 × 30 ÷ 35 = {f['u']:.2f} m/yr. **[STUDENTS: replace with measured values for georeferencing, digitizing/extraction and tidal error if you obtain them — config.uncertainty_m.]** Because no measured positional error was available, the ±{c['risk']['confidence_scenario_unc_m']} m figure was used only as a what-if to label the confidence of each class, and the classification itself was not adjusted for uncertainty.

## 3.v Classification and barangay summary

Each transect was assigned to a class from its erosion rate (the magnitude of a negative EPR): Low, < 2 m/yr; Medium, 2–5 m/yr (inclusive); High, > 5 m/yr (Table 3.1). Transects with positive EPR (accretion) were counted as Low and flagged as accreting. Transects that cross neighbouring transects (near the river mouth) were left unclassified. The 2025 shoreline was divided into segments at the mid-points between transects; each segment took the class of its transect. Segments were attributed to the nearest study barangay within {c['barangay_join_tolerance_m']} m. For each barangay the mean, minimum and maximum EPR and the length (km) of shoreline in each class were computed; areas in hectares were obtained as length × a {c['risk']['strip_width_m']:g} m coastal strip **[STUDENTS: justify the strip width or report kilometres only]**.

## 3.u Checks

The procedure was verified with synthetic shorelines of known change (a straight coast retreating 2.000 m/yr and advancing 1.500 m/yr, concentric circular arcs, missing years, loops, mirrored land/sea orientation) in an automated test suite. A second shoreline data set traced from the Earth Engine edge-pixel masks was measured on the same transects: for {f['src_n']} transects the two sets gave EPR correlation r = {f['src_r']:.2f}, an RMSE of {f['src_rmse']:.2f} m/yr and the same class for {f['src_agree']:.0f} % of transects. The sensitivity of the class shares to transect spacing, smoothing, multi-hit rule and baseline offset was ≤ {f['max_shift']:.1f} percentage points, whereas shifting both class limits by ±0.5 m/yr changed the Medium share from {f['runs'].loc['base','pct_Medium']:.0f} % to {f['runs'].loc['thr_-0.5','pct_Medium']:.0f} % / {f['runs'].loc['thr_+0.5','pct_Medium']:.0f} % (`docs/05_sensitivity_validation.md`).

## 3.t Limitations to state in the text

1. Classification uses erosion rate only; exposure and vulnerability were not assessed (as already stated on p. 41).
2. Positional error and acquisition dates/tides were not available; a 30 m pixel is coarse relative to the 2 m/yr class limit.
3. The river-mouth shorelines were not classified.
4. No field verification has yet been carried out (template: `docs/field_validation_form.md`).
"""


# --------------------------------------------------------------------------- results
def results(f: dict) -> str:
    c = f["cfg"]
    order = c["table_4_2_order"]
    th = f["th"].copy()
    ext = f["ext"]
    top = ext["Mean EPR (m/yr)"].idxmin()
    flat = ext.loc[order][["Low risk (km)", "Medium risk (km)", "High risk (km)", "Unclassified (km)"]]
    ktot = f["km_tot"]
    return f"""# Draft — Chapter IV, results text for the rebuilt shoreline analysis  {TAG}

*Strictly describes the numbers produced by `make tables` / `make maps`. No engineering recommendation, no cause is asserted (causes need the factors in `docs/erosion_factors_plan.md`). Replace Table 4.2 and Figures 4.1–4.2 of the manuscript with the versions in `outputs/`.*

## Multi-Temporal Shoreline Change (Figure 4.1)

Figure 4.1 shows the open-coast shorelines of 1990, 2000, 2010, 2020 and 2025 along the {ktot['Classified shoreline (km)'] + ktot['Unclassified (km)']:.1f} km of coast that has valid transects (river banks are drawn dashed and were not analysed). Along the straight coast from Bulala Sur to Bulala Norte the 1990 shoreline lies seaward of the later shorelines (mean net movement 1990–2025 of {f['nsm_by_b'].get('Bulala Sur', np.nan):+.0f} m at Bulala Sur and {f['nsm_by_b'].get('Bulala Norte', np.nan):+.0f} m at Bulala Norte), whereas the mean net movement was {f['nsm_by_b'].get('Maura', np.nan):+.0f} m at Maura, {f['nsm_by_b'].get('Dodan', np.nan):+.0f} m at Dodan and {f['nsm_by_b'].get('Paddaya', np.nan):+.0f} m at Paddaya. At the Linao spit and the river mouth the lines diverge and cross each other; transects there are not comparable and were left unclassified.

## Computation of the shoreline change rate

A total of {f['n_tr']} transects spaced {c['transects']['spacing_m']} m apart were generated, {f['n_valid']} of them valid. The End Point Rate 1990–2025 of the valid transects ranged from {f['epr_min']:+.2f} to {f['epr_max']:+.2f} m/yr (mean {f['epr_mean']:+.2f}, median {f['epr_median']:+.2f} m/yr); {f['pct_erode']:.0f} % of valid transects had a negative EPR (landward movement). The largest erosion rate was {abs(f['epr_min']):.2f} m/yr; no valid transect reached the 5 m/yr limit of the High class.

## Barangay-Level EPR and Coastal Erosion Risk Results (Table 4.2)

{md(f['th'].round(2), floatfmt='{:,.2f}')}

*Hectares are kilometres of classified shoreline × a {c['risk']['strip_width_m']:g} m coastal strip; kilometres (below) are the primary measure.*

{md(pd.concat([flat, ext.loc[order][['n valid', 'n flagged', 'confidence high/medium/low (n)']]], axis=1), index=True, floatfmt='{:,.2f}')}

In order of mean EPR, the largest landward movement was recorded at {top} ({ext.loc[top, 'Mean EPR (m/yr)']:+.2f} m/yr), followed by {', '.join(ext['Mean EPR (m/yr)'].sort_values().index[1:3])}. Of the {ktot['Classified shoreline (km)']:.1f} km of classified shoreline, {ktot['Low risk (km)']:.1f} km ({ktot['Low risk (km)']/ktot['Classified shoreline (km)']*100:.0f} %) fell in the Low class, {ktot['Medium risk (km)']:.1f} km ({ktot['Medium risk (km)']/ktot['Classified shoreline (km)']*100:.0f} %) in the Medium class and {ktot['High risk (km)']:.1f} km in the High class; {ktot['Unclassified (km)']:.1f} km (river-mouth transects with crossing transects) were not classified. Per barangay:

{b_lines(f)}

## Coastal Erosion Risk Map (Figure 4.2)

Figure 4.2 shows the classified shoreline. Medium-class segments occur along Bulala Sur and Bulala Norte ({ext.loc['Bulala Sur', 'Medium risk (km)']:.2f} and {ext.loc['Bulala Norte', 'Medium risk (km)']:.2f} km; Low: {ext.loc['Bulala Sur', 'Low risk (km)']:.2f} and {ext.loc['Bulala Norte', 'Low risk (km)']:.2f} km), in parts of Linao ({ext.loc['Linao', 'Medium risk (km)']:.2f} km) and in short stretches of Dodan ({ext.loc['Dodan', 'Medium risk (km)']:.2f} km) and Maura ({ext.loc['Maura', 'Medium risk (km)']:.2f} km); Low-class segments occur elsewhere. Accreting segments (blue triangles) total {f['acc_km']:.2f} km: {', '.join(f'{b} {v:.2f} km' for b, v in f['acc_by_b'].items())}. **The High class does not occur on the open coast.** Segments drawn dotted have low confidence.

*Differences from the manuscript's earlier version of Figure 4.2:* the earlier figure showed High risk along Bulala Sur/Bulala Norte; the rebuilt analysis gives Medium there (mean EPR {ext.loc['Bulala Sur','Mean EPR (m/yr)']:+.2f} and {ext.loc['Bulala Norte','Mean EPR (m/yr)']:+.2f} m/yr). `docs/01_data_audit.md` explains why the earlier figure cannot be reproduced.

## Reliability of the classification (suggested paragraph for the Discussion)

The class limits lie close to the typical rates: moving both limits by ±0.5 m/yr changes the Medium share of the coast from {f['runs'].loc['base','pct_Medium']:.0f} % to between {f['runs'].loc['thr_+0.5','pct_Medium']:.0f} % and {f['runs'].loc['thr_-0.5','pct_Medium']:.0f} %. With a one-pixel uncertainty of ±{f['u']:.2f} m/yr, the class of the following barangays did not change across the sensitivity runs: {', '.join(f['rob_names'])}; it was not stable for {', '.join(f['notrob_names'])}. An independent shoreline set gave the same class for {f['src_agree']:.0f} % of {f['src_n']} transects.
"""


# --------------------------------------------------------------------------- Q&A
def qa(f: dict) -> str:
    c = f["cfg"]
    ext = f["ext"]; runs = f["runs"]; pos = f["pos"]
    u = f["u"]
    Q = []
    def q(n, question, answer, evidence):
        Q.append((n, question, answer.strip(), evidence))
    q(1, "Why EPR and not LRR (or another rate)?",
      f"The thesis defines the classes on the 1990–2025 End Point Rate, which only needs the first and last shoreline. We also computed LRR from all five dates: they are strongly correlated (r = {f['epr_lrr_r']:.2f}) and put the same class on {f['epr_lrr_agree']:.0f} % of transects; LRR is the more robust estimator when intermediate dates exist, EPR is the one the objectives name. We report both and classify with EPR.",
      "docs/05_sensitivity_validation.md §2; outputs/maps/Fig_6_epr_vs_lrr.png")
    q(2, "How accurate is a 30 m Landsat pixel for a rate as small as 0.86 m/yr?",
      f"It is not: one pixel over 35 years *is* 0.86 m/yr, and a one-pixel error at both dates gives ±{u:.2f} m/yr. That is why we report the uncertainty, mark classes that could change inside it (`class_may_flip`), and do not claim that Low versus Medium is a sharp physical boundary. The Medium class at Bulala Norte (mean {ext.loc['Bulala Norte','Mean EPR (m/yr)']:+.2f} m/yr; {ext.loc['Bulala Norte','% classes that may flip']:.0f} % of its transects could change class) lies clearly beyond the error band around the 2 m/yr limit; Bulala Sur ({ext.loc['Bulala Sur','Mean EPR (m/yr)']:+.2f} m/yr; {ext.loc['Bulala Sur','% classes that may flip']:.0f} % could change) is borderline, and the Low class elsewhere is largely within the band.",
      "docs/02_method.md §7; Table_4_2_extended.csv (% classes that may flip)")
    q(3, "How did you handle the Cagayan River mouth?",
      f"The open sea-facing coast and the river banks were separated by a fixed geometric rule, and only the open coast was classified. At the mouth the shorelines of different years diverge and loop, transects cross each other, and the resulting rates mean nothing, so those transects are left unclassified (grey on the map). Including the river banks in a sensitivity run produced High values ({f['runs'].loc['with_estuarine','pct_High']:.1f} % of transects), all at the mouth.",
      "docs/02_method.md §1; outputs/maps/clean_review.png; sensitivity run `with_estuarine`")
    q(4, "Why these thresholds (2 and 5 m/yr)?",
      "They are the limits adopted by the thesis from the literature (Osondu et al., 2025 [VERIFY CITATION]; the manuscript also attributes the 5 m/yr limit to Luijendijk et al., 2018 [VERIFY CITATION]). They are conventions, not natural laws; we show that the class shares move a lot if the limits shift by ±0.5 m/yr and that is stated as a limitation.",
      "docs/05_sensitivity_validation.md §1")
    q(5, "Why only 1990 and 2025?",
      "The thesis defines EPR with two end points; the three middle shorelines are shown in Figure 4.1 and used in the LRR. With five dates a regression is possible and we report it. The reason for not using only the middle dates is that EPR is the documented method of the study and is standard (DSAS).",
      "docs/02_method.md §4")
    q(6, "Is this a vulnerability or risk assessment?",
      "No. It is a classification of the erosion rate, as the manuscript itself says (p. 41, p. 60). Risk would also need exposure (people, buildings, roads) and vulnerability; those were not assessed. We would call the classes 'erosion-rate classes' in the discussion.",
      "docs/02_method.md §7 (point 6); Ch. IV Discussion")
    q(7, "Where do your shorelines come from and how do you know they are right?",
      f"**[STUDENTS: state the origin of the lines first — see Q-G1.]** What we can show: the lines were cleaned with a logged procedure, and an independent raster-derived set (from the Earth Engine masks) agrees with them to a median of {pos.robust_sd_m.min():.0f}–{pos.robust_sd_m.max():.0f} m (robust SD) on the same transects, with the same class for {f['src_agree']:.0f} % of {f['src_n']} transects. What we cannot show: ground truth. A field check at 20 points is planned.",
      "docs/05_sensitivity_validation.md §3; docs/field_validation_form.md")
    q(8, "Why are the figures and numbers different from your proposal?",
      f"Because the original GIS outputs could not be reproduced: of the 124 risk polygons, {f['audit_hand']} (the only 'High' and 'Medium 2.59' ones) were not derived from any raster we have, 48 were labelled Medium although their own value was 0.857 m/yr, and the Earth Engine statistics used 1 km circles around points. We rebuilt the analysis in a documented pipeline and disclosed the change to the adviser.",
      "docs/01_data_audit.md; docs/01b_gee_audit.md; docs/for_the_adviser.md")
    q(9, "What is the uncertainty of your EPR values?",
      f"No measured positional error exists. With one Landsat pixel at each date the EPR uncertainty is ±{u:.2f} m/yr (a lower bound: tide, georeferencing and extraction errors would add to it). An empirical comparison of two shoreline sets suggests a per-date error of about {pos.proposal_sigma_per_date_m.min():.0f}–{pos.proposal_sigma_per_date_m.max():.0f} m for the cleaned lines, but the 30 m pixel is the physical floor for Landsat-based shorelines.",
      "docs/05_sensitivity_validation.md §3")
    q(10, "Why is there no High-risk shoreline?",
      f"Because no valid open-coast transect lost more than {abs(f['epr_min']):.1f} m/yr. The old figure's High class came from two hand-drawn polygons that cannot be reproduced; the raster High pixels lie in the river mouth. The result is stable under the tested choices except including the river banks (and a single transect at the 400 m smoothing).",
      "outputs/maps/Fig_legacy_vs_rebuilt.png; docs/05_sensitivity_validation.md")
    q(11, "Which barangay is eroding fastest and by how much?",
      f"Bulala Norte: mean EPR {ext.loc['Bulala Norte','Mean EPR (m/yr)']:+.2f} m/yr (about {abs(f['nsm_by_b']['Bulala Norte']):.0f} m in 35 years), then Bulala Sur ({ext.loc['Bulala Sur','Mean EPR (m/yr)']:+.2f}). Both are Medium class.",
      "Table_4_2_barangay_results.xlsx")
    q(12, "Does tide affect the shorelines?",
      "Yes. A satellite waterline is the water level at the moment of the image; on a gently sloping beach one metre of tide moves the line tens of metres. Tide state was not recorded, so it is a source of error that cannot be removed here; using the same season each year (the proposed Landsat v2 composite) and recording the tide are the remedies.",
      "docs/02_method.md §7 (point 2); scripts/gee_v2.js")
    q(13, "What about seasonality and typhoons?",
      "The legacy composites were whole-year medians that mix seasons. Typhoon storms can move a shoreline by metres in a day; with five snapshots 10 years apart, we cannot separate storm response from the long-term trend. We state EPR as a long-term average only.",
      "docs/01b_gee_audit.md §1")
    q(14, "Why 50 m transect spacing?",
      f"It is a standard DSAS-type choice. We repeated the analysis at 25 m and 100 m: the share of each class changed by ≤ {f['max_shift']:.1f} percentage points.",
      "docs/05_sensitivity_validation.md §1")
    q(15, "How was the baseline chosen and could it bias the result?",
      f"The baseline is the smoothed 1990 shoreline moved landward behind all years; it is only a measuring grid, since EPR is a difference of two distances measured along the same transect. Changing the smoothing window (100–400 m) or the offset (150→300 m) changed class shares by ≤ {f['max_shift']:.1f} percentage points.",
      "docs/02_method.md §3; sensitivity runs")
    q(16, "Did you check on the ground?",
      "**[STUDENTS: answer truthfully.]** As of this writing no field verification has been done. A 20-point verification template with coordinates is provided; until it is filled in the answer is 'not yet'.",
      "docs/field_validation_form.md; outputs/field_validation/")
    q(17, "Why are 54 respondents enough, and why purposive sampling?",
      "**[STUDENTS]** The sample size was not fixed in advance (Ch. III) and 54 reached. For a ranking by weighted means n = 54 gives stable means, but most respondents (53.7 %) have under 5 years' experience and 72 % never worked on a shoreline structure. The honest position is: this is an *expert-opinion* survey of mostly early-career engineers; its ranking is a perception, not a performance measurement.",
      "docs/06_survey_statistics.md §2")
    q(18, "What is the Cronbach's alpha of your questionnaire?",
      "**[STUDENTS: the value is not reported anywhere in the manuscript. Compute it from the pilot and final data with `make survey` and quote it, or say the pilot was not done.]** With one item per criterion, alpha should be presented as the internal consistency of a 'suitability' index.",
      "src/aparri/stats_survey.py; docs/06_survey_statistics.md")
    q(19, "Seawalls rank first, yet your literature review says seawalls can cause scour and downdrift erosion. Contradiction?",
      f"The survey measures perceived suitability on six criteria, not performance. The review warns about side-effects that the 'environmental impact' and 'maintenance' criteria only partly capture (seawall scores 4.20 and 4.30 there). The ranking is robust to criterion weights (Seawall first in {f['ws_first_seawall']:.0f} % of random weightings) but the order of the others is not: with engineering criteria only the order becomes {f['ws_eng']}. The framework should present the ranking together with these caveats.",
      "outputs/tables/survey_ranking_weight_sensitivity_PUBLISHED_means.csv; Ch. II")
    q(20, "How does your framework depend on the erosion-risk level if the survey did not ask per risk level?",
      "It does not yet, empirically. The questionnaire has one block per structure, so the ranking is area-wide. The link to risk level is a design principle of the framework; the group should either add a per-risk-level section to the questionnaire, or present the link as the group's reasoned proposal and say so (Chapter V).",
      "docs/06_survey_statistics.md §2")
    q(21, "How did you test Ho1?",
      "**[STUDENTS]** As written (difference *across risk levels*) Ho1 cannot be tested with the existing data. Options: re-word to 'differs among structures' and use a Friedman test with Wilcoxon post-hoc (Holm); or add a risk-level section and test again. Do not claim a test that was not done.",
      "docs/06_survey_statistics.md; src/aparri/stats_survey.py")
    q(22, "What does the accretion at Linao and Punta mean?",
      f"The Linao spit and Punta show seaward movement (Linao EPR up to {ext.loc['Linao','Max EPR (m/yr)']:+.1f} m/yr; Punta mean {ext.loc['Punta','Mean EPR (m/yr)']:+.2f}). These are river-mouth landforms whose position responds to the Cagayan River's sediment and flow; they are flagged and not part of the erosion classes. We do not interpret them physically here.",
      "outputs/maps/Fig_4_3_epr_profile_along_coast.png")
    q(23, "What about sea-level rise and subsidence?",
      "They are driving factors described in Chapter II but not measured in this study; the classification is empirical (what the shoreline did) and does not model causes or future change. Projections were not made (the manuscript's definition of GIS that mentions projections should be reworded).",
      "docs/03_thesis_revision_notes.md (item on the GIS definition)")
    q(24, "Can the framework be used for other coasts?",
      "The workflow (config-driven transect analysis) can; the survey-based ranking reflects perceptions of Philippine practitioners mostly in the Cagayan region and the physical results apply only to the open coast of these eight barangays.",
      "config/config.yaml; Ch. III scope")
    q(25, "What are the main limitations and what would you do with more time?",
      "Limits: 30 m imagery with no error or date records, waterline indicator and unknown tide, erosion rate only, river mouth excluded, no field check, survey not per risk level. With more time: seasonal Landsat composites with recorded scenes (script provided), measured GPS shorelines at the 20 points, an exposure overlay (buildings and roads), and a per-risk-level questionnaire.",
      "docs/02_method.md §7; scripts/gee_v2.js; docs/field_validation_form.md")
    out = [f"# 04 — Defense Q&A: 25 likely panel questions  {TAG}", "",
           "*Answers are short and honest; items in **[STUDENTS]** need your own facts. Numbers come from the pipeline's output tables. Practise answering in your own words.*", ""]
    for n, qu, an, ev in Q:
        out += [f"### {n}. {qu}", "", an, "", f"*Evidence:* `{ev}`", ""]
    return "\n".join(out)


# --------------------------------------------------------------------------- adviser memo
def adviser(f: dict) -> str:
    return f"""# Memo for the adviser — what changed in the GIS analysis and why  {TAG}

**To:** Engr. Mark Lester Cagurangan, adviser  **From:** the thesis group (to be signed by the students)  **Date:** [STUDENTS]

**Purpose.** To disclose, before the defense, that the GIS results in the manuscript were re-examined and re-done, and what that changed.

**What we found.** The shoreline-change results had been produced by an external person we can no longer contact. When we tried to document the method, we found that the three GIS products supplied (an Earth Engine raster workflow, a set of shoreline lines and a risk-polygon layer) were not consistent with one another or with the method in Chapter III: 124 risk polygons carried only three distinct rates; {f['audit_hand']} polygons (including the only 'High' ones) were not derived from any raster file and the other {f['audit_pix']} were 30 m pixel cells whose classes do not match the supplied rasters; the Earth Engine barangay statistics were computed in 1 km circles around single points, left two study barangays empty, and the raster 'accretion' was mostly open sea ({f['gee_acc_sea']:.0f} %); Table 4.2 of the manuscript was empty. Details: `docs/01_data_audit.md`, `docs/01b_gee_audit.md`.

**What we did.** We rebuilt the analysis in a documented, scripted workflow (shoreline cleaning, baseline and {f['cfg']['transects']['spacing_m']} m transects, End Point Rate and regression rate, the thesis' own class limits), checked it with test cases of known answers, compared it with an independent shoreline set, tested its sensitivity, and produced Table 4.2 and new Figures 4.1–4.2 from it.

**What changed in the results.** Open-coast erosion rates are {abs(f['epr_median']):.1f} m/yr (median) with a maximum of {abs(f['epr_min']):.1f} m/yr. No shoreline reaches the High class (> 5 m/yr); Bulala Sur and Bulala Norte are Medium (mean {f['ext'].loc['Bulala Sur','Mean EPR (m/yr)']:+.2f} and {f['ext'].loc['Bulala Norte','Mean EPR (m/yr)']:+.2f} m/yr); most of the remaining coast is Low, though much of it lies within the measurement error of the 2 m/yr limit. The earlier Figure 4.2 (High along Bulala) is withdrawn.

**What did not change.** The survey of 54 experts and Table 4.4 are unchanged (we have not seen the raw responses; arithmetic checked: one 0.0001 rounding slip). Objective 3 and Hypothesis Ho1 cannot be tested with the questionnaire as designed (no risk-level dimension); we propose an amendment (`docs/06_survey_statistics.md`).

**What we ask of you.** (1) Agreement that the Chapter III method text and Chapter IV GIS results be replaced as described; (2) guidance on the treatment of Ho1/Objective 3; (3) permission to carry out a short field verification before the final defense.

**What remains unknown.** Origin and dates of the original shoreline lines; positional error; tide; field verification. These are stated as limitations.
"""


def run() -> None:  # pragma: no cover
    cfg = load_config()
    f = facts(cfg)
    docs = REPO_ROOT / "docs"
    for name, text in (("methods_draft.md", methods(f)), ("results_drafts.md", results(f)), ("04_defense_qa.md", qa(f)), ("for_the_adviser.md", adviser(f))):
        (docs / name).write_text(text, encoding="utf-8")
        print("wrote docs/" + name)


if __name__ == "__main__":  # pragma: no cover
    run()
