"""Phase 7 tests - every statistic checked against a hand computation; all survey data here are SYNTHETIC."""
import numpy as np
import pandas as pd
import pytest

from aparri import stats_survey as SS
from aparri.io import load_config
from tests.fixtures.make_synthetic_survey import synthetic_table_4_4, synthetic_with_risk_levels


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def syn(cfg):
    return synthetic_table_4_4(cfg)


def test_cronbach_alpha_hand_value():
    # items X=[1,2,3], Y=[2,4,6], Z=[3,6,9]: total=[6,12,18] var=36 ; item vars 1+4+9=14
    # alpha = 3/2 * (1 - 14/36) = 0.916666...
    items = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 6], "z": [3, 6, 9]})
    r = SS.cronbach_alpha(items)
    assert abs(r["alpha"] - 0.9166666667) < 1e-9 and r["k"] == 3 and r["n"] == 3


def test_cronbach_alpha_zero_covariance_is_zero():
    items = pd.DataFrame({"a": [1, 2, 1, 2], "b": [1, 1, 2, 2], "c": [1, 2, 2, 1]})   # pairwise uncorrelated
    assert abs(SS.cronbach_alpha(items)["alpha"]) < 1e-9


def test_weighted_mean_equals_sum_fx_over_n():
    x = np.array([5, 5, 4, 3])                 # f(5)=2 f(4)=1 f(3)=1 -> (10+4+3... ) = (2*5+4+3)/4 = 4.25
    assert abs(SS.weighted_mean(x) - 4.25) < 1e-12


def test_interpretation_bands(cfg):
    b = cfg["survey"]["interpretation"]
    assert [SS.interpretation(v, b) for v in (4.21, 4.20, 3.41, 3.40, 2.61, 2.60, 1.81, 1.80, 1.0)] == \
        ["Very High", "High", "High", "Moderate", "Moderate", "Low", "Low", "Very Low", "Very Low"]


def test_friedman_hand_value(cfg):
    # 3 respondents all rank A>B>C -> ranks sums 9,6,3 ; chi2 = 12/(N k (k+1)) * sum R^2 - 3 N (k+1) = 6 ; W = 1
    S = ["Seawall", "Revetment", "Riprap"]
    cfg2 = {**cfg, "survey": {**cfg["survey"], "structures": S}}
    rows = []
    for rid in "abc":
        for s, v in zip(S, (5, 4, 2)):
            rows.append({"respondent_id": rid, "structure": s, "criterion": "Stability", "score": v, "risk_level": ""})
    r = SS.friedman_among_structures(pd.DataFrame(rows), cfg2)
    assert abs(r["statistic"] - 6.0) < 1e-9 and abs(r["kendall_W"] - 1.0) < 1e-9 and r["df"] == 2


def test_reproduces_published_table_4_4_from_synthetic_respondents(cfg, syn):
    t = SS.decision_matrix(syn, cfg)
    diff = SS.diff_vs_published(t)
    assert not diff.mismatch.any(), diff[diff.mismatch]
    odd = diff[diff.beyond_4dp_rounding]
    assert len(odd) == 1 and odd.iloc[0].structure == "Breakwater" and odd.iloc[0].column == "Effectiveness"      # manuscript: 3.8149, exact 206/54 = 3.8148
    assert t.loc["Seawall", "Rank"] == 1 and t.loc["Mangrove Rehabilitation", "Rank"] == 2 and t.loc["Riprap", "Rank"] == 5
    assert t.loc["Seawall", "Interpretation"] == "Very High" and t.loc["Mangrove Rehabilitation", "Interpretation"] == "High"


def test_mismatch_is_reported_when_data_differ(cfg, syn):
    d = syn.copy()
    idx = d[(d.structure == "Seawall") & (d.criterion == "Stability")].index[:5]
    d.loc[idx, "score"] = 1
    diff = SS.diff_vs_published(SS.decision_matrix(d, cfg))
    assert diff[(diff.structure == "Seawall") & (diff.column == "Stability")].mismatch.iloc[0]


