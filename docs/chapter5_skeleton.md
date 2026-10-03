# Chapter V skeleton — Conclusion and Recommendation  [DRAFT – FOR STUDENT REVIEW]

*Structure only, tied one-to-one to the four specific objectives. Each slot lists (a) the evidence that exists in this repository, (b) what the students still have to supply, and (c) a sentence frame with blanks. **No conclusion is written for you**: a conclusion is the students' to make and defend, and none may go beyond the evidence. Delete the prompts when done. Paragraph form, not bullets (department format).*

## Summary (paragraph form)
Frame: *The study aimed to develop a construction management framework for shoreline protection structures in Aparri, Cagayan, based on erosion-rate classes of … . Shoreline positions of 1990, 2000, 2010, 2020 and 2025 for the open coast of … barangays were derived from **[source]** and processed with a transect-based End Point Rate method (… transects every 50 m). … experts (n = …) rated five structures on six criteria (Likert scale 1–5), analysed with the weighted mean. The framework was assembled from … .*
Evidence: `docs/methods_draft.md`, `docs/results_drafts.md`, Table 4.2, Table 4.4. Supply: the framework's final form (Fig. 2 or its replacement) and any field verification.

## Conclusion (one conclusion per objective)

**Objective 1 — classify the coast into Low, Medium and High erosion-risk classes.**
Evidence: Table 4.2; Fig. 4.2 (rebuilt); `docs/05_sensitivity_validation.md`. Facts available to state (check against the final run): the open coast was classified Low / Medium / High as given in Table 4.2; no High class occurs; Medium occurs at Bulala Sur and Bulala Norte and in parts of Linao, Dodan and Maura; the river-mouth shorelines were not classified; Low versus Medium is uncertain wherever the rate is near 2 m/yr (30 m pixel).
Frame: *Based on the 1990–2025 End Point Rate, … km (…%) of the … km classified shoreline were Low, … km Medium and … km High. The highest mean rate occurred in … (… m/yr). These classes describe the erosion rate only.*
Supply: whether the group adopts the rebuilt results (decision for adviser); positional error if obtained.

**Objective 2 — determine the most suitable structures by perceived efficiency and feasibility.**
Evidence: Table 4.4 (checked: overall means and ranks consistent, one 0.0001 rounding slip); weight-sensitivity of the ranking (`docs/06_survey_statistics.md` §2b). Frame: *The experts rated … highest (overall weighted mean …, Very High) followed by …; the order of … and … changed when …. This reflects perceived suitability among respondents of whom …% had under five years' experience.*
Supply: raw responses, SD, α, the test among structures.

**Objective 3 — rank the structures for each risk level.**
Evidence: **none yet** — the questionnaire did not ask per risk level (see `docs/06_survey_statistics.md`). Options: (A) add the section and re-survey; (B) present the area-wide ranking and *state that* risk-level matching is the group's proposal; (C) re-word the objective. Frame (option B): *The survey ranked the structures for the study area as a whole; matching a structure to a risk level in the framework rests on the group's engineering reasoning (Chapter II), not on respondent ratings by risk level.*

**Objective 4 — develop the construction management framework.**
Evidence: Fig. 2 (generic flow, four phases). Supply: the framework content per risk class (what is required in planning, design, construction, monitoring for Low, Medium and, if it ever occurs, High), each item tied to a source or to the group's reasoning; a worked example for one barangay from Table 4.2.
Frame: *The framework consists of … phases … . For a Medium-class segment such as … the framework prescribes … because … .*

## Hypothesis (if retained)
State the test actually carried out (name, statistic, df, p, effect size) and the decision at α = 0.05 — or state that the hypothesis was reformulated and why.

## Recommendations (specific, actionable, derived from the findings)
Slots (adapt; delete what the evidence does not support):
1. *To the LGU / MDRRMO:* prioritise field inspection of the Medium-class stretches (Bulala Sur–Norte; …) and install **[monitoring such as repeated GPS shoreline surveys, with the points in `outputs/field_validation/`]**. Evidence: Table 4.2, Fig. 4.2.
2. *To DPWH / engineers:* use the framework only together with site-specific coastal engineering design; the classes describe rate only (state this).
3. *To the group's successors:* (a) record image dates and tide for each shoreline, (b) use a seasonal composite, (c) add exposure (buildings/roads) and vulnerability, (d) collect a per-risk-level survey, (e) extend to the Cagayan River mouth with a method suited to estuaries.
4. *To the department:* keep the reproducible pipeline (config + scripts + logs) with the thesis.

## Limitations to restate
Rate only; 30 m imagery without recorded error, dates or tide; river mouth excluded; survey not per risk level and with mostly early-career respondents; no/limited field verification.
