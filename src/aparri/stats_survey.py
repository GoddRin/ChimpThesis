"""Phase 7: expert-survey statistics (Likert ratings, weighted mean, ranking, reliability, hypothesis tests).

STATUS: tooling only.  No respondent-level data were supplied, so **nothing in ``outputs/`` was produced from
survey data**.  When the students put their responses in ``data/raw/survey/survey_responses.csv`` (format in
``docs/survey_schema.md``) ``make survey`` validates them, reproduces Table 4.4, compares it with the published
numbers and writes the tables.  Synthetic data (``data_origin == SYNTHETIC``) can be analysed in memory for testing
but this module refuses to write it into ``outputs/``.

Thesis design (Ch. III): 54 expert respondents rate 5 structures (Seawall, Revetment, Riprap, Breakwater, Mangrove
Rehabilitation) on 6 criteria (Stability, Effectiveness, Cost, Durability, Maintenance, Environmental Impact) with
a 5-point Likert scale; weighted mean x = sum(f x)/N; Cronbach's alpha with threshold 0.70; interpretation bands
4.21-5.00 Very High, 3.41-4.20 High, 2.61-3.40 Moderate, 1.81-2.60 Low, 1.00-1.80 Very Low.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from .io import REPO_ROOT, ensure_dir, load_config, repo_path
from .runreport import RunReport

PROFILE_COLS = ["profession", "years_experience", "worked_on_structure", "familiar_with_structures", "trained"]
LONG_COLS = ["respondent_id", *PROFILE_COLS, "structure", "risk_level", "criterion", "score", "data_origin"]
PROFESSIONS = ["Civil Engineer", "DPWH Engineer", "Coastal/Environmental Engineer", "Contractor", "LGU Technical Personnel"]
EXPERIENCE = ["Less than 5 years", "5-10 years", "11-20 years", "More than 20 years"]
RISK_LEVELS = ["Low", "Medium", "High"]
YESNO = ["Yes", "No"]

# Table 4.4 as printed in the manuscript (Chapter IV, p. 66) - used only to CHECK real data against it
PUBLISHED_4_4 = pd.DataFrame(
    [[4.5370, 4.5741, 4.2778, 4.2037, 4.2963, 4.2037, 4.3488],
     [4.2593, 4.1296, 3.9074, 3.7593, 4.0000, 3.8704, 3.9877],
     [3.8148, 3.5741, 3.5741, 3.3704, 3.8148, 3.6111, 3.6265],
     [3.8519, 3.8149, 3.6667, 3.4630, 3.7963, 3.6481, 3.7068],
     [4.0185, 4.1667, 4.3519, 3.8889, 3.9074, 4.4815, 4.1358]],
    index=["Seawall", "Revetment", "Riprap", "Breakwater", "Mangrove Rehabilitation"],
    columns=["Stability", "Effectiveness", "Cost", "Durability", "Maintenance", "Environmental Impact", "Overall"])


# --------------------------------------------------------------------------- schema, templates, validation
@dataclass
class Issue:
    row: int | None
    field: str
    message: str


def template_long(cfg: dict) -> pd.DataFrame:
    """A blank, correctly shaped long-format table with ONE example respondent clearly marked as an example."""
    S, C = cfg["survey"]["structures"], cfg["survey"]["criteria"]
    rows = []
    for s in S:
        for c in C:
            rows.append({"respondent_id": "EXAMPLE-DELETE-ME", "profession": PROFESSIONS[0], "years_experience": EXPERIENCE[0], "worked_on_structure": "No",
                         "familiar_with_structures": "Yes", "trained": "No", "structure": s, "risk_level": "", "criterion": c, "score": "", "data_origin": "REAL"})
    return pd.DataFrame(rows, columns=LONG_COLS)


def template_wide(cfg: dict) -> pd.DataFrame:
    """One row per respondent: easier to type from the questionnaires or a Google-Forms export."""
    S, C = cfg["survey"]["structures"], cfg["survey"]["criteria"]
    cols = ["respondent_id", *PROFILE_COLS] + [f"{s} | {c}" for s in S for c in C]
    return pd.DataFrame(columns=cols)


def wide_to_long(w: pd.DataFrame, cfg: dict, data_origin: str = "REAL") -> pd.DataFrame:
    S, C = cfg["survey"]["structures"], cfg["survey"]["criteria"]
    rows = []
    for _, r in w.iterrows():
        for s in S:
            for c in C:
                col = f"{s} | {c}"
                if col in w.columns and pd.notna(r[col]) and str(r[col]).strip() != "":
                    rows.append({"respondent_id": r["respondent_id"], **{k: r[k] for k in PROFILE_COLS}, "structure": s, "risk_level": "",
                                 "criterion": c, "score": r[col], "data_origin": data_origin})
    return pd.DataFrame(rows, columns=LONG_COLS)


def validate(df: pd.DataFrame, cfg: dict) -> list[Issue]:
    """Plain-English problems found in a long-format response table (row numbers are spreadsheet rows, header = row 1)."""
    S, C = cfg["survey"]["structures"], cfg["survey"]["criteria"]
    out: list[Issue] = []
    miss = [c for c in LONG_COLS if c not in df.columns]
    if miss:
        return [Issue(None, ",".join(miss), "These columns are missing: " + ", ".join(miss) + ". Use data/templates/survey_responses_template.csv as a starting point.")]
    for i, r in df.iterrows():
        row = i + 2
        sc = pd.to_numeric(r["score"], errors="coerce")
        if pd.isna(sc):
            out.append(Issue(row, "score", f"score '{r['score']}' is empty or not a number; the scale is 1 to 5."))
        elif sc != int(sc) or not (1 <= sc <= 5):
            out.append(Issue(row, "score", f"score {r['score']} is outside the 1-5 whole-number scale."))
        if r["structure"] not in S:
            out.append(Issue(row, "structure", f"structure '{r['structure']}' is not one of: {', '.join(S)}."))
        if r["criterion"] not in C:
            out.append(Issue(row, "criterion", f"criterion '{r['criterion']}' is not one of: {', '.join(C)}."))
        rl = r["risk_level"]
        if isinstance(rl, str) and rl.strip() not in ("", "NA") and rl not in RISK_LEVELS:
            out.append(Issue(row, "risk_level", f"risk_level '{rl}' must be Low, Medium, High or left empty."))
        if r["profession"] not in PROFESSIONS:
            out.append(Issue(row, "profession", f"profession '{r['profession']}' is not one of the questionnaire options: {', '.join(PROFESSIONS)}."))
        if r["years_experience"] not in EXPERIENCE:
            out.append(Issue(row, "years_experience", f"years_experience '{r['years_experience']}' is not one of: {', '.join(EXPERIENCE)}."))
        for f in ("worked_on_structure", "familiar_with_structures", "trained"):
            if r[f] not in YESNO:
                out.append(Issue(row, f, f"{f} must be Yes or No (found '{r[f]}')."))
        if r["data_origin"] not in ("REAL", "SYNTHETIC"):
            out.append(Issue(row, "data_origin", "data_origin must be REAL or SYNTHETIC."))
    key = ["respondent_id", "structure", "risk_level", "criterion"]
    d = df.copy(); d["risk_level"] = d["risk_level"].fillna("").astype(str)
    dup = d[d.duplicated(key, keep=False)]
    for i in dup.index:
        out.append(Issue(i + 2, "duplicate", "this respondent already has a score for the same structure/criterion/risk level (duplicate row)."))
    # profile must be constant within a respondent
    for rid, g in df.groupby("respondent_id"):
        for f in PROFILE_COLS:
            if g[f].nunique() > 1:
                out.append(Issue(int(g.index[0]) + 2, f, f"respondent {rid} has more than one value of {f}: {sorted(g[f].astype(str).unique())}."))
    return out


def explain(issues: list[Issue]) -> str:
    if not issues:
        return "No problems found."
    lines = [f"{len(issues)} problem(s) found:"]
    lines += [f"  row {i.row}: {i.message}" if i.row else f"  {i.message}" for i in issues[:60]]
    if len(issues) > 60:
        lines.append(f"  ... and {len(issues) - 60} more.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- statistics
def interpretation(x: float, bands: list) -> str:
    for lo, lab in bands:
        if x >= lo - 1e-12:
            return lab
    return bands[-1][1]


def weighted_mean(scores: np.ndarray) -> float:
    """x = sum(f * x) / N where f = frequency of each scale value; identical to the arithmetic mean."""
    scores = np.asarray(scores, float)
    vals, f = np.unique(scores, return_counts=True)
    return float((f * vals).sum() / f.sum())


def decision_matrix(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Structure x criterion weighted means, overall mean (= simple average of the criterion means, equal weights as in
    the thesis), interpretation label and rank (1 = highest)."""
    S, C = cfg["survey"]["structures"], cfg["survey"]["criteria"]
    bands = cfg["survey"]["interpretation"]
    t = pd.DataFrame(index=S, columns=C, dtype=float)
    for s in S:
        for c in C:
            x = df[(df.structure == s) & (df.criterion == c)].score.astype(float)
            t.loc[s, c] = weighted_mean(x.values) if len(x) else np.nan
    t["Overall"] = t[C].mean(axis=1)
    t["Interpretation"] = [interpretation(v, bands) if pd.notna(v) else "" for v in t["Overall"]]
    t["Rank"] = t["Overall"].rank(ascending=False, method="min").astype("Int64")
    return t


