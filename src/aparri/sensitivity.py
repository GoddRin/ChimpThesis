"""Phase 6: sensitivity, validation and robustness.

Question answered: "which of our conclusions would change if we had made a different (equally reasonable) choice?"
Everything is recomputed in memory with the same engine (``transects.compute``) and summarised; nothing here
changes the main results.  Output: ``outputs/tables/sensitivity_*.csv``, ``outputs/maps/Fig_6_*.png``,
``outputs/field_validation/``, ``docs/05_sensitivity_validation.md``.
"""
from __future__ import annotations

import copy
import itertools

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.ops import unary_union

from . import metrics as M
from .io import REPO_ROOT, ensure_dir, load_config, read_vector, repo_path
from .risk import CLASSES, classify
from .runreport import RunReport
from .transects import SET_FILES, available_sets, compute, load_parts


def class_shares(tr: pd.DataFrame, cfg: dict, field: str = "EPR_m_yr") -> dict:
    v = tr[tr.valid_epr & tr[field].notna()]
    c = classify(v[field].values, cfg["risk"]["low_max"], cfg["risk"]["medium_max"], cfg["risk"]["accretion_class"])
    n = max(len(v), 1)
    return {"n_valid": len(v), **{f"pct_{k}": float((c == k).sum() / n * 100) for k in CLASSES}}


def barangay_class(tr: pd.DataFrame, cfg: dict, field: str = "EPR_m_yr") -> pd.DataFrame:
    rows = []
    for b in cfg["table_4_2_order"]:
        t = tr[(tr.barangay == b) & tr.valid_epr & tr[field].notna()]
        if len(t) == 0:
            rows.append({"barangay": b, "n": 0, "dominant": "no data", "worst": "no data", "mean": np.nan}); continue
        c = classify(t[field].values, cfg["risk"]["low_max"], cfg["risk"]["medium_max"], cfg["risk"]["accretion_class"])
        share = {k: float((c == k).mean()) for k in CLASSES}
        dom = max(CLASSES, key=lambda k: (share[k], CLASSES.index(k)))
        worst = "High" if share["High"] >= 0.10 else ("Medium" if share["Medium"] >= 0.10 else "Low")
        rows.append({"barangay": b, "n": len(t), "dominant": dom, "worst": worst, "mean": float(t[field].mean())})
    return pd.DataFrame(rows)


def scenarios(cfg: dict) -> list[tuple[str, str, dict]]:
    """(id, description, config overrides) - one-at-a-time changes around the base run."""
    out = [("base", "base run", {})]
    for sp in (25, 100):
        out.append((f"spacing_{sp}", f"transect spacing {sp} m", {"transects": {"spacing_m": sp}}))
    for sm in (100, 400):
        out.append((f"smooth_{sm}", f"baseline smoothing {sm} m", {"baseline": {"smooth_m": sm}}))
    out.append(("multihit_farthest", "multi-hit rule: farthest crossing", {"transects": {"multi_hit_rule": "farthest"}}))
    out.append(("with_estuarine", "include estuarine banks", {"_include_estuarine": True}))
    for dl in (-0.5, +0.5):
        out.append((f"thr_{dl:+.1f}", f"thresholds shifted {dl:+.1f} m/yr", {"risk": {"low_max": cfg["risk"]["low_max"] + dl, "medium_max": cfg["risk"]["medium_max"] + dl}}))
    out.append(("classify_by_LRR", "classify with LRR instead of EPR", {"_field": "lrr"}))
    out.append(("offset_landward_300", "baseline offset 300 m instead of 150 m", {"baseline": {"offset_landward_m": 300}}))
    return out


def apply(cfg: dict, ov: dict) -> dict:
    c = copy.deepcopy(cfg)
    for k, v in ov.items():
        if k.startswith("_"):
            continue
        c[k] = {**c[k], **v}
    return c


def run_sensitivity(cfg: dict, parts: gpd.GeoDataFrame, land, study) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    runs, bar = [], []
    for sid, desc, ov in scenarios(cfg):
        c = apply(cfg, ov)
        try:
            res = compute(c, parts, parts, land, study, shoreline_set=cfg["shoreline_set"], include_estuarine=ov.get("_include_estuarine"))
        except Exception as e:                                           # pragma: no cover
            runs.append({"scenario": sid, "description": desc, "error": str(e)}); continue
        tr = res["transects"]
        fld = ov.get("_field", "EPR_m_yr")
        r = {"scenario": sid, "description": desc, "transects": len(tr), **class_shares(tr, c, fld)}
        v = tr[tr.valid_epr]
        r["mean_EPR"] = float(v[fld].mean()); r["median_EPR"] = float(v[fld].median())
        runs.append(r)
        bc = barangay_class(tr, c, fld); bc.insert(0, "scenario", sid); bar.append(bc)
    runs = pd.DataFrame(runs); bar = pd.concat(bar)
    base = bar[bar.scenario == "base"].set_index("barangay")
    rob = []
    for b in cfg["table_4_2_order"]:
        s = bar[(bar.barangay == b) & (bar.scenario != "base")]
        same_dom = float((s.dominant == base.loc[b, "dominant"]).mean() * 100)
        same_worst = float((s.worst == base.loc[b, "worst"]).mean() * 100)
        rob.append({"barangay": b, "base_dominant": base.loc[b, "dominant"], "base_worst": base.loc[b, "worst"], "runs": len(s),
                    "pct_runs_same_dominant": same_dom, "pct_runs_same_worst": same_worst,
                    "robust": bool(same_dom >= 90 and same_worst >= 90),
                    "classes_seen": ",".join(sorted(set(s.dominant) | {base.loc[b, "dominant"]}))})
    return runs, bar, pd.DataFrame(rob)


