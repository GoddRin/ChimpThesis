# Memo for the adviser — what changed in the GIS analysis and why  [DRAFT – FOR STUDENT REVIEW]

**To:** Engr. Mark Lester Cagurangan, adviser  **From:** the thesis group (to be signed by the students)  **Date:** [STUDENTS]

**Purpose.** To disclose, before the defense, that the GIS results in the manuscript were re-examined and re-done, and what that changed.

**What we found.** The shoreline-change results had been produced by an external person we can no longer contact. When we tried to document the method, we found that the three GIS products supplied (an Earth Engine raster workflow, a set of shoreline lines and a risk-polygon layer) were not consistent with one another or with the method in Chapter III: 124 risk polygons carried only three distinct rates; 7 polygons (including the only 'High' ones) were not derived from any raster file and the other 117 were 30 m pixel cells whose classes do not match the supplied rasters; the Earth Engine barangay statistics were computed in 1 km circles around single points, left two study barangays empty, and the raster 'accretion' was mostly open sea (96 %); Table 4.2 of the manuscript was empty. Details: `docs/01_data_audit.md`, `docs/01b_gee_audit.md`.

**What we did.** We rebuilt the analysis in a documented, scripted workflow (shoreline cleaning, baseline and 50 m transects, End Point Rate and regression rate, the thesis' own class limits), checked it with test cases of known answers, compared it with an independent shoreline set, tested its sensitivity, and produced Table 4.2 and new Figures 4.1–4.2 from it.

**What changed in the results.** Open-coast erosion rates are 1.5 m/yr (median) with a maximum of 3.5 m/yr. No shoreline reaches the High class (> 5 m/yr); Bulala Sur and Bulala Norte are Medium (mean -2.74 and -3.35 m/yr); most of the remaining coast is Low, though much of it lies within the measurement error of the 2 m/yr limit. The earlier Figure 4.2 (High along Bulala) is withdrawn.

**What did not change.** The survey of 54 experts and Table 4.4 are unchanged (we have not seen the raw responses; arithmetic checked: one 0.0001 rounding slip). Objective 3 and Hypothesis Ho1 cannot be tested with the questionnaire as designed (no risk-level dimension); we propose an amendment (`docs/06_survey_statistics.md`).

**What we ask of you.** (1) Agreement that the Chapter III method text and Chapter IV GIS results be replaced as described; (2) guidance on the treatment of Ho1/Objective 3; (3) permission to carry out a short field verification before the final defense.

**What remains unknown.** Origin and dates of the original shoreline lines; positional error; tide; field verification. These are stated as limitations.
