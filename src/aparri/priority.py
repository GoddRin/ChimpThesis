"""Phase 10C: a transparent, adjustable ranking of barangays for FIELD INSPECTION priority.

It is *not* a risk index: it uses erosion information only (no buildings, roads or people - none were available).
Two indicators per barangay, each scaled 0-1 across the eight barangays and combined with weights from ``config.priority``:

  rate        mean erosion rate e = max(0, -EPR) over valid transects                       (how fast)
  extent      km of shoreline in the Medium or High class                                   (how much)

priority = (w_rate*rate + w_extent*extent) / (w_rate + w_extent) ;  rank 1 = inspect first.
The share of transects whose class is NOT sensitive to the error band ("how sure") is reported beside the score but
is deliberately not part of it: certainty about a stable coast should not raise its priority.
Change the weights in the config and rerun ``make priority`` - the ranking and its stability are reported.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .io import ensure_dir, load_config, repo_path
from .runreport import RunReport


def minmax(x: pd.Series) -> pd.Series:
    lo, hi = x.min(), x.max()
    return (x - lo) / (hi - lo) if hi > lo else x * 0.0


def priority_table(ext: pd.DataFrame, tm: pd.DataFrame, w: dict) -> pd.DataFrame:
    v = tm[tm.valid_epr].copy()
    v["e"] = np.maximum(0.0, -v.EPR_m_yr)
    rate = v.groupby("barangay").e.mean()
    extent = ext[["Medium risk (km)", "High risk (km)"]].sum(axis=1)
    conf = 1 - ext["% classes that may flip"] / 100.0
    df = pd.DataFrame({"mean_erosion_rate_m_yr": rate, "km_medium_or_high": extent, "share_class_not_sensitive": conf}).reindex(ext.index)
    s = pd.DataFrame({"rate": minmax(df.mean_erosion_rate_m_yr.fillna(0)), "extent": minmax(df.km_medium_or_high.fillna(0))})
    tot = w["rate"] + w["extent"]
    df["priority_score"] = (w["rate"] * s.rate + w["extent"] * s.extent) / tot
    df["rank"] = df.priority_score.rank(ascending=False, method="min").astype(int)
    return df.sort_values("rank")


def rank_stability(ext, tm, w, n=2000, seed=1) -> pd.DataFrame:
    """How often does each barangay keep its rank under random weights (Dirichlet)?  Gives the defence an honest answer to 'why these weights?'."""
    rng = np.random.default_rng(seed)
    base = priority_table(ext, tm, w)["rank"]
    top3 = pd.Series(0.0, index=base.index); same = pd.Series(0.0, index=base.index)
    for _ in range(n):
        d = rng.dirichlet(np.ones(2)); ww = dict(zip(["rate", "extent"], d))
        r = priority_table(ext, tm, ww)["rank"]
        top3 += (r.reindex(base.index) <= 3); same += (r.reindex(base.index) == base)
    return pd.DataFrame({"base_rank": base, "share_in_top3": top3 / n, "share_same_rank": same / n})


def run() -> None:  # pragma: no cover
    cfg = load_config()
    rep = RunReport("priority", cfg)
    ext = pd.read_csv(repo_path("outputs/tables/Table_4_2_extended.csv")).set_index("Barangay")
    tm = pd.read_csv(repo_path(f"data/processed/{cfg['shoreline_set']}/transect_metrics.csv"))
    w = cfg["priority"]["weights"]
    t = priority_table(ext, tm, w)
    st = rank_stability(ext, tm, w)
    out = ensure_dir("outputs/tables")
    t.round(3).to_csv(out / "priority_ranking_field_inspection.csv"); st.round(3).to_csv(out / "priority_rank_stability.csv")
    rep.count("ranking", t["rank"].to_dict()); rep.write()
    print(t.round(2).to_string()); print(st.round(2).to_string())


if __name__ == "__main__":  # pragma: no cover
    run()
