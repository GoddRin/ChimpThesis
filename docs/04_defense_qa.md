# 04 — Defense Q&A: 25 likely panel questions  [DRAFT – FOR STUDENT REVIEW]

*Answers are short and honest; items in **[STUDENTS]** need your own facts. Numbers come from the pipeline's output tables. Practise answering in your own words.*

### 1. Why EPR and not LRR (or another rate)?

The thesis defines the classes on the 1990–2025 End Point Rate, which only needs the first and last shoreline. We also computed LRR from all five dates: they are strongly correlated (r = 0.94) and put the same class on 89 % of transects; LRR is the more robust estimator when intermediate dates exist, EPR is the one the objectives name. We report both and classify with EPR.

*Evidence:* `docs/05_sensitivity_validation.md §2; outputs/maps/Fig_6_epr_vs_lrr.png`

### 2. How accurate is a 30 m Landsat pixel for a rate as small as 0.86 m/yr?

It is not: one pixel over 35 years *is* 0.86 m/yr, and a one-pixel error at both dates gives ±1.21 m/yr. That is why we report the uncertainty, mark classes that could change inside it (`class_may_flip`), and do not claim that Low versus Medium is a sharp physical boundary. The Medium class at Bulala Norte (mean -3.35 m/yr; 4 % of its transects could change class) lies clearly beyond the error band around the 2 m/yr limit; Bulala Sur (-2.74 m/yr; 100 % could change) is borderline, and the Low class elsewhere is largely within the band.

*Evidence:* `docs/02_method.md §7; Table_4_2_extended.csv (% classes that may flip)`

### 3. How did you handle the Cagayan River mouth?

The open sea-facing coast and the river banks were separated by a fixed geometric rule, and only the open coast was classified. At the mouth the shorelines of different years diverge and loop, transects cross each other, and the resulting rates mean nothing, so those transects are left unclassified (grey on the map). Including the river banks in a sensitivity run produced High values (4.8 % of transects), all at the mouth.

*Evidence:* `docs/02_method.md §1; outputs/maps/clean_review.png; sensitivity run `with_estuarine``

### 4. Why these thresholds (2 and 5 m/yr)?

They are the limits adopted by the thesis from the literature (Osondu et al., 2025 [VERIFY CITATION]; the manuscript also attributes the 5 m/yr limit to Luijendijk et al., 2018 [VERIFY CITATION]). They are conventions, not natural laws; we show that the class shares move a lot if the limits shift by ±0.5 m/yr and that is stated as a limitation.

*Evidence:* `docs/05_sensitivity_validation.md §1`

### 5. Why only 1990 and 2025?

The thesis defines EPR with two end points; the three middle shorelines are shown in Figure 4.1 and used in the LRR. With five dates a regression is possible and we report it. The reason for not using only the middle dates is that EPR is the documented method of the study and is standard (DSAS).

*Evidence:* `docs/02_method.md §4`

### 6. Is this a vulnerability or risk assessment?

No. It is a classification of the erosion rate, as the manuscript itself says (p. 41, p. 60). Risk would also need exposure (people, buildings, roads) and vulnerability; those were not assessed. We would call the classes 'erosion-rate classes' in the discussion.

*Evidence:* `docs/02_method.md §7 (point 6); Ch. IV Discussion`

### 7. Where do your shorelines come from and how do you know they are right?

**[STUDENTS: state the origin of the lines first — see Q-G1.]** What we can show: the lines were cleaned with a logged procedure, and an independent raster-derived set (from the Earth Engine masks) agrees with them to a median of 10–17 m (robust SD) on the same transects, with the same class for 92 % of 253 transects. What we cannot show: ground truth. A field check at 20 points is planned.

*Evidence:* `docs/05_sensitivity_validation.md §3; docs/field_validation_form.md`

### 8. Why are the figures and numbers different from your proposal?

Because the original GIS outputs could not be reproduced: of the 124 risk polygons, 7 (the only 'High' and 'Medium 2.59' ones) were not derived from any raster we have, 48 were labelled Medium although their own value was 0.857 m/yr, and the Earth Engine statistics used 1 km circles around points. We rebuilt the analysis in a documented pipeline and disclosed the change to the adviser.

*Evidence:* `docs/01_data_audit.md; docs/01b_gee_audit.md; docs/for_the_adviser.md`

### 9. What is the uncertainty of your EPR values?

No measured positional error exists. With one Landsat pixel at each date the EPR uncertainty is ±1.21 m/yr (a lower bound: tide, georeferencing and extraction errors would add to it). An empirical comparison of two shoreline sets suggests a per-date error of about 7–12 m for the cleaned lines, but the 30 m pixel is the physical floor for Landsat-based shorelines.

*Evidence:* `docs/05_sensitivity_validation.md §3`

### 10. Why is there no High-risk shoreline?

Because no valid open-coast transect lost more than 3.5 m/yr. The old figure's High class came from two hand-drawn polygons that cannot be reproduced; the raster High pixels lie in the river mouth. The result is stable under the tested choices except including the river banks (and a single transect at the 400 m smoothing).

*Evidence:* `outputs/maps/Fig_legacy_vs_rebuilt.png; docs/05_sensitivity_validation.md`

### 11. Which barangay is eroding fastest and by how much?

Bulala Norte: mean EPR -3.35 m/yr (about 117 m in 35 years), then Bulala Sur (-2.74). Both are Medium class.

*Evidence:* `Table_4_2_barangay_results.xlsx`

### 12. Does tide affect the shorelines?