# --------------------------------------------------------------------------- agreement of two methods / two sources
def method_agreement(tr: pd.DataFrame, cfg: dict) -> dict:
    v = tr[tr.valid_epr & tr.lrr.notna()]
    ce = classify(v.EPR_m_yr.values, cfg["risk"]["low_max"], cfg["risk"]["medium_max"], cfg["risk"]["accretion_class"])
    cl = classify(v.lrr.values, cfg["risk"]["low_max"], cfg["risk"]["medium_max"], cfg["risk"]["accretion_class"])
    conf = pd.crosstab(pd.Series(ce, name="EPR class"), pd.Series(cl, name="LRR class"))
    diff = v.lrr - v.EPR_m_yr
    return {"n": len(v), "corr": float(v.EPR_m_yr.corr(v.lrr)), "mean_diff": float(diff.mean()), "sd_diff": float(diff.std()),
            "disagree_pct": float((ce != cl).mean() * 100), "confusion": conf, "v": v}


def source_agreement(tv: pd.DataFrame, tr_: pd.DataFrame, cfg: dict) -> dict:
    """Vector set (tv) vs raster set (tr_) on the SAME transects."""
    years = cfg["years"]
    m = tv.merge(tr_, on="transect_id", suffixes=("_v", "_r"))
    rows = []
    for y in years:
        d = (m[f"d_{y}_r"] - m[f"d_{y}_v"]).dropna()
        if len(d) == 0:
            continue
        med = d.median(); mad = 1.4826 * (d - med).abs().median()
        core = d[(d - med).abs() <= 3 * max(mad, 1e-9)]
        rows.append({"year": y, "n": len(d), "bias_median_m": med, "robust_sd_m": mad, "rmse_m": float(np.sqrt((d ** 2).mean())),
                     "p95_abs_m": float(d.abs().quantile(0.95)), "share_within_60m": float((d.abs() <= 60).mean()),
                     "n_core": len(core), "sd_core_m": float(core.std()), "proposal_sigma_per_date_m": float(max(mad, core.std()) / np.sqrt(2))})
    pos = pd.DataFrame(rows)
    both = m[m.valid_epr_v & m.valid_epr_r]
    ce_v = classify(both.EPR_m_yr_v.values, cfg["risk"]["low_max"], cfg["risk"]["medium_max"], cfg["risk"]["accretion_class"])
    ce_r = classify(both.EPR_m_yr_r.values, cfg["risk"]["low_max"], cfg["risk"]["medium_max"], cfg["risk"]["accretion_class"])
    conf = pd.crosstab(pd.Series(ce_v, name="vector_clean class"), pd.Series(ce_r, name="raster_clean class"))
    dd = both.EPR_m_yr_r - both.EPR_m_yr_v
    dl = (both.lrr_r - both.lrr_v).dropna()
    return {"positions": pos, "n_pairs": len(both), "epr_corr": float(both.EPR_m_yr_v.corr(both.EPR_m_yr_r)), "epr_diff_mean": float(dd.mean()),
            "epr_diff_rmse": float(np.sqrt((dd ** 2).mean())), "epr_diff_p95": float(dd.abs().quantile(0.95)), "lrr_diff_rmse": float(np.sqrt((dl ** 2).mean())),
            "class_agree_pct": float((ce_v == ce_r).mean() * 100), "confusion": conf, "both": both}


