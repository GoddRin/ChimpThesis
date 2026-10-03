# 03 — Thesis revision notes  [DRAFT – FOR STUDENT REVIEW]

*An edit list for the manuscript `CE-Project-Manuscript-Format.docx` (the original was **not** changed). Every item was re-checked against the text of the .docx. Page numbers are the manuscript's own running-header numbers (±1 page, because the header sits at the top of the next page). Priority: **H** must fix before the defense · **M** should fix · **L** polish. Items marked [VERIFY CITATION] were not checked against the original sources — no source could be reached from the analysis environment; the students must check them.*

## A. Method and content consistency

| ID | Where | What the manuscript says now | Suggested fix | Why | P |
|---|---|---|---|---|---|
| R-01 | Ch. III, Risk Assessment Method p. 39; Data Gathering p. 37–38 | The shoreline positions "will be digitized and overlaid" from satellite imagery | Replace by the procedure in `docs/methods_draft.md` (cleaning, baseline, transects, EPR/LRR, uncertainty, classification), past tense | The work done was Landsat/NDWI (Earth Engine) rasters plus cleaned vector lines, not described anywhere | H |
| R-02 | Ch. III Research Instrument p. 37; Data Gathering p. 38 | Satellite images "of the years 1990, 2000, 2010, 2020 and 2025 will be considered" — no source, sensor, resolution, date or shoreline indicator | State imagery source, sensors, 30 m resolution, dates (or that they are unknown), tide, and the shoreline indicator | A reader cannot repeat or judge the GIS work; the panel will ask | H |
| R-03 | Conceptual Framework p. 4–5 (figure) | Inputs: "Satellite images (Google Earth Pro)", "QGIS"; process: "Pilot testing", "Analysis", "Decision Matrix" | Redraw to match what was done (Landsat imagery; cleaned shorelines; transects; EPR; classes; survey; decision matrix; field verification if done) | The figure names tools that were not the ones used | M |
| R-04 | Hypothesis p. 5; Statistical Tools p. 47–50 | Ho1/Ha1: risk levels differ in perceived efficiency/feasibility; no test named, no significance level | See `docs/06_survey_statistics.md`: either re-word (differences among structures; Friedman + Wilcoxon-Holm) or collect per-risk-level ratings; state α = 0.05 | The questionnaire has no risk-level dimension, so Ho1 cannot be tested as written | H |
| R-05 | Ch. IV Introduction p. 52; Ch. IV p. 52–66 | "The findings … include … ranking of suitable shoreline protection structures [by risk level] and construction management framework" | Add sections for Objectives 3 and 4 or re-word the objectives to what the data support (area-wide ranking) | Ch. IV contains Table 4.4 (one overall ranking) and no framework section | H |
| R-06 | Title; General Objective p. 4; Objective 3 p. 4 | "… based on coastal erosion risk levels"; "rank … depending on the various coastal erosion risk levels" | Re-word, or add the risk-level dimension to the survey | Same reason as R-05 | H |
| R-07 | Definition of Terms p. 8 ("Coastal Erosion Factors"); Conceptual Framework p. 5; Significance p. 6; Scope p. 7 ("field survey"); Reliability p. 46 ("Field Observation Checklist") | Factors (waves, sediments, development) "assessed to explain shoreline behavior"; field observations and checklist mentioned | Add a short "Coastal erosion factors" subsection using `docs/erosion_factors_plan.md`, or delete the claim | No data or results on factors or field observation exist in the manuscript | H |
| R-08 | Definition of Terms p. 8, GIS | "…visualize future shoreline projections…" | Delete "future shoreline projections" (no projection was made) or add a clearly labelled projection (Phase 10 option B) | Promised, not done | M |
| R-09 | Ch. III Population and Sample p. 36 | "The total number of respondents is not specified … Collection of data will stop once enough information…" | State n = 54, how and when selected, how many were invited, response rate | Ch. IV reports 54 | M |
| R-10 | Ch. III Reliability Test p. 46–47; Ch. IV | Pilot test and Cronbach's α ≥ 0.70 promised; no α reported anywhere | Report α for the pilot and the final data (`make survey`) or state that the pilot was not done | Promised analysis missing | H |
| R-11 | Table 3.1 note p. 41 vs Table 4.1 source p. 55; Ch. II p. 19 | Note: "adapted from coastal geomorphology studies"; Table 4.1: Osondu et al. (2025); Ch. II credits Luijendijk et al. (2018) for the 5 m/yr limit | Use one source statement in both tables; check what each paper really says [VERIFY CITATION]. Say "erosion rate = magnitude of negative EPR; limits inclusive at 2 and 5 m/yr" | Source and sign convention differ between tables; Table 3.1 gives magnitudes while the formula gives negative erosion | M |
| R-12 | Ch. IV Table 4.2 p. 56–57 | Empty (header and the row "Dodan") | Replace with `outputs/tables/Table_4_2_barangay_results.docx` (+ km version) | Empty table | H |
| R-13 | Figures 4.1 (p. 53–54) and 4.2 (p. 58) | Old figures from unreproducible layers | Replace with `outputs/maps/Fig_4_1_v2_*.png` and `Fig_4_2_v2_*.png`; add the EPR profile `Fig_4_3_*.png` | `docs/01_data_audit.md` | H |
| R-14 | Ch. IV p. 58–60 (text after Fig. 4.2 and Discussion) | High risk at Bulala Sur and Bulala Norte; Medium at Bulala Norte, Punta, San Antonio, Maura, Dodan, Paddaya; Low at Linao | Rewrite with `docs/results_drafts.md` | Not supported by the rebuilt analysis (Bulala = Medium; no High; Linao mixed) | H |
| R-15 | Chapter V p. 67 | Template instructions ("Provide a concise recap …") | Write Summary, Conclusion, Recommendations using `docs/chapter5_skeleton.md` | Empty chapter | H |
| R-16 | Proposal Summary p. 5–6 | Written as a proposal ("will address", "will use") | Rewrite as an abstract of the finished study with results and keywords | Out of date | M |
| R-17 | Approval Sheet p. 2 | "…recommended for proposal defense" | Update for the stage actually being defended | Stage mismatch | L |
| R-18 | Ch. III throughout | Mixed tenses ("will be employed" / "was utilized", p. 48–49) | Use past tense for completed work | Consistency | L |
| R-19 | Research Design p. 35 | Two consecutive paragraphs both begin "Quantitative analysis will …"; the first (GIS rates) and the second (ranking) | Check whether the second was meant to be "Qualitative …"; otherwise merge | Probable slip | L |
| R-20 | Ch. I p. 2; Ch. III Study Area p. 34 | "Aparri … 18 km coastline (Ballad et al., 2021)" | Reconcile with the open-coast length of the eight barangays in the analysis (≈ 20.5 km per shoreline) or explain the difference [VERIFY CITATION] | Two different coast lengths | L |

