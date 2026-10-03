# Survey data schema (how to give the survey data to the pipeline)

The pipeline never guesses survey numbers. Put the **real** responses in `data/raw/survey/survey_responses.csv` (create the folder) and run `make survey`.

## Easiest way: one row per respondent ("wide")
Fill `data/templates/survey_responses_template_wide.csv` (36 columns): `respondent_id`, five profile columns, then 30 rating columns named `<Structure> | <Criterion>` (for example `Seawall | Stability`). Convert it with `aparri.stats_survey.wide_to_long`, or paste into the long template.

## What the program reads ("long")
One row = one respondent × one structure × one criterion. See `data/templates/survey_responses_template.csv`.

| column | allowed values |
|---|---|
| `respondent_id` | any unique text (keep it anonymous: R01, R02 …) |
| `profession` | Civil Engineer · DPWH Engineer · Coastal/Environmental Engineer · Contractor · LGU Technical Personnel |
| `years_experience` | Less than 5 years · 5-10 years · 11-20 years · More than 20 years |
| `worked_on_structure` | Yes / No (Have you worked on or supervised a shoreline protection structure?) |
| `familiar_with_structures` | Yes / No |
| `trained` | Yes / No (education or training in coastal engineering or shoreline protection) |
| `structure` | Seawall · Revetment · Riprap · Breakwater · Mangrove Rehabilitation |
| `risk_level` | empty (current questionnaire) · Low · Medium · High (only if a risk-level version of the questionnaire is ever used) |
| `criterion` | Stability · Effectiveness · Cost · Durability · Maintenance · Environmental Impact |
| `score` | whole number 1–5 |
| `data_origin` | REAL (SYNTHETIC rows are refused for outputs) |

The validator reports every problem in plain English with the spreadsheet row (out-of-range scores, unknown labels, duplicates, a respondent with two different professions …).

## Facts extracted from the thesis (Chapter III–IV, Appendix B)
* 54 expert respondents (Table 4.1): Civil Engineer 21, DPWH Engineer 18, Coastal/Environmental Engineer 12, Contractor 1, LGU 2.
* 5 structures × 6 criteria, each criterion measured by **one** Likert statement (Appendix B); scale 1–5; weighted mean x̄ = Σfx/N; interpretation 4.21–5.00 Very High, 3.41–4.20 High, 2.61–3.40 Moderate, 1.81–2.60 Low, 1.00–1.80 Very Low.
* Reliability: pilot test, Cronbach's α ≥ 0.70 acceptable (no value reported).
* Decision matrix (Table 3.2): overall score = average of the six criterion means; rank 1 = highest.
* Hypothesis Ho1/Ha1: risk levels have no/a significant difference on the perceived efficiency and feasibility of the structures; significance level not stated (the config uses 0.05 and labels it as an assumption).
