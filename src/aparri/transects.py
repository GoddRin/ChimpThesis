"""Phase 4: DSAS-style baseline, transects and shoreline-change metrics (USGS DSAS re-created in the open).

Plain-English recipe (see docs/02_method.md for the diagram):

  1. BASELINE  A reference line that lies on land, behind ALL shorelines.  We take the reference-year
     (1990) open-coast shoreline, smooth it (moving average, ``baseline.smooth_m``) and push it landward by
     the largest landward excursion of any year plus ``baseline.offset_landward_m``.  Which side is land is
     decided from the municipal land polygons (test points either side), never assumed.
  2. TRANSECTS  Short lines perpendicular to the baseline every ``transects.spacing_m`` metres.  Each has a
     stable ID (sector + sequence) and starts on land.  They are the "measuring tapes".
  3. For each year, where a transect crosses that year's shoreline we read the distance from the transect
     start.  If it crosses twice we keep the crossing set by ``transects.multi_hit_rule`` and flag it.
  4. METRICS (``metrics.py``): NSM, SCE, EPR (1990->2025), LRR (all years), uncertainty.

Sign convention (thesis): distance is positive seaward, so negative change = landward = EROSION.
All geometry is in EPSG:32651.  The same baseline/transects are used for every shoreline set, so that
sets can be compared transect by transect (Phase 6); the baseline is only a measuring grid.
"""
from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.ndimage import uniform_filter1d
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, unary_union

from . import metrics as M
from .io import ensure_dir, load_config, read_vector, repo_path
from .runreport import RunReport

SET_FILES = {
    "vector_clean": "data/interim/shorelines_clean.gpkg",
    "raster_clean": "data/interim/shorelines_raster_clean.gpkg",
    "landsat_v2": "data/interim/shorelines_landsat_v2.gpkg",
}
PIXEL_SETS = {"raster_clean", "landsat_v2"}     # derived from 30 m Landsat pixels (Earth Engine SCALE = 30)


# --------------------------------------------------------------------------- baseline
def resample(coords: np.ndarray, step: float) -> np.ndarray:
    ls = LineString(coords)
    n = max(int(np.ceil(ls.length / step)), 2)
    d = np.linspace(0, ls.length, n + 1)
    return np.array([ls.interpolate(x).coords[0] for x in d])


def smooth(pts: np.ndarray, window_m: float, step: float) -> np.ndarray:
    """Moving average along the line (window in metres); the two end points are kept in place."""
    w = max(int(round(window_m / step)), 1)
    out = np.column_stack([uniform_filter1d(pts[:, k], size=w, mode="nearest") for k in (0, 1)])
    out[0], out[-1] = pts[0], pts[-1]
    return out


def left_normals(pts: np.ndarray) -> np.ndarray:
    t = np.gradient(pts, axis=0)
    t /= np.maximum(np.hypot(t[:, 0], t[:, 1]), 1e-9)[:, None]
    return np.column_stack([-t[:, 1], t[:, 0]])


def landward_is_left(pts: np.ndarray, nl: np.ndarray, land, test_m: float = 300.0, n_test: int = 40) -> tuple[bool, int, int]:
    """Which side of the line is land?  Count test points inside the land polygons on each side."""
    idx = np.linspace(0, len(pts) - 1, min(n_test, len(pts))).astype(int)
    left = shapely.contains_xy(land, *(pts[idx] + nl[idx] * test_m).T).sum()
    right = shapely.contains_xy(land, *(pts[idx] - nl[idx] * test_m).T).sum()
    return bool(left > right), int(left), int(right)


@dataclass
class Sector:
    sid: str
    P: np.ndarray          # smoothed reference points
    n_sea: np.ndarray      # unit normals pointing seaward
    land_check: tuple      # (landward_is_left, n_left, n_right)
    shift: float = 0.0     # landward shift applied to P to get the baseline (m)


def merge_sectors(lines: list[LineString], min_len: float = 200.0) -> list[LineString]:
    if not lines:
        return []
    u = unary_union(lines)
    m = linemerge(u) if u.geom_type == "MultiLineString" else u
    geoms = list(m.geoms) if m.geom_type == "MultiLineString" else [m]
    geoms = [g for g in geoms if g.length >= min_len]
    # NW -> SE along each line and sectors ordered NW -> SE
    out = []
    for g in geoms:
        c = np.array(g.coords)[:, :2]
        if c[0, 0] - c[0, 1] > c[-1, 0] - c[-1, 1]:
            c = c[::-1]
        out.append(LineString(c))
    return sorted(out, key=lambda g: g.coords[0][0] - g.coords[0][1])