def cronbach_alpha(items: pd.DataFrame) -> dict:
    """alpha = k/(k-1) * (1 - sum(item variances) / variance(total score)), sample variances (ddof = 1).

    ``items`` has one row per respondent and one column per item; incomplete rows are dropped (listwise)."""
    x = items.dropna().astype(float)
    k = x.shape[1]
    n = x.shape[0]
    if k < 2 or n < 3:
        return {"alpha": np.nan, "k": k, "n": n, "note": "need >= 2 items and >= 3 complete respondents"}
    iv = x.var(axis=0, ddof=1).sum()
    tv = x.sum(axis=1).var(ddof=1)
    if tv == 0:
        return {"alpha": np.nan, "k": k, "n": n, "note": "total score has no variance"}
    return {"alpha": float(k / (k - 1) * (1 - iv / tv)), "k": k, "n": n, "note": ""}


def reliability(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    S, C = cfg["survey"]["structures"], cfg["survey"]["criteria"]
    rows = []
    d = df[df.risk_level.fillna("").isin(["", "NA"])] if "risk_level" in df else df
    for s in S:
        w = d[d.structure == s].pivot_table(index="respondent_id", columns="criterion", values="score", aggfunc="first")[[c for c in C if c in d.criterion.unique()]]
        r = cronbach_alpha(w); rows.append({"scope": s, **r})
    wide = d.assign(item=d.structure + " | " + d.criterion).pivot_table(index="respondent_id", columns="item", values="score", aggfunc="first")
    r = cronbach_alpha(wide); rows.append({"scope": f"ALL {wide.shape[1]} items", **r})
    out = pd.DataFrame(rows)
    out["meets_threshold"] = out["alpha"] >= cfg["survey"]["alpha_min"]
    return out


def profile_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    r = df.drop_duplicates("respondent_id")
    n = len(r)
    def tab(col, order):
        c = r[col].value_counts().reindex(order, fill_value=0)
        return pd.DataFrame({"Frequency": c, "Percentage": (c / n * 100).round(1)}).rename_axis(col).reset_index()
    return {"profession": tab("profession", PROFESSIONS), "years_experience": tab("years_experience", EXPERIENCE),
            "worked_on_structure": tab("worked_on_structure", YESNO), "familiar_with_structures": tab("familiar_with_structures", YESNO),
            "trained": tab("trained", YESNO), "n": pd.DataFrame({"respondents": [n]})}


def diff_vs_published(t: pd.DataFrame, tol: float = 0.00051) -> pd.DataFrame:
    """Cell-by-cell difference of the reproduced Table 4.4 and the manuscript's; lists every cell beyond rounding."""
    rows = []
    for s in PUBLISHED_4_4.index:
        for c in PUBLISHED_4_4.columns:
            a, b = t.loc[s, c] if s in t.index else np.nan, PUBLISHED_4_4.loc[s, c]
            rows.append({"structure": s, "column": c, "reproduced": a, "published": b, "difference": a - b, "mismatch": bool(pd.isna(a) or abs(a - b) > tol),
                         "beyond_4dp_rounding": bool(pd.notna(a) and abs(a - b) > 5e-5)})
    return pd.DataFrame(rows)


def weight_sensitivity(means: pd.DataFrame, n_draws: int = 20000, seed: int = 1) -> dict:
    """How stable is the ranking if the six criteria are not weighted equally?

    ``means`` = structure x criterion weighted means (columns = the six criteria only).  Named scenarios plus
    ``n_draws`` random weight vectors (Dirichlet(1,...,1): every weighting equally likely).  Works on the
    PUBLISHED means too, since it needs no respondent data."""
    C = [c for c in means.columns if c not in ("Overall", "Interpretation", "Rank")]
    M = means[C].astype(float).values
    S = list(means.index)
    base_rank = pd.Series((M.mean(axis=1))).rank(ascending=False, method="min").astype(int).tolist()
    def ranks(w):
        sc = M @ w
        return pd.Series(sc).rank(ascending=False, method="min").astype(int).tolist()
    named = {
        "equal weights (thesis)": np.ones(len(C)),
        "cost counts double": np.array([2.0 if c == "Cost" else 1.0 for c in C]),
        "environmental impact counts double": np.array([2.0 if c == "Environmental Impact" else 1.0 for c in C]),
        "stability + durability count double": np.array([2.0 if c in ("Stability", "Durability") else 1.0 for c in C]),
        "engineering only (no cost, no environment)": np.array([0.0 if c in ("Cost", "Environmental Impact") else 1.0 for c in C]),
        "cost + environment only": np.array([1.0 if c in ("Cost", "Environmental Impact") else 0.0 for c in C]),
    }
    rows = []
    for name, w in named.items():
        w = w / w.sum(); sc = M @ w
        rows.append({"scenario": name, **{S[i]: round(float(sc[i]), 4) for i in range(len(S))}, "ranking (best first)": " > ".join(np.array(S)[np.argsort(-sc)])})
    rng = np.random.default_rng(seed)
    W = rng.dirichlet(np.ones(len(C)), size=n_draws)
    sc = W @ M.T
    first = np.bincount(sc.argmax(axis=1), minlength=len(S)) / n_draws
    same = np.mean([ranks(w) == base_rank for w in W[:2000]])
    return {"named": pd.DataFrame(rows), "p_first": dict(zip(S, first.round(3))), "p_same_full_ranking": float(same), "n_draws": n_draws}


def ranking_by_risk(df: pd.DataFrame, cfg: dict) -> dict[str, pd.DataFrame] | None:
    """Decision matrix per risk level - only if the data HAVE a risk_level dimension."""
    rl = df.risk_level.fillna("").astype(str)
    levels = [x for x in RISK_LEVELS if (rl == x).any()]
    if not levels:
        return None
    return {lv: decision_matrix(df[rl == lv], cfg) for lv in levels}


def design_check(df: pd.DataFrame) -> dict:
    """Can Ho1 ('perceived efficiency/feasibility differ across erosion-risk levels') be tested with this data?"""
    rl = df.risk_level.fillna("").astype(str)
    has = rl.isin(RISK_LEVELS).any()
    if not has:
        return {"testable": False, "design": "no risk_level dimension",
                "message": "Every respondent rated each structure once, with no mention of a risk level. Ho1/Ha1 as written (difference ACROSS risk levels) "
                           "cannot be tested with these data. Options: (A) add a per-risk-level section to the questionnaire and re-survey; (B) re-word the hypothesis "
                           "to 'perceived suitability differs AMONG the five structures' and test it with a Friedman test + Wilcoxon post-hoc (Holm); "
                           "(C) keep Ho1 as a qualitative design principle and drop the test."}
    per = df[rl.isin(RISK_LEVELS)].groupby("respondent_id").risk_level.nunique()
    within = bool((per > 1).any())
    return {"testable": True, "design": "within-subject (each respondent rated several risk levels)" if within else "between-subject (each respondent rated one level)",
            "within": within, "message": "risk_level dimension present."}


def holm(p: np.ndarray) -> np.ndarray:
    from statsmodels.stats.multitest import multipletests
    return multipletests(p, method="holm")[1]


def friedman_among_structures(df: pd.DataFrame, cfg: dict) -> dict:
    """Respondent-level overall score per structure (mean of that respondent's criterion scores) -> Friedman test
    (non-parametric repeated measures) + Kendall's W + pairwise Wilcoxon signed-rank with Holm correction."""
    S = cfg["survey"]["structures"]
    d = df[df.risk_level.fillna("").isin(["", "NA"])]
    m = d.groupby(["respondent_id", "structure"]).score.mean().unstack()[S].dropna()
    N, k = m.shape
    chi2, p = stats.friedmanchisquare(*[m[s].values for s in S])
    W = chi2 / (N * (k - 1))
    pairs, pv, stat, rbc = [], [], [], []
    for a in range(k):
        for b in range(a + 1, k):
            x, y = m[S[a]].values, m[S[b]].values
            try:
                w = stats.wilcoxon(x, y, zero_method="wilcox")
                pv.append(w.pvalue); stat.append(w.statistic)
            except ValueError:
                pv.append(1.0); stat.append(np.nan)
            diff = x - y
            nz = diff[diff != 0]
            rbc.append(float((np.sign(nz) * stats.rankdata(np.abs(nz))).sum() / (len(nz) * (len(nz) + 1) / 2)) if len(nz) else 0.0)
            pairs.append(f"{S[a]} vs {S[b]}")
    post = pd.DataFrame({"pair": pairs, "wilcoxon_W": stat, "p_raw": pv, "p_holm": holm(np.array(pv)), "rank_biserial": rbc})
    return {"test": "Friedman chi-square", "N": N, "k": k, "df": k - 1, "statistic": float(chi2), "p": float(p), "kendall_W": float(W), "post_hoc": post,
            "mean_ranks": m.rank(axis=1, ascending=False).mean().round(3).to_dict()}


def compare_risk_levels(df: pd.DataFrame, cfg: dict) -> dict:
    """Ho1 proper, only if the design allows it.  Prints the exact test, statistic, df, p and effect size."""
    chk = design_check(df)
    if not chk["testable"]:
        return {"status": "NOT_TESTABLE", **chk}
    d = df[df.risk_level.isin(RISK_LEVELS)]
    sc = d.groupby(["respondent_id", "risk_level"]).score.mean().unstack()
    alpha = cfg["survey"]["significance_level"]
    if chk["within"]:
        m = sc.dropna(axis=0)
        cols = [c for c in RISK_LEVELS if c in m.columns]
        chi2, p = stats.friedmanchisquare(*[m[c].values for c in cols])
        N, k = m.shape[0], len(cols)
        return {"status": "TESTED", "test": "Friedman chi-square (within-subject)", "N": N, "df": k - 1, "statistic": float(chi2), "p": float(p),
                "effect_size": f"Kendall W = {chi2 / (N * (k - 1)):.3f}", "reject_H0": bool(p < alpha), **chk}
    groups = [sc[c].dropna().values for c in RISK_LEVELS if c in sc.columns]
    sw = [stats.shapiro(g).pvalue for g in groups if len(g) >= 3]
    lev = stats.levene(*groups).pvalue
    normal = all(x > 0.05 for x in sw) and lev > 0.05
    if normal:
        F, p = stats.f_oneway(*groups)
        n_all = sum(len(g) for g in groups); k = len(groups)
        gm = np.concatenate(groups).mean()
        ssb = sum(len(g) * (g.mean() - gm) ** 2 for g in groups); sst = sum(((g - gm) ** 2).sum() for g in groups)
        return {"status": "TESTED", "test": "one-way ANOVA (Shapiro and Levene passed)", "df": (k - 1, n_all - k), "statistic": float(F), "p": float(p),
                "effect_size": f"eta^2 = {ssb / sst:.3f}", "reject_H0": bool(p < alpha), **chk}
    H, p = stats.kruskal(*groups)
    n_all = sum(len(g) for g in groups); k = len(groups)
    eps2 = (H - k + 1) / (n_all - k) if n_all > k else np.nan
    allv = np.concatenate(groups); ranks = stats.rankdata(allv)
    pos = np.cumsum([0] + [len(g) for g in groups]); mean_r = [ranks[pos[i]:pos[i + 1]].mean() for i in range(k)]
    tie = stats.tiecorrect(ranks)
    names = [c for c in RISK_LEVELS if c in sc.columns]
    pairs, zs, ps = [], [], []
    for a in range(k):
        for b in range(a + 1, k):
            se = np.sqrt(n_all * (n_all + 1) / 12 * (1 / len(groups[a]) + 1 / len(groups[b])) * tie)
            z = (mean_r[a] - mean_r[b]) / se
            zs.append(z); ps.append(2 * (1 - stats.norm.cdf(abs(z)))); pairs.append(f"{names[a]} vs {names[b]}")
    dunn = pd.DataFrame({"pair": pairs, "z": zs, "p_raw": ps, "p_holm": holm(np.array(ps))})
    return {"status": "TESTED", "test": "Kruskal-Wallis (normality/homogeneity not met)", "df": k - 1, "statistic": float(H), "p": float(p),
            "effect_size": f"epsilon^2 = {eps2:.3f}", "reject_H0": bool(p < alpha), "dunn_holm": dunn, **chk}


# --------------------------------------------------------------------------- loading and refusing to publish synthetic data
def load_responses(path) -> tuple[pd.DataFrame, bool]:
    df = pd.read_csv(path, comment="#", dtype=str, keep_default_na=False)
    synthetic = bool((df.get("data_origin", pd.Series(dtype=str)) == "SYNTHETIC").any())
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    return df, synthetic


def assert_publishable(is_synthetic: bool, out_dir) -> None:
    """Hard rule (CLAUDE.md #2): synthetic data never reach outputs/."""
    p = repo_path(out_dir).resolve()
    if is_synthetic and (REPO_ROOT / "outputs") in [p, *p.parents]:
        raise PermissionError("SYNTHETIC survey data must never be written to outputs/ (CLAUDE.md rule 2)")


def analyse(df: pd.DataFrame, cfg: dict) -> dict:
    t = decision_matrix(df, cfg)
    res = {"table_4_4": t, "reliability": reliability(df, cfg), "profile": profile_tables(df), "diff": diff_vs_published(t),
           "design": design_check(df), "ho1": compare_risk_levels(df, cfg), "by_risk": ranking_by_risk(df, cfg)}
    try:
        res["friedman"] = friedman_among_structures(df, cfg)
    except Exception as e:  # pragma: no cover
        res["friedman"] = {"error": str(e)}
    return res


def run() -> None:  # pragma: no cover
    cfg = load_config()
    rep = RunReport("survey", cfg)
    tdir = ensure_dir("data/templates")
    template_long(cfg).to_csv(tdir / "survey_responses_template.csv", index=False)
    template_wide(cfg).to_csv(tdir / "survey_responses_template_wide.csv", index=False)
    PUBLISHED_4_4.round(4).to_csv(tdir / "published_table_4_4_manuscript.csv")
    # Uses ONLY the manuscript's published means (the students' own numbers), no respondent data needed
    ws = weight_sensitivity(PUBLISHED_4_4.drop(columns="Overall"))
    ws["named"].to_csv(ensure_dir("outputs/tables") / "survey_ranking_weight_sensitivity_PUBLISHED_means.csv", index=False)
    pd.DataFrame({"structure": list(ws["p_first"]), "share_of_random_weightings_ranked_first": list(ws["p_first"].values())}).to_csv(
        ensure_dir("outputs/tables") / "survey_ranking_first_probability_PUBLISHED_means.csv", index=False)
    src = repo_path("data/raw/survey/survey_responses.csv")
    if not src.exists():
        msg = ("No respondent-level survey data found at data/raw/survey/survey_responses.csv - no respondent-level analysis was produced (only the weight-sensitivity of the PUBLISHED means was written). "
               "Fill data/templates/survey_responses_template(_wide).csv (see docs/survey_schema.md) and rerun `make survey`.")
        rep.warn(msg); rep.write(); print(msg)
        return
    df, synth = load_responses(src)
    rep.add_input(src)
    issues = validate(df, cfg)
    print(explain(issues))
    if issues:
        rep.warn(f"{len(issues)} validation problem(s); fix them before analysing")
        rep.write(); return
    out = ensure_dir("outputs/tables")
    assert_publishable(synth, out)
    res = analyse(df, cfg)
    res["table_4_4"].round(4).to_csv(out / "survey_table_4_4_reproduced.csv")
    res["diff"].round(4).to_csv(out / "survey_table_4_4_vs_published.csv", index=False)
    res["reliability"].round(4).to_csv(out / "survey_cronbach_alpha.csv", index=False)
    for k, v in res["profile"].items():
        v.to_csv(out / f"survey_profile_{k}.csv", index=False)
    if res["by_risk"]:
        for lv, t in res["by_risk"].items():
            t.round(4).to_csv(out / f"survey_decision_matrix_{lv}.csv")
    if "post_hoc" in res.get("friedman", {}):
        res["friedman"]["post_hoc"].round(4).to_csv(out / "survey_friedman_posthoc.csv", index=False)
    rep.count("mismatches_vs_published", int(res["diff"].mismatch.sum()))
    print(res["table_4_4"].round(4).to_string()); print(res["reliability"].round(3).to_string())
    print("Ho1:", {k: v for k, v in res["ho1"].items() if k not in ("dunn_holm",)})
    rep.write()


if __name__ == "__main__":  # pragma: no cover
    run()