def test_profile_tables_match_manuscript_counts(syn):
    p = SS.profile_tables(syn)
    assert p["profession"].Frequency.tolist() == [21, 18, 12, 1, 2] and p["years_experience"].Frequency.tolist() == [29, 16, 6, 3]
    assert p["worked_on_structure"].Frequency.tolist() == [15, 39] and p["trained"].Frequency.tolist() == [21, 33]
    assert abs(p["profession"].Percentage.iloc[0] - 38.9) < 0.05 and p["n"].respondents.iloc[0] == 54


def test_validator_explains_problems(cfg, syn):
    d = syn.copy()
    d.loc[3, "score"] = 7
    d.loc[5, "structure"] = "Dike"
    d = pd.concat([d, d.iloc[[10]]], ignore_index=True)           # duplicate row
    msgs = " ".join(i.message for i in SS.validate(d, cfg))
    assert "outside the 1-5" in msgs and "'Dike' is not one of" in msgs and "duplicate row" in msgs
    assert SS.validate(syn, cfg) == []


def test_template_and_wide_roundtrip(cfg):
    w = SS.template_wide(cfg)
    assert w.shape[1] == 6 + 30
    row = {"respondent_id": "r1", "profession": SS.PROFESSIONS[0], "years_experience": SS.EXPERIENCE[1], "worked_on_structure": "Yes",
           "familiar_with_structures": "Yes", "trained": "No"}
    for s in cfg["survey"]["structures"]:
        for c in cfg["survey"]["criteria"]:
            row[f"{s} | {c}"] = 4
    long = SS.wide_to_long(pd.DataFrame([row]), cfg)
    assert len(long) == 30 and SS.validate(long, cfg) == []


def test_ho1_not_testable_without_risk_levels(cfg, syn):
    r = SS.compare_risk_levels(syn, cfg)
    assert r["status"] == "NOT_TESTABLE" and "cannot be tested" in r["message"] and "Friedman" in r["message"]


def test_ho1_testable_between_and_within(cfg):
    b = SS.compare_risk_levels(synthetic_with_risk_levels(cfg, n=45, within=False), cfg)
    assert b["status"] == "TESTED" and 0 <= b["p"] <= 1 and "between-subject" in b["design"] and "effect_size" in b
    w = SS.compare_risk_levels(synthetic_with_risk_levels(cfg, n=30, within=True), cfg)
    assert w["status"] == "TESTED" and "Friedman" in w["test"] and w["df"] == 2 and "Kendall" in w["effect_size"]


def test_ranking_by_risk_level(cfg):
    r = SS.ranking_by_risk(synthetic_with_risk_levels(cfg, n=30, within=True), cfg)
    assert set(r) == {"Low", "Medium", "High"} and set(r["Low"].Rank.dropna()) <= set(range(1, 6))


def test_refuses_to_publish_synthetic_into_outputs():
    with pytest.raises(PermissionError):
        SS.assert_publishable(True, "outputs/tables")
    SS.assert_publishable(True, "/tmp/somewhere")           # allowed outside outputs/
    SS.assert_publishable(False, "outputs/tables")          # real data allowed


def test_reliability_runs_per_structure_and_overall(cfg, syn):
    r = SS.reliability(syn, cfg)
    assert len(r) == 6 and r.iloc[-1].scope.startswith("ALL 30")


def test_weight_sensitivity_on_published_means():
    r = SS.weight_sensitivity(SS.PUBLISHED_4_4.drop(columns="Overall"), n_draws=4000, seed=1)
    eq = r["named"].iloc[0]
    assert eq["ranking (best first)"].startswith("Seawall > Mangrove Rehabilitation > Revetment > Breakwater > Riprap")
    assert r["p_first"]["Seawall"] > 0.9 and abs(sum(r["p_first"].values()) - 1) < 1e-9
    assert r["named"].iloc[5]["ranking (best first)"].startswith("Mangrove Rehabilitation")     # cost + environment only