## B. Numbers, tables, figures

| ID | Where | Current | Fix | P |
|---|---|---|---|---|
| R-21 | Ch. IV: Table 4.1 appears twice (risk classes p. 55; profession p. 61) and Table 4.2 twice (barangay results p. 56; experience p. 62); text refers to "Table 4.1 below" (p. 62), "Table 4.2 shows" (p. 63) | Duplicate numbers | Renumber in order: 4.1 risk classes, 4.2 barangay results, 4.3 profession, 4.4 experience, 4.5 familiarity/training, 4.6 decision matrix; update all in-text references and the list of tables | H |
| R-22 | Multi-Temporal Shoreline Change p. 54 | "According to Figure 4.2, the position of the shorelines is different…" | Figure 4.1 (the shoreline overlay) | M |
| R-23 | Ch. III "Figure 1", "Figure 2" vs Ch. IV "Figure 4.1/4.2" | Mixed numbering | "Figure 3.1", "Figure 3.2" | L |
| R-24 | Table 4.4 p. 65 | Breakwater × Effectiveness = 3.8149 | 206 ÷ 54 = 3.8148 (all other cells check out; overall means and ranks verified) | L |
| R-25 | Table 4.4 | Means only | Add SD, n and a Friedman test with post-hoc (`docs/06_survey_statistics.md`) | M |
| R-26 | Table 4.1 (risk classes) p. 55 repeats Table 3.1 | Duplicate table | Keep one (or cross-reference) | L |

## C. Wording

