"""Phase 4: shoreline-change statistics on a table of shoreline distances.

Input is a matrix ``D`` (rows = transects, columns = years) of the distance (m) from the transect
start (landward baseline) to the shoreline, positive seaward.  NaN = shoreline not found.

Definitions (first use):
  NSM  Net Shoreline Movement  = D_last - D_first                      (m)   + seaward / - landward
  SCE  Shoreline Change Envelope = max(D) - min(D) over available years (m)
  EPR  End Point Rate          = NSM / T                                (m/yr)
  LRR  Linear Regression Rate  = slope of the least-squares line D(t)   (m/yr), needs >= 3 dates
  WLR  Weighted LRR            = same with weights 1/E^2 when per-year uncertainties exist
Sign convention (thesis): negative = erosion, positive = accretion.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def nsm(D: np.ndarray) -> np.ndarray:
    return D[:, -1] - D[:, 0]


def sce(D: np.ndarray) -> np.ndarray:
    ok = np.isfinite(D).sum(axis=1) >= 2
    out = np.full(len(D), np.nan)
    with np.errstate(all="ignore"):
        out[ok] = (np.nanmax(D[ok], axis=1) - np.nanmin(D[ok], axis=1))
    return out


def epr(D: np.ndarray, T: float) -> np.ndarray:
    return nsm(D) / T


def _ols(t: np.ndarray, d: np.ndarray, w: np.ndarray | None = None):
    n = len(t)
    if w is None:
        w = np.ones(n)
    W = w.sum()
    tm = (w * t).sum() / W; dm = (w * d).sum() / W
    sxx = (w * (t - tm) ** 2).sum()
    slope = (w * (t - tm) * (d - dm)).sum() / sxx
    icpt = dm - slope * tm
    resid = d - (icpt + slope * t)
    sse = (w * resid ** 2).sum()
    sst = (w * (d - dm) ** 2).sum()
    return slope, icpt, sse, sst, sxx


def lrr_table(D: np.ndarray, t: np.ndarray, min_dates: int = 3, E: np.ndarray | None = None) -> pd.DataFrame:
    """Linear regression rate per transect with standard error, R^2, 95 % CI (and WLR if ``E`` given).

    ``E`` = per-year uncertainty (m) vector; WLR weights are 1/E^2.  A transect with fewer than
    ``min_dates`` valid dates gets NaN and a note - never a made-up value."""
    rows = []
    for d in D:
        ok = np.isfinite(d)
        n = int(ok.sum())
        r = {"n_dates": n, "lrr": np.nan, "lrr_se": np.nan, "lrr_r2": np.nan, "lrr_ci_low": np.nan, "lrr_ci_high": np.nan, "wlr": np.nan, "lrr_note": ""}
        if n < min_dates:
            r["lrr_note"] = f"only {n} date(s); need >= {min_dates}"
            rows.append(r); continue
        tt, dd = t[ok], d[ok]
        slope, icpt, sse, sst, sxx = _ols(tt, dd)
        r["lrr"] = slope
        if n > 2:
            se = np.sqrt(sse / (n - 2) / sxx)
            r["lrr_se"] = se
            tcrit = stats.t.ppf(0.975, n - 2)
            r["lrr_ci_low"], r["lrr_ci_high"] = slope - tcrit * se, slope + tcrit * se
        r["lrr_r2"] = 1 - sse / sst if sst > 0 else np.nan
        if E is not None and np.all(np.isfinite(E[ok])) and np.all(E[ok] > 0):
            r["wlr"] = _ols(tt, dd, 1.0 / E[ok] ** 2)[0]
        rows.append(r)
    return pd.DataFrame(rows)


def year_uncertainty(components: dict) -> tuple[float | None, str]:
    """Combine configured error components (m) as root-sum-of-squares.

    Returns (E, status): status COMPLETE (all four given), PARTIAL (some given: E is only a LOWER BOUND)
    or NOT_PROVIDED (none).  Nothing is ever substituted for a null."""
    vals = {k: v for k, v in components.items() if v is not None}
    if not vals:
        return None, "NOT_PROVIDED"
    e = float(np.sqrt(sum(v ** 2 for v in vals.values())))
    return e, ("COMPLETE" if len(vals) == len(components) else "PARTIAL")


def epr_uncertainty(e_first: float | None, e_last: float | None, T: float) -> float | None:
    if e_first is None or e_last is None:
        return None
    return float(np.sqrt(e_first ** 2 + e_last ** 2) / T)


def decimal_year(date_str) -> float:
    d = pd.Timestamp(date_str)
    return d.year + (d.dayofyear - 1) / (366.0 if d.is_leap_year else 365.0)


def time_axis(years: list[int], dates: dict) -> tuple[np.ndarray, str]:
    """Decimal years for the regression and the EPR time span.  Uses real acquisition dates only if
    ALL years have one; otherwise falls back to the calendar year (and says so)."""
    if all(dates.get(y) for y in years):
        return np.array([decimal_year(dates[y]) for y in years]), "acquisition_dates"
    return np.array(years, float), "year_difference"