Yes. A satellite waterline is the water level at the moment of the image; on a gently sloping beach one metre of tide moves the line tens of metres. Tide state was not recorded, so it is a source of error that cannot be removed here; using the same season each year (the proposed Landsat v2 composite) and recording the tide are the remedies.

*Evidence:* `docs/02_method.md §7 (point 2); scripts/gee_v2.js`

### 13. What about seasonality and typhoons?

The legacy composites were whole-year medians that mix seasons. Typhoon storms can move a shoreline by metres in a day; with five snapshots 10 years apart, we cannot separate storm response from the long-term trend. We state EPR as a long-term average only.

*Evidence:* `docs/01b_gee_audit.md §1`

### 14. Why 50 m transect spacing?

It is a standard DSAS-type choice. We repeated the analysis at 25 m and 100 m: the share of each class changed by ≤ 0.5 percentage points.

*Evidence:* `docs/05_sensitivity_validation.md §1`

### 15. How was the baseline chosen and could it bias the result?

The baseline is the smoothed 1990 shoreline moved landward behind all years; it is only a measuring grid, since EPR is a difference of two distances measured along the same transect. Changing the smoothing window (100–400 m) or the offset (150→300 m) changed class shares by ≤ 0.5 percentage points.

*Evidence:* `docs/02_method.md §3; sensitivity runs`

### 16. Did you check on the ground?

**[STUDENTS: answer truthfully.]** As of this writing no field verification has been done. A 20-point verification template with coordinates is provided; until it is filled in the answer is 'not yet'.

*Evidence:* `docs/field_validation_form.md; outputs/field_validation/`

### 17. Why are 54 respondents enough, and why purposive sampling?

**[STUDENTS]** The sample size was not fixed in advance (Ch. III) and 54 reached. For a ranking by weighted means n = 54 gives stable means, but most respondents (53.7 %) have under 5 years' experience and 72 % never worked on a shoreline structure. The honest position is: this is an *expert-opinion* survey of mostly early-career engineers; its ranking is a perception, not a performance measurement.

*Evidence:* `docs/06_survey_statistics.md §2`

### 18. What is the Cronbach's alpha of your questionnaire?

**[STUDENTS: the value is not reported anywhere in the manuscript. Compute it from the pilot and final data with `make survey` and quote it, or say the pilot was not done.]** With one item per criterion, alpha should be presented as the internal consistency of a 'suitability' index.

*Evidence:* `src/aparri/stats_survey.py; docs/06_survey_statistics.md`

### 19. Seawalls rank first, yet your literature review says seawalls can cause scour and downdrift erosion. Contradiction?

The survey measures perceived suitability on six criteria, not performance. The review warns about side-effects that the 'environmental impact' and 'maintenance' criteria only partly capture (seawall scores 4.20 and 4.30 there). The ranking is robust to criterion weights (Seawall first in 96 % of random weightings) but the order of the others is not: with engineering criteria only the order becomes Seawall > Revetment > Mangrove Rehabilitation > Breakwater > Riprap. The framework should present the ranking together with these caveats.

*Evidence:* `outputs/tables/survey_ranking_weight_sensitivity_PUBLISHED_means.csv; Ch. II`

### 20. How does your framework depend on the erosion-risk level if the survey did not ask per risk level?

It does not yet, empirically. The questionnaire has one block per structure, so the ranking is area-wide. The link to risk level is a design principle of the framework; the group should either add a per-risk-level section to the questionnaire, or present the link as the group's reasoned proposal and say so (Chapter V).

*Evidence:* `docs/06_survey_statistics.md §2`

### 21. How did you test Ho1?

**[STUDENTS]** As written (difference *across risk levels*) Ho1 cannot be tested with the existing data. Options: re-word to 'differs among structures' and use a Friedman test with Wilcoxon post-hoc (Holm); or add a risk-level section and test again. Do not claim a test that was not done.

*Evidence:* `docs/06_survey_statistics.md; src/aparri/stats_survey.py`

### 22. What does the accretion at Linao and Punta mean?

The Linao spit and Punta show seaward movement (Linao EPR up to +5.3 m/yr; Punta mean +0.19). These are river-mouth landforms whose position responds to the Cagayan River's sediment and flow; they are flagged and not part of the erosion classes. We do not interpret them physically here.

*Evidence:* `outputs/maps/Fig_4_3_epr_profile_along_coast.png`

### 23. What about sea-level rise and subsidence?

They are driving factors described in Chapter II but not measured in this study; the classification is empirical (what the shoreline did) and does not model causes or future change. Projections were not made (the manuscript's definition of GIS that mentions projections should be reworded).

*Evidence:* `docs/03_thesis_revision_notes.md (item on the GIS definition)`

### 24. Can the framework be used for other coasts?

The workflow (config-driven transect analysis) can; the survey-based ranking reflects perceptions of Philippine practitioners mostly in the Cagayan region and the physical results apply only to the open coast of these eight barangays.

*Evidence:* `config/config.yaml; Ch. III scope`

### 25. What are the main limitations and what would you do with more time?

Limits: 30 m imagery with no error or date records, waterline indicator and unknown tide, erosion rate only, river mouth excluded, no field check, survey not per risk level. With more time: seasonal Landsat composites with recorded scenes (script provided), measured GPS shorelines at the 20 points, an exposure overlay (buildings and roads), and a per-risk-level questionnaire.

*Evidence:* `docs/02_method.md §7; scripts/gee_v2.js; docs/field_validation_form.md`