| ID | Where | Current | Fix | P |
|---|---|---|---|---|
| R-27 | Evaluation of Shoreline Protection Structures p. 65 | "The responses were analyzed using the to determine the average assessment…" | "…analyzed using the weighted mean to determine…" | M |
| R-28 | Definition of Terms, Erosion Risk Map p. 8 | "…based on computed shoreliSelectin e rates" | "…based on computed shoreline change rates" | M |
| R-29 | Definition of Terms p. 8 | "Geographical Information System (GIS)" (elsewhere "Geographic") | Use "Geographic Information System" throughout | L |
| R-30 | Definition of Terms p. 8 | "Scouring. It is the primary cause of structural failure in the region." — an unsupported claim, not a definition | Define scouring (removal of bed/foreshore material at a structure's toe); if the claim is kept, cite a source [VERIFY CITATION]. Same for "Morphological Flux", "Shoreline Protection Structures", "Coastal Erosion Factors" (they assert roles instead of defining) | M |
| R-31 | Definition of Terms | EPR, NSM, LRR, transect, baseline, NDWI, Landsat, accretion are used but not defined | Add them (wording in `docs/02_method.md`) | M |

## D. References and citations ([VERIFY CITATION] throughout)

| ID | Where | Issue | P |
|---|---|---|---|
| R-32 | Ch. I–II | **In-text citations with no matching entry in the reference list** (surname search): Dong et al. 2024 ("WS Dong"); Rocha et al. 2023; Rivera & Dela Vega 2025; Taslin et al. 2024; Nguyen et al. 2025; Ballad et al. 2021; DPWH 2021; Angnuureng 2025; Toledo et al. 2025; Zhou et al. 2023; Thirumurthy et al. 2022; "OECD (2026)"; "Nature Communications (2022)"; "Elsevier's Anthropocene (2023)"; "Ouyang & Wang (2024)" (the list has Zhang, Ouyang et al., 2024) | H |
| R-33 | Ch. II p. 12–13, 18 | **In-text claim does not obviously match the listed work**: Nerves et al. (2024) is described as a study of river deltas such as Aparri with "150+ m in 30 years" and "open bay regions", but the listed paper is a DSAS study at New Washington, Aklan; Calapini et al. (2025) is cited for sea-level-rise rates but the listed paper is a flood-hazard model of the Cagayan River Basin; Nieuwenhout & Andreasson (2023) is cited for typhoon clustering but the listed paper is on the legal framework of artificial energy islands; Luijendijk et al. (2018) is cited for ">5 m/yr = rapidly eroding" (check the paper) | H |
| R-34 | Reference list p. 68+ | Many entries carry Google-Scholar search/cache links (e.g. Tsiakos & Chalkias; Sun et al.; Igbokwe et al.; Cao et al.; Osondu et al.; Dodgson et al.; Tzepkenlis et al.; Li & Fang) instead of DOI/publisher URLs; some have broken line-wrapped URLs | M |
| R-35 | Reference list | Several 2026 entries (Felipe et al.; Li & Fang; Tora et al.; Elemin et al.; Senatilleke et al.; Tikekar et al.; Bartolome & Griño) — confirm each is published in final form and that the link works | L |

## E. Template leftovers and formatting

| ID | Where | Issue | P |
|---|---|---|---|
| R-36 | p. 68–70 | The department's template guidance is still in the manuscript: "References" instructions with the hypothetical examples (Dela Rosa 2025, GreenFuture, Lopez 2021, Ramirez 2022, Santos & Cruz 2024, Villanueva 2023) and "Appendix A. Guide to Appendices" / "Appendix B. Typical Appendix Contents" | Delete before the real References and Appendices | H |
| R-37 | Table of Contents | Lists both the template and the real References/Appendices; page numbers will move after the edits | Regenerate the TOC and add a List of Tables and List of Figures | L |
| R-38 | Appendices | Only the work schedule and a sample questionnaire | Add: respondent data (anonymised) and α; GIS technical annex (`make annex`); cleaning/audit logs; permission and consent forms; the field-verification forms | M |

## F. Summary of what the students must supply before these edits can be finished
Origin and dates of the shoreline lines (Q-G1–G4); respondent-level survey data and pilot results (Q-S1–S2); a decision on Ho1/Objective 3 (Q-S4); field verification results (if any); confirmation of every item marked [VERIFY CITATION].
