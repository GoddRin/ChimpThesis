"""SYNTHETIC survey data for TESTS ONLY (CLAUDE.md rule 2). Never used for results.

``synthetic_table_4_4(cfg)`` builds 54 FAKE respondents whose cell sums reproduce the manuscript's Table 4.4 means
exactly (mean x 54 is a whole number), so the pipeline can be tested end-to-end.  Every row has
``data_origin == "SYNTHETIC"``; the module that analyses surveys refuses to write such data into outputs/.
"""
import numpy as np
import pandas as pd

from aparri.stats_survey import EXPERIENCE, LONG_COLS, PROFESSIONS, PUBLISHED_4_4, YESNO


def _scores_with_sum(total: int, n: int, rng) -> np.ndarray:
    """n integers in 1..5 with the given sum, as even as possible, shuffled."""
    base = np.full(n, total // n)
    base[: total - base.sum()] += 1
    rng.shuffle(base)
    return np.clip(base, 1, 5)


def synthetic_table_4_4(cfg: dict, n: int = 54, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    prof = np.repeat(PROFESSIONS, [21, 18, 12, 1, 2]); exp = np.repeat(EXPERIENCE, [29, 16, 6, 3])
    worked = np.repeat(YESNO, [15, 39]); fam = np.repeat(YESNO, [49, 5]); tr = np.repeat(YESNO, [21, 33])
    for a in (prof, exp, worked, fam, tr):
        rng.shuffle(a)
    rows = []
    for s in cfg["survey"]["structures"]:
        for c in cfg["survey"]["criteria"]:
            target = PUBLISHED_4_4.loc[s, c]
            total = int(round(target * n))
            assert abs(total / n - target) < 1e-4, (s, c, total / n, target)   # manuscript's Breakwater/Effectiveness 3.8149 is 206/54 = 3.8148 (1e-4 rounding slip)
            sc = _scores_with_sum(total, n, rng)
            for i in range(n):
                rows.append({"respondent_id": f"SYN{i+1:03d}", "profession": prof[i], "years_experience": exp[i], "worked_on_structure": worked[i],
                             "familiar_with_structures": fam[i], "trained": tr[i], "structure": s, "risk_level": "", "criterion": c,
                             "score": int(sc[i]), "data_origin": "SYNTHETIC"})
    return pd.DataFrame(rows, columns=LONG_COLS)


def synthetic_with_risk_levels(cfg: dict, n: int = 30, seed: int = 3, within: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    levels = ["Low", "Medium", "High"]
    for i in range(n):
        lv_choices = levels if within else [levels[i % 3]]
        for lv in lv_choices:
            for s in cfg["survey"]["structures"]:
                for c in cfg["survey"]["criteria"]:
                    shift = {"Low": -0.3, "Medium": 0.0, "High": 0.4}[lv]
                    sc = int(np.clip(round(rng.normal(3.6 + shift, 0.8)), 1, 5))
                    rows.append({"respondent_id": f"SYN{i+1:03d}", "profession": PROFESSIONS[i % 5], "years_experience": EXPERIENCE[i % 4], "worked_on_structure": "No",
                                 "familiar_with_structures": "Yes", "trained": "No", "structure": s, "risk_level": lv, "criterion": c, "score": sc, "data_origin": "SYNTHETIC"})
    return pd.DataFrame(rows, columns=LONG_COLS)