# --------------------------------------------------------------------------- field validation template
def validation_points(tr: gpd.GeoDataFrame, cfg: dict, n_target: int = 20) -> pd.DataFrame:
    """~20 stratified verification points (barangay x class), spread evenly along each stratum, deterministic.

    Points sit on the 2025 shoreline position of the chosen transect (where the students would stand)."""
    from pyproj import Transformer
    v = tr[tr.valid_epr & tr.d_2025.notna()].copy()
    v["px"] = v.bx + v.nx * v.d_2025; v["py"] = v.by + v.ny * v.d_2025
    strata = v.groupby(["barangay", "risk_class"]).size().reset_index(name="n")
    # allocate: 1 per non-empty stratum first, then top up in barangays with the largest coast, never more than 1 per ~1 km
    alloc = {(r.barangay, r.risk_class): 1 for r in strata.itertuples()}
    extra = n_target - sum(alloc.values())
    order = v.groupby("barangay").size().sort_values(ascending=False).index.tolist()
    i = 0
    while extra > 0 and order:
        b = order[i % len(order)]
        keys = [k for k in alloc if k[0] == b]
        k = max(keys, key=lambda kk: strata[(strata.barangay == kk[0]) & (strata.risk_class == kk[1])].n.iloc[0] / alloc[kk])
        if alloc[k] < strata[(strata.barangay == k[0]) & (strata.risk_class == k[1])].n.iloc[0]:
            alloc[k] += 1; extra -= 1
        i += 1
        if i > 500:
            break
    rows = []
    t2 = Transformer.from_crs(cfg["crs_work"], 4326, always_xy=True)
    for (b, c), k in sorted(alloc.items()):
        g = v[(v.barangay == b) & (v.risk_class == c)].sort_values("axis_km")
        idx = np.linspace(0, len(g) - 1, k + 2)[1:-1].round().astype(int) if k > 1 else [len(g) // 2]
        for j in idx:
            r = g.iloc[int(j)]
            lon, lat = t2.transform(r.px, r.py)
            rows.append({"barangay": b, "predicted_class": c, "transect_id": r.transect_id, "EPR_m_yr": round(float(r.EPR_m_yr), 2),
                         "LRR_m_yr": round(float(r.lrr), 2) if pd.notna(r.lrr) else None, "confidence": r.confidence,
                         "lon": round(lon, 6), "lat": round(lat, 6), "x_utm51n": round(float(r.px), 1), "y_utm51n": round(float(r.py), 1)})
    df = pd.DataFrame(rows).reset_index(drop=True)
    df.insert(0, "point_id", [f"V{k+1:02d}" for k in range(len(df))])
    for col in ("date_visited", "recorder", "gps_device_and_accuracy_m", "distance_to_vegetation_line_m", "distance_to_waterline_at_survey_m",
                "tide_state_or_time", "protection_structure_present (none/seawall/revetment/riprap/breakwater/mangrove/other)", "structure_condition",
                "evidence_of_erosion (scarp/undercut_trees/exposed_roots/none)", "photo_filenames", "notes"):
        df[col] = ""
    return df


def run() -> None:  # pragma: no cover
    cfg = load_config()
    rep = RunReport("sensitivity", cfg)
    work = cfg["crs_work"]; P = cfg["paths"]
    land = unary_union(list(read_vector(P["barangays_all"], work).geometry))
    study = read_vector(P["barangays_study"], work)
    name = cfg["shoreline_set"]
    parts = load_parts(SET_FILES[name]); rep.add_input(SET_FILES[name])
    runs, bar, rob = run_sensitivity(cfg, parts, land, study)
    t = ensure_dir("outputs/tables")
    runs.round(3).to_csv(t / "sensitivity_runs.csv", index=False); bar.round(3).to_csv(t / "sensitivity_barangay_class.csv", index=False); rob.round(1).to_csv(t / "sensitivity_robustness.csv", index=False)
    tv = pd.read_csv(repo_path(f"data/processed/{name}/transect_metrics.csv"))
    ma = method_agreement(gpd.read_file(repo_path(f"data/processed/{name}/risk_transects.gpkg")), cfg)
    ma["confusion"].to_csv(t / "sensitivity_epr_vs_lrr_confusion.csv")
    res = {"runs": runs, "rob": rob, "ma": ma}
    if "raster_clean" in available_sets() and name != "raster_clean":
        tr_ = pd.read_csv(repo_path("data/processed/raster_clean/transect_metrics.csv"))
        sa = source_agreement(tv, tr_, cfg)
        sa["positions"].round(2).to_csv(t / "sensitivity_source_positions.csv", index=False)
        sa["confusion"].to_csv(t / "sensitivity_source_class_confusion.csv")
        res["sa"] = sa
    seg = gpd.read_file(repo_path(f"data/processed/{name}/risk_transects.gpkg"))
    vp = validation_points(seg, cfg)
    outv = ensure_dir("outputs/field_validation")
    vp.to_csv(outv / "field_validation_points.csv", index=False)
    gpd.GeoDataFrame(vp, geometry=gpd.points_from_xy(vp.lon, vp.lat), crs=4326).to_file(outv / "field_validation_points.gpkg", driver="GPKG")
    res["vp"] = vp
    from .sensitivity_report import render, figures
    figures(res, cfg, ensure_dir("outputs/maps"))
    doc = render(res, cfg)
    for f in list(t.glob("sensitivity_*.csv")) + [doc]:
        rep.add_output(f)
    rep.write()
    print(runs[["scenario", "pct_Low", "pct_Medium", "pct_High", "mean_EPR"]].round(1).to_string(index=False)); print(rob.round(0).to_string(index=False))


if __name__ == "__main__":  # pragma: no cover
    run()
