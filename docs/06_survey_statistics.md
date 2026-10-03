# 06 — What the survey design supports statistically (Phase 7)

*[DRAFT – FOR STUDENT REVIEW]. No respondent-level data were supplied, so nothing below was computed from survey responses. Everything is either (a) arithmetic on the numbers already printed in the manuscript, (b) an analysis of the **design**, or (c) tooling (`src/aparri/stats_survey.py`, 16 tests with hand-computed answers, synthetic data only).*

## 1. What I checked in the manuscript

| Check | Result |
|---|---|
| Table 4.1 (profession): 21+18+12+1+2 | = 54, percentages 38.9 / 33.3 / 22.2 / 1.9 / 3.7 are correct |
| Table 4.2 (experience): 29+16+6+3 | = 54, percentages correct |
| Table 4.3 | yes+no = 54 for every question, percentages correct |
| Table 4.4 overall mean = mean of the six criterion means | correct for all five structures (to 4 decimals) |
| Are the cell means possible with n = 54? | Yes — every mean × 54 is a whole number, as it must be. **One cell is off by a rounding slip:** Breakwater × Effectiveness is printed 3.8149; 206/54 = 3.8148 (difference 0.0001) |
| Interpretation labels (bands) and ranks | consistent with the printed means (Seawall Very High, rank 1; the other four "High") |

## 2. What the design does *not* support

1. **Objective 3 and Ho1 cannot be answered with this questionnaire.** Appendix B asks each respondent to rate each structure once on six statements. There is no risk-level dimension, so there is no data on "which structure is best for Low / Medium / High erosion risk", and Ho1/Ha1 (*risk levels differ in perceived efficiency/feasibility*) has nothing to test. Table 4.4 is a single, area-wide ranking. Options, in order of effort:
   * **A (best, needs time):** add a short section to the questionnaire — "for a shoreline with *Low / Medium / High* erosion rate (describe each), rate the same structures" — and re-survey, at least a smaller group. The pipeline already handles this (`risk_level` column; Friedman for repeated ratings or Kruskal–Wallis/Dunn–Holm for independent groups).
   * **B (no new data):** re-word the hypothesis as *"perceived suitability differs among the five structures"* and test it on the existing data with a Friedman test and Wilcoxon post-hoc with Holm correction (implemented: `friedman_among_structures`).
   * **C:** keep risk-level matching as a *design principle* of the framework (engineering judgement, clearly labelled as the group's proposal) and drop the hypothesis test. State honestly in Chapter V that the ranking is area-wide.
2. **No significance test accompanies the ranking.** Table 4.4 shows means only. "Seawall ranks first" needs at least a standard deviation and a Friedman test; without them the panel can ask whether 4.35 vs 4.14 is a real difference.
3. **Ceiling effect and narrow range.** All 30 cell means lie between 3.37 and 4.57, i.e. almost everything is "High" or "Very High". The instrument discriminates little between structures.
4. **Item wording.** Statement 4 reads "*X is your most recommended erosion protection structure according to its durability*" — it cannot be true of all five structures at once, and the 1–5 labels on the questionnaire ("Not/Slightly/Moderately/Highly Appropriate") do not match the agree-style statements ("Seawalls are structurally stable"). All six statements are worded positively, which invites acquiescence.
5. **Who answered.** 53.7 % have under 5 years' experience, 72.2 % never worked on or supervised a shoreline structure and 61.1 % have no coastal-engineering training (Table 4.3). Describe this as a limitation and, once raw data exist, check whether the ranking holds in the experienced subgroup.
6. **Reliability.** The manuscript promises a pilot test and α ≥ 0.70 but reports no α. With one item per criterion, α for a structure measures whether people who rate a structure high on one criterion rate it high on the others; it is defensible only if the six statements are treated as indicators of one idea ("suitability"). Report α per structure and overall (`reliability()`), and say so.

## 2b. Is the ranking sensitive to the (unstated) equal weights?

The decision matrix averages the six criteria with equal weights. Using only the **published means** (no respondent data needed), `weight_sensitivity()` re-ranks under named weightings and 20 000 random weightings (`outputs/tables/survey_ranking_weight_sensitivity_PUBLISHED_means.csv`):

* equal weights, cost ×2, environment ×2, stability+durability ×2: Seawall > Mangrove > Revetment > Breakwater > Riprap in all four;
* engineering criteria only (no cost, no environment): Seawall > Revetment > Mangrove …;
* cost + environment only: Mangrove first;
* over random weightings Seawall is ranked first in about **96 %** and the whole order is unchanged in about **87 %** (seed 1).

So "Seawall first, Riprap last" is robust to weighting; the order of Mangrove vs Revetment depends on how much weight engineering performance gets.

## 3. What to do when the raw responses arrive

1. Put them in `data/raw/survey/survey_responses.csv` (see `docs/survey_schema.md`); `make survey` validates, then reproduces Table 4.4 and prints every cell that differs from the manuscript (`outputs/tables/survey_table_4_4_vs_published.csv`).
2. Add SD, median and % of 4–5 ratings to each cell; report Cronbach's α (pilot and final).
3. Test the hypothesis you decided on (A/B/C above) with the exact test, statistic, df, p and effect size — the code prints all five.
4. Optional: Kruskal–Wallis of the overall rating by profession and by experience group (does the ranking depend on who answered?).