def build_sectors(ref_lines: list[LineString], land, cfg: dict) -> list[Sector]:
    step = 10.0
    b = cfg["baseline"]
    override = (b.get("landward_override") or {})
    secs = []
    for i, g in enumerate(merge_sectors(ref_lines), start=1):
        sid = f"S{i}"
        pts = smooth(resample(np.array(g.coords)[:, :2], step), b["smooth_m"], step)
        nl = left_normals(pts)
        is_left, nL, nR = landward_is_left(pts, nl, land)
        if sid in override:
            is_left = str(override[sid]).lower() == "left"
        n_sea = -nl if is_left else nl
        secs.append(Sector(sid, pts, n_sea, (is_left, nL, nR)))
    return secs


def _transect_points(sec: Sector, spacing: float, step: float = 10.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Points every ``spacing`` m along the smoothed reference line with their seaward normals."""
    seg = np.hypot(*np.diff(sec.P, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    pos = np.arange(spacing / 2, s[-1], spacing)
    x = np.interp(pos, s, sec.P[:, 0]); y = np.interp(pos, s, sec.P[:, 1])
    nx = np.interp(pos, s, sec.n_sea[:, 0]); ny = np.interp(pos, s, sec.n_sea[:, 1])
    n = np.column_stack([nx, ny]); n /= np.hypot(n[:, 0], n[:, 1])[:, None]
    return np.column_stack([x, y]), n, pos


def make_transects(sectors: list[Sector], shift_by_sector: dict[str, float], cfg: dict) -> gpd.GeoDataFrame:
    """Transect lines.  Geometry starts ``length_landward_m`` behind the baseline point B and ends
    ``shift + length_seaward_m`` seaward of the smoothed reference point P (B = P shifted landward)."""
    t = cfg["transects"]
    rows = []
    for sec in sectors:
        D = shift_by_sector.get(sec.sid, 0.0)
        P, n, pos = _transect_points(sec, t["spacing_m"])
        for k, (p, nn, s) in enumerate(zip(P, n, pos), start=1):
            B = p - nn * D
            start = B - nn * t["length_landward_m"]
            end = p + nn * t["length_seaward_m"]
            rows.append({"transect_id": f"{sec.sid}-{k:04d}", "sector": sec.sid, "seq": k, "chainage_m": float(s),
                         "bx": B[0], "by": B[1], "nx": nn[0], "ny": nn[1], "shift_m": D, "geometry": LineString([start, end])})
    g = gpd.GeoDataFrame(rows, crs=cfg["crs_work"])
    g["baseline_offset_m"] = cfg["transects"]["length_landward_m"]       # distance of the geometry start behind B
    return g


def quality_flags(tr: gpd.GeoDataFrame, land, cfg: dict) -> pd.Series:
    """Fan / crossing / sharp-bend flags for transects (they make a rate meaningless there)."""
    flags = [[] for _ in range(len(tr))]
    geoms = tr.geometry.values
    # crossings with the next two neighbours of the same sector
    for i in range(len(tr) - 1):
        for j in (i + 1, i + 2):
            if j < len(tr) and tr.sector.iloc[i] == tr.sector.iloc[j] and geoms[i].intersects(geoms[j]):
                flags[i].append("crossing"); flags[j].append("crossing")
    n = tr[["nx", "ny"]].values
    for i in range(1, len(tr)):
        if tr.sector.iloc[i] == tr.sector.iloc[i - 1]:
            ang = np.degrees(np.arccos(np.clip(n[i] @ n[i - 1], -1, 1)))
            if ang > cfg["transects"].get("max_turn_deg", 15.0):
                flags[i].append("sharp_bend")
    start_on_land = shapely.contains_xy(land, tr.bx.values, tr.by.values)
    for i, ok in enumerate(start_on_land):
        if not ok:
            flags[i].append("start_not_on_land")
    return pd.Series([";".join(sorted(set(f))) for f in flags], index=tr.index)


# --------------------------------------------------------------------------- measuring
def hits_on_transects(tr: gpd.GeoDataFrame, shoreline, land_off: float) -> list[list[float]]:
    """All crossing distances (m from baseline point B, + seaward) of each transect with ``shoreline``."""
    if shoreline is None or shoreline.is_empty:
        return [[] for _ in range(len(tr))]
    inter = shapely.intersection(tr.geometry.values, shoreline)
    out = []
    for g, geom in zip(inter, tr.geometry.values):
        pts = shapely.get_coordinates(g) if not g.is_empty else np.empty((0, 2))
        if len(pts) == 0:
            out.append([]); continue
        d = shapely.line_locate_point(geom, shapely.points(pts[:, 0], pts[:, 1])) - land_off
        out.append(sorted(set(np.round(d, 3).tolist())))
    return out


def choose_hit(hits: list[float], rule: str) -> float:
    if not hits:
        return np.nan
    if rule == "farthest":
        return max(hits)
    return min(hits)            # "nearest" to the baseline (also used for "flag_only")


def measure(tr: gpd.GeoDataFrame, lines_by_year: dict[int, list[LineString]], cfg: dict) -> tuple[np.ndarray, pd.DataFrame]:
    years = cfg["years"]
    rule = cfg["transects"]["multi_hit_rule"]
    off = cfg["transects"]["length_landward_m"]
    D = np.full((len(tr), len(years)), np.nan)
    recs = []
    for j, y in enumerate(years):
        sh = unary_union(lines_by_year.get(y, [])) if lines_by_year.get(y) else None
        allhits = hits_on_transects(tr, sh, off)
        for i, hits in enumerate(allhits):
            D[i, j] = choose_hit(hits, rule)
            if hits:
                d = D[i, j]
                bx, by, nx, ny = tr.bx.iloc[i], tr.by.iloc[i], tr.nx.iloc[i], tr.ny.iloc[i]
                recs.append({"transect_id": tr.transect_id.iloc[i], "year": y, "d_m": d, "x": bx + nx * d, "y": by + ny * d,
                             "n_hits": len(hits), "multi_hit": len(hits) > 1, "rule": rule})
    return D, pd.DataFrame(recs)


def required_shift(tr_trial: gpd.GeoDataFrame, lines_by_year, cfg: dict, sectors) -> dict[str, float]:
    """Largest landward excursion of any year, per sector, measured from the smoothed reference line P."""
    off = cfg["transects"]["length_landward_m"]
    shifts = {s.sid: 0.0 for s in sectors}
    for y, ls in lines_by_year.items():
        if not ls:
            continue
        hits = hits_on_transects(tr_trial, unary_union(ls), off)
        for sid, h in zip(tr_trial.sector, hits):
            if h:
                shifts[sid] = max(shifts[sid], -min(h))        # d is measured from P in the trial run; negative = landward of P
    return {k: v + cfg["baseline"]["offset_landward_m"] for k, v in shifts.items()}


# --------------------------------------------------------------------------- the engine
def compute(cfg: dict, parts: gpd.GeoDataFrame, baseline_parts: gpd.GeoDataFrame, land, study: gpd.GeoDataFrame | None = None,
            shoreline_set: str = "vector_clean", include_estuarine: bool | None = None) -> dict:
    """Run the whole engine in memory.

    ``parts``           shoreline parts (columns year, scope, geometry) of the set being measured
    ``baseline_parts``  parts used only to build the baseline/transects (reference year)
    """
    years = cfg["years"]
    inc_est = cfg["scope"]["include_estuarine_banks"] if include_estuarine is None else include_estuarine
    keep = parts if inc_est else parts[parts.scope == "open_coast"]
    lines_by_year = {y: list(keep[keep.year == y].geometry) for y in years}
    bkeep = baseline_parts if inc_est else baseline_parts[baseline_parts.scope == "open_coast"]
    ref = list(bkeep[bkeep.year == cfg["baseline"]["reference_year"]].geometry)
    sectors = build_sectors(ref, land, cfg)
    if not sectors:
        raise ValueError("no reference-year shoreline: cannot build a baseline")
    # trial run: transects from P, symmetric, to find how far landward the shorelines wander
    trial_cfg = {**cfg, "transects": {**cfg["transects"]}}
    # baseline excursion is determined against the baseline-source set (so that sets share one grid)
    base_lines = {y: list(bkeep[bkeep.year == y].geometry) for y in years}
    tr0 = make_transects(sectors, {}, trial_cfg)
    shift = required_shift(tr0, base_lines, trial_cfg, sectors)
    for s in sectors:
        s.shift = shift[s.sid]
    tr = make_transects(sectors, shift, cfg)
    tr["quality_flag"] = quality_flags(tr, land, cfg)
    D, pts = measure(tr, lines_by_year, cfg)

    t_axis, t_src = M.time_axis(years, cfg.get("acquisition_dates", {}))
    T = float(t_axis[-1] - t_axis[0])
    comp = dict(cfg["uncertainty_m"])
    if shoreline_set in PIXEL_SETS and comp.get("pixel") is None:
        comp["pixel"] = float(cfg["uncertainty_proposals_m"]["pixel_landsat"])      # SCALE = 30 in the Earth Engine script
    E_year, status = M.year_uncertainty(comp)
    epr_unc = M.epr_uncertainty(E_year, E_year, T)

    met = pd.DataFrame({"transect_id": tr.transect_id.values})
    met["NSM_m"] = M.nsm(D); met["SCE_m"] = M.sce(D); met["EPR_m_yr"] = met.NSM_m / T
    for j, y in enumerate(years):
        met[f"d_{y}"] = D[:, j]
    lrr = M.lrr_table(D, t_axis, cfg["transects"].get("min_years_for_lrr", 3))
    met = pd.concat([met, lrr], axis=1)
    met["T_years"] = T; met["T_source"] = t_src
    met["unc_status"] = status
    met["epr_unc_m_yr"] = epr_unc if status == "COMPLETE" else np.nan
    met["epr_unc_lower_bound_m_yr"] = epr_unc if status == "PARTIAL" else np.nan
    absE = met.EPR_m_yr.abs()
    met["confident"] = (absE > epr_unc) if status == "COMPLETE" else pd.NA              # only with ALL error components given
    met["exceeds_unc_lower_bound"] = (absE > epr_unc) if status == "PARTIAL" else pd.NA  # lower bound only (e.g. 30 m pixel)
    mh = pts[pts.multi_hit].groupby("transect_id").year.apply(lambda s: ",".join(map(str, sorted(s)))) if len(pts) else pd.Series(dtype=str)
    tr["multi_hit_years"] = tr.transect_id.map(mh).fillna("")
    miss = [";".join(f"missing_{y}" for j, y in enumerate(years) if np.isnan(D[i, j])) for i in range(len(tr))]
    tr["missing"] = miss
    tr = tr.merge(met, on="transect_id")
    tr["valid_epr"] = tr.EPR_m_yr.notna() & ~tr.quality_flag.str.contains("crossing|start_not_on_land")
    tr["flagged"] = (tr.quality_flag != "") | (tr.multi_hit_years != "") | (tr.missing != "")
    # chainage along the coast axis (km from the NW end) for plots
    p0 = np.array([tr.bx.iloc[0], tr.by.iloc[0]]); p1 = np.array([tr.bx.iloc[-1], tr.by.iloc[-1]])
    ab = (p1 - p0) / np.linalg.norm(p1 - p0)
    tr["axis_km"] = ((tr[["bx", "by"]].values - p0) @ ab) / 1000.0
    # barangay assignment (nearest study polygon within tolerance) at the mean shoreline position
    if study is not None:
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                dm = np.nanmean(D, axis=1)
        dm = np.where(np.isnan(dm), 0.0, dm)
        mx = tr.bx.values + tr.nx.values * dm; my = tr.by.values + tr.ny.values * dm
        pts_s = shapely.points(mx, my)
        dist = np.vstack([shapely.distance(pts_s, g) for g in study.geometry])
        j = dist.argmin(axis=0)
        names = np.array(study.ADM4_EN)[j]
        ok = dist.min(axis=0) <= cfg["barangay_join_tolerance_m"]
        tr["barangay"] = np.where(ok, names, None)
        tr["barangay_dist_m"] = dist.min(axis=0)
    return {"transects": tr, "points": pts, "D": D, "years": years, "T": T, "T_source": t_src, "unc_status": status,
            "epr_unc": epr_unc, "sectors": sectors, "shift": shift, "E_year": E_year}


def summary(tr: gpd.GeoDataFrame) -> dict:
    v = tr[tr.valid_epr]
    return {
        "transects": int(len(tr)), "valid_epr": int(len(v)), "flagged": int(tr.flagged.sum()),
        "with_crossing": int(tr.quality_flag.str.contains("crossing").sum()),
        "with_sharp_bend": int(tr.quality_flag.str.contains("sharp_bend").sum()),
        "missing_first_or_last": int(tr.EPR_m_yr.isna().sum()),
        "multi_hit": int((tr.multi_hit_years != "").sum()),
        "epr_mean": float(v.EPR_m_yr.mean()), "epr_median": float(v.EPR_m_yr.median()),
        "epr_min": float(v.EPR_m_yr.min()), "epr_max": float(v.EPR_m_yr.max()),
        "pct_eroding": float((v.EPR_m_yr < 0).mean() * 100),
    }


# --------------------------------------------------------------------------- IO wrappers
def load_parts(path: str) -> gpd.GeoDataFrame:
    return gpd.read_file(repo_path(path), layer="shoreline_parts")


def available_sets() -> list[str]:
    return [k for k, p in SET_FILES.items() if repo_path(p).exists()]


def qa_figures(res: dict, name: str, out_dir) -> None:  # pragma: no cover
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tr = res["transects"]; v = tr[tr.valid_epr]
    fig, ax = plt.subplots(1, 2, figsize=(14, 4.5))
    ax[0].hist(v.EPR_m_yr.clip(-15, 15), bins=60, color="#1f77b4")
    for x in (-5, -2, 2, 5):
        ax[0].axvline(x, color="r" if x < 0 else "g", ls="--", lw=0.8)
    ax[0].set_title(f"{name}: EPR 1990-2025 of {len(v)} valid transects (m/yr; clipped to ±15)\nred dashed = erosion class limits (-2, -5)")
    ax[0].set_xlabel("EPR (m/yr), negative = erosion"); ax[0].set_ylabel("transects")
    cmap = {"": "#2ca02c"}
    for _, r in tr.iterrows():
        x, y = r.geometry.xy
        col = "#2ca02c" if not r.flagged else ("#d62728" if "crossing" in r.quality_flag or "start_not_on_land" in r.quality_flag else "#ff7f0e")
        ax[1].plot(x, y, color=col, lw=0.5)
    ax[1].set_aspect("equal"); ax[1].set_title("transects: green ok · orange flagged (bend/missing/multi-hit) · red crossing/start not on land", fontsize=9)
    fig.tight_layout(); fig.savefig(out_dir / f"qa_{name}.png", dpi=130); plt.close(fig)


def run() -> None:  # pragma: no cover
    cfg = load_config()
    rep = RunReport("transects", cfg)
    work = cfg["crs_work"]; P = cfg["paths"]
    rep.add_input(P["barangays_all"]); rep.add_input(P["barangays_study"])
    land = unary_union(list(read_vector(P["barangays_all"], work).geometry))
    study = read_vector(P["barangays_study"], work)
    base_name = cfg["baseline"].get("source_set", "vector_clean")
    base_parts = load_parts(SET_FILES[base_name]); rep.add_input(SET_FILES[base_name])
    if cfg["acquisition_dates"] and not all(cfg["acquisition_dates"].values()):
        rep.warn("acquisition_dates not provided: EPR uses the calendar-year difference (35 years), not real image dates")
    rep.warn_if_null(cfg["uncertainty_m"], "uncertainty_m")
    allsum = []
    for name in available_sets():
        parts = load_parts(SET_FILES[name]); rep.add_input(SET_FILES[name])
        res = compute(cfg, parts, base_parts, land, study, shoreline_set=name)
        out = ensure_dir(f"data/processed/{name}")
        tr = res["transects"]
        keep_cols = [c for c in tr.columns if c not in ("nx", "ny")]
        tr[keep_cols + ["nx", "ny"]].to_file(out / "transects.gpkg", layer="transects", driver="GPKG")
        pd.DataFrame({"sector": [s.sid for s in res["sectors"]], "shift_landward_m": [s.shift for s in res["sectors"]],
                      "landward_is_left": [s.land_check[0] for s in res["sectors"]], "test_left": [s.land_check[1] for s in res["sectors"]],
                      "test_right": [s.land_check[2] for s in res["sectors"]]}).to_csv(out / "baseline_info.csv", index=False)
        gpd.GeoDataFrame({"sector": [s.sid for s in res["sectors"]],
                          "geometry": [LineString(s.P - s.n_sea * s.shift) for s in res["sectors"]]}, crs=work).to_file(out / "transects.gpkg", layer="baseline", driver="GPKG", mode="a")
        res["points"].to_csv(out / "shoreline_points.csv", index=False)
        tr.drop(columns="geometry").to_csv(out / "transect_metrics.csv", index=False)
        qa_figures(res, name, ensure_dir("outputs/maps"))
        s = summary(tr); s["set"] = name; s["T_source"] = res["T_source"]; s["unc_status"] = res["unc_status"]
        allsum.append(s)
        unc_ = res["epr_unc"]
        rep.count(f"{name}_summary", s)
        if res["unc_status"] != "COMPLETE":
            rep.warn(f"{name}: uncertainty {res['unc_status']}" + (f" - EPR lower-bound uncertainty {unc_:.2f} m/yr (pixel only)" if unc_ else ""))
        rep.add_output(out / "transects.gpkg")
    df = pd.DataFrame(allsum)
    df.to_csv(ensure_dir("outputs/tables") / "transect_summary_by_set.csv", index=False)
    rep.write()
    print(df.round(2).to_string(index=False))


if __name__ == "__main__":  # pragma: no cover
    run()
