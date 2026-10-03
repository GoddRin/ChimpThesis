"""Phase 3A: reproducible, logged cleaning of the vector shorelines (product B).

Input : ``data/raw/shoreline_changes/Shoreline Changes.shp`` (read-only).
Output: ``data/interim/shorelines_clean.gpkg`` with layers
          ``shorelines_clean``  one row per continuous chain (year, chain id, length ...)
          ``shoreline_parts``   chains cut into open-coast / estuarine-bank parts (the unit Phase 4 uses)
          ``quarantine``        features that are NOT analysed until a human decides (the "Hig" feature)
          ``clean_log``         every action: what, why, how many metres (also ``outputs/tables/clean_log.csv``)
        ``data/interim/scope_review.gpkg``  QGIS-editable review package (see ``docs/02_method.md``)
        ``outputs/maps/clean_review.png``   review map.

Principles (CLAUDE.md rules 1-4): nothing is deleted silently, nothing is guessed.  Ambiguous
cases (the mislabelled "Hig" line, big loops, doubled stretches) go to the human-review list.
All geometry work is done in EPSG:32651 (metres).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import unary_union

from . import audit as A
from .io import ensure_dir, load_config, read_vector, repo_path
from .runreport import RunReport
from .scope import CoastScope


# --------------------------------------------------------------------------- log
@dataclass
class CleanLog:
    rows: list[dict] = field(default_factory=list)

    def add(self, action: str, year, fid, before_m: float, after_m: float, reason: str, point=None, review: bool = False) -> None:
        self.rows.append({"action": action, "year": year, "feature_id": fid, "before_m": round(float(before_m), 2),
                          "after_m": round(float(after_m), 2), "removed_m": round(float(before_m - after_m), 2),
                          "reason": reason, "x": None if point is None else round(point[0], 1),
                          "y": None if point is None else round(point[1], 1), "needs_human_review": review})

    def frame(self) -> pd.DataFrame:
        cols = ["action", "year", "feature_id", "before_m", "after_m", "removed_m", "reason", "x", "y", "needs_human_review"]
        return pd.DataFrame(self.rows, columns=cols)


# --------------------------------------------------------------------------- geometry helpers
def coords_of(g: LineString) -> np.ndarray:
    return np.array(g.coords)[:, :2]


def dedupe(c: np.ndarray, tol: float = 0.01) -> np.ndarray:
    """Drop consecutive duplicate vertices (the audit found several)."""
    out = [c[0]]
    for p in c[1:]:
        if np.hypot(*(p - out[-1])) > tol:
            out.append(p)
    return np.array(out)


def seg_intersection(p, p2, q, q2):
    """Proper intersection point of segments p-p2 and q-q2, or None."""
    r = p2 - p
    s = q2 - q
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-12:
        return None
    t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / den
    u = ((q[0] - p[0]) * r[1] - (q[1] - p[1]) * r[0]) / den
    if 0 < t < 1 and 0 < u < 1:
        return p + t * r
    return None


def self_intersections(c: np.ndarray) -> list[tuple[int, int, np.ndarray]]:
    """All crossings between non-adjacent segments: (i, j, point) with segment i before segment j."""
    out = []
    n = len(c) - 1
    # bounding boxes to skip most pairs
    mn = np.minimum(c[:-1], c[1:]); mx = np.maximum(c[:-1], c[1:])
    for i in range(n):
        cand = np.where((mn[i + 2:, 0] <= mx[i, 0]) & (mx[i + 2:, 0] >= mn[i, 0]) &
                        (mn[i + 2:, 1] <= mx[i, 1]) & (mx[i + 2:, 1] >= mn[i, 1]))[0] + i + 2
        for j in cand:
            pt = seg_intersection(c[i], c[i + 1], c[j], c[j + 1])
            if pt is not None:
                out.append((i, int(j), pt))
    return out


def loop_length(c: np.ndarray, i: int, j: int, pt: np.ndarray) -> float:
    mid = c[i + 1:j + 1]
    pts = np.vstack([pt, mid, pt])
    return float(np.hypot(*np.diff(pts, axis=0).T).sum())


def remove_small_loops(c: np.ndarray, max_len: float) -> tuple[np.ndarray, list[dict], list[dict]]:
    """Cut out self-crossing loops shorter than ``max_len`` metres.

    Returns (new coords, removed loops, kept loops).  A loop is the piece of line between the two
    passes through a crossing point.  Only loops shorter than ``max_len`` are removed - they are
    digitising slips; longer ones are real geography (river-mouth bars) and are reported only."""
    removed: list[dict] = []
    c = dedupe(c)
    while True:
        xs = self_intersections(c)
        small = [(loop_length(c, i, j, pt), i, j, pt) for i, j, pt in xs if loop_length(c, i, j, pt) < max_len]
        if not small:
            break
        L, i, j, pt = min(small, key=lambda z: z[0])
        removed.append({"length_m": L, "x": float(pt[0]), "y": float(pt[1])})
        c = np.vstack([c[:i + 1], pt, c[j + 1:]])
        c = dedupe(c)
    kept = [{"length_m": loop_length(c, i, j, pt), "x": float(pt[0]), "y": float(pt[1])} for i, j, pt in self_intersections(c)]
    return c, removed, kept


def drop_duplicate_fragments(items: list[tuple[int, LineString]], tol: float, cover: float) -> tuple[list, list[dict]]:
    """Find stretches digitised twice within one year.

    A fragment is a duplicate when at least ``cover`` of its length lies within ``tol`` metres of the
    OTHER fragments still kept.  Fragments are tested shortest first, so the longest continuous
    version of a stretch survives."""
    kept = sorted(items, key=lambda it: it[1].length)
    dropped: list[dict] = []
    for it in list(kept):
        others = [o for o in kept if o[0] != it[0]]
        if not others:
            continue
        u = unary_union([o[1] for o in others])
        share = it[1].intersection(u.buffer(tol)).length / it[1].length
        if share >= cover:
            kept = [o for o in kept if o[0] != it[0]]
            dropped.append({"fid": it[0], "length_m": it[1].length, "covered_share": share,
                            "covered_by": [o[0] for o in others if it[1].intersection(o[1].buffer(tol)).length / it[1].length > 0.05]})
    return sorted(kept, key=lambda it: it[0]), dropped


def orient_nw_se(c: np.ndarray) -> np.ndarray:
    """All chains run NW -> SE (x - y increasing) so that "start" and "end" mean the same everywhere."""
    return c if (c[0, 0] - c[0, 1]) <= (c[-1, 0] - c[-1, 1]) else c[::-1]


def snap_merge(items: list[tuple[int, np.ndarray]], tol: float) -> tuple[list[tuple[list[int], np.ndarray]], list[dict]]:
    """Join chains whose end points are within ``tol`` metres (greedy, closest pair first)."""
    chains = [([fid], c.copy()) for fid, c in items]
    joins: list[dict] = []
    while True:
        best = None
        for a in range(len(chains)):
            for b in range(a + 1, len(chains)):
                ca, cb = chains[a][1], chains[b][1]
                for ea, pa in (("s", ca[0]), ("e", ca[-1])):
                    for eb, pb in (("s", cb[0]), ("e", cb[-1])):
                        d = float(np.hypot(*(pa - pb)))
                        if d <= tol and (best is None or d < best[0]):
                            best = (d, a, b, ea, eb)
        if best is None:
            break
        d, a, b, ea, eb = best
        (fa, ca), (fb, cb) = chains[a], chains[b]
        if ea == "s":
            ca = ca[::-1]
        if eb == "e":
            cb = cb[::-1]
        merged = np.vstack([ca, cb[1:] if d < 0.01 else cb])
        joins.append({"fids": (fa, fb), "gap_m": d})
        chains = [ch for k, ch in enumerate(chains) if k not in (a, b)] + [(fa + fb, merged)]
    return chains, joins


def tag_parts(chain: LineString, scope: CoastScope, min_run_m: float) -> list[tuple[LineString, str, float]]:
    """Cut a chain into open_coast / estuarine_bank parts with the hull rule.

    Runs shorter than ``min_run_m`` are absorbed by their neighbour so the tag does not flicker."""
    c = coords_of(chain)
    z = scope.classify_xy(c[:, 0], c[:, 1])
    is_open = (z == "open_coast")
    seg_len = np.hypot(*np.diff(c, axis=0).T)
    # tag per segment: open if both ends open, else by majority of the two ends' (use start)
    seg_open = is_open[:-1] & is_open[1:]
    runs = []
    s = 0
    for k in range(1, len(seg_open) + 1):
        if k == len(seg_open) or seg_open[k] != seg_open[s]:
            runs.append([s, k - 1, bool(seg_open[s])])
            s = k
    # absorb short runs
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for idx, (a, b, v) in enumerate(runs):
            ln = seg_len[a:b + 1].sum()
            if ln < min_run_m:
                nb = idx - 1 if idx > 0 else idx + 1
                runs[nb][0] = min(runs[nb][0], a); runs[nb][1] = max(runs[nb][1], b)
                runs.pop(idx)
                changed = True
                break
        # merge adjacent equal tags
        merged = []
        for r in runs:
            if merged and merged[-1][2] == r[2]:
                merged[-1][1] = r[1]
            else:
                merged.append(r)
        runs = merged
    parts = []
    for a, b, v in runs:
        sub = c[a:b + 2]
        parts.append((LineString(sub), "open_coast" if v else "estuarine_bank", float(seg_len[a:b + 1].sum())))
    return parts


# --------------------------------------------------------------------------- coverage
def covered_intervals(lines: list[LineString], a: np.ndarray, ax: np.ndarray, gap_m: float = 150.0) -> list[tuple[float, float]]:
    """Intervals (km) of the along-coast axis covered by the lines (small gaps tolerated)."""
    iv = []
    for g in lines:
        c = coords_of(g)
        t = (c - a) @ ax / 1000.0
        for k in range(len(t) - 1):
            lo, hi = sorted((t[k], t[k + 1]))
            iv.append((lo, hi))
    iv.sort()
    out: list[list[float]] = []
    for lo, hi in iv:
        if out and lo <= out[-1][1] + gap_m / 1000:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [(lo, hi) for lo, hi in out]


def interval_overlap(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = []
    for lo1, hi1 in a:
        for lo2, hi2 in b:
            lo, hi = max(lo1, lo2), min(hi1, hi2)
            if hi > lo:
                out.append((lo, hi))
    return out


def total(iv: list[tuple[float, float]]) -> float:
    return float(sum(h - l for l, h in iv))


# --------------------------------------------------------------------------- pipeline
def clean_shorelines(raw: gpd.GeoDataFrame, cfg: dict, land, log: CleanLog) -> dict:
    """The whole cleaning chain on an in-memory frame (also used by the tests)."""
    work = cfg["crs_work"]; cc = cfg["clean"]
    lines = A.normalise_lines(raw, work) if "year_raw" not in raw.columns else raw
    lines = lines[~lines.geometry.is_empty & (lines.length > 0)].copy()
    overrides = {str(k): v for k, v in (cfg.get("manual_year_overrides") or {}).items()}

    quarantine, usable = [], []
    for _, r in lines.iterrows():
        key = f"feature_{r.fid}"
        yr = overrides.get(key, overrides.get(str(r.fid)))
        if yr is None and pd.isna(r.year):
            quarantine.append(r)
            log.add("quarantine", r.year_raw, int(r.fid), r.geometry.length, 0.0,
                    f"year value '{r.year_raw}' is not a year; excluded until a human sets manual_year_overrides.{key}",
                    point=r.geometry.interpolate(0.5, normalized=True).coords[0], review=True)
            continue
        if yr is not None:
            log.add("manual_year_override", yr, int(r.fid), r.geometry.length, r.geometry.length, f"year set by a human via config ({key} -> {yr})")
            r = r.copy(); r["year"] = yr; r["year_raw"] = str(yr)
        usable.append(r)
    use = gpd.GeoDataFrame(usable, crs=lines.crs)
    years = sorted(int(y) for y in use.year.unique())

    scope = CoastScope(list(use.geometry), land, cfg["scope"]["hull_tolerance_m"], cfg["scope"].get("concave_ratio", 0.1))
    chains_out, parts_out = [], []
    for y in years:
        grp = use[use.year == y]
        before = grp.length.sum()
        items = [(int(r.fid), r.geometry) for _, r in grp.iterrows()]
        items, dups = drop_duplicate_fragments(items, tol=cc.get("duplicate_tol_m", 60.0), cover=cc.get("duplicate_cover", 0.8))
        for d in dups:
            log.add("duplicate_stretch_removed", y, d["fid"], d["length_m"], 0.0,
                    f"{d['covered_share']:.0%} of this fragment lies within {cc.get('duplicate_tol_m', 60.0):.0f} m of fragment(s) {d['covered_by']} "
                    "(same coast digitised twice); the longer continuous version is kept", review=True)
        arrays = []
        for fid, g in items:
            c, rem, kept = remove_small_loops(coords_of(g), cc["min_loop_m"])
            for L in rem:
                log.add("small_loop_removed", y, fid, L["length_m"], 0.0, f"self-crossing loop of {L['length_m']:.1f} m < min_loop_m={cc['min_loop_m']}", (L["x"], L["y"]))
            for L in kept:
                log.add("loop_kept", y, fid, L["length_m"], L["length_m"], f"self-crossing loop of {L['length_m']:.0f} m >= min_loop_m: kept (probably real river-mouth geometry); please check", (L["x"], L["y"]), review=True)
            arrays.append((fid, orient_nw_se(c)))
        merged, joins = snap_merge(arrays, cc["snap_tol_m"])
        for j in joins:
            log.add("endpoints_joined", y, str(j["fids"]), j["gap_m"], 0.0, f"end points {j['gap_m']:.2f} m apart (<= snap_tol_m={cc['snap_tol_m']}) joined")
        chain_no = 0
        for fids, c in merged:
            ln = float(np.hypot(*np.diff(c, axis=0).T).sum())
            if ln < cc["min_segment_m"]:
                log.add("short_segment_removed", y, str(fids), ln, 0.0, f"shorter than min_segment_m={cc['min_segment_m']}")
                continue
            chain_no += 1
            g = LineString(orient_nw_se(c))
            cid = f"{y}-{chain_no}"
            chains_out.append({"year": y, "chain_id": cid, "source_fids": ",".join(map(str, sorted(fids))), "length_m": g.length,
                               "n_vertices": len(g.coords), "geometry": g})
            for k, (sub, tag, ln_p) in enumerate(tag_parts(g, scope, cc.get("min_scope_run_m", 150.0)), start=1):
                parts_out.append({"year": y, "chain_id": cid, "part_id": f"{cid}-{k}", "scope": tag, "scope_source": "rule",
                                  "length_m": sub.length, "geometry": sub})
        after = sum(r["length_m"] for r in chains_out if r["year"] == y)
        n_ch = sum(1 for r in chains_out if r["year"] == y)
        log.add("year_summary", y, f"{len(items)}->{n_ch} chains", before, after,
                f"{len(grp)} input features -> {n_ch} continuous chains" + ("" if n_ch <= 3 else
                                                                         "; >3 because the remaining gaps (> snap_tol_m) are real breaks in the digitised line (river mouth, islands), not joined on purpose"))
    chains = gpd.GeoDataFrame(chains_out, crs=work)
    parts = gpd.GeoDataFrame(parts_out, crs=work)
    q = gpd.GeoDataFrame(quarantine, crs=work) if quarantine else gpd.GeoDataFrame(columns=["fid", "year_raw", "geometry"], geometry="geometry", crs=work)
    return {"chains": chains, "parts": parts, "quarantine": q, "scope": scope, "years": years}


def apply_review_mask(parts: gpd.GeoDataFrame, review_file, log: CleanLog) -> gpd.GeoDataFrame:
    """Honour a hand-edited review package: layer ``shoreline_parts`` with column ``scope_override``
    (open_coast | estuarine_bank) keyed by ``part_id``."""
    if not review_file:
        return parts
    ed = gpd.read_file(repo_path(review_file), layer="shoreline_parts")
    ov = ed.dropna(subset=["scope_override"]).set_index("part_id")["scope_override"].to_dict()
    parts = parts.copy()
    for pid, tag in ov.items():
        if pid in set(parts.part_id) and tag in ("open_coast", "estuarine_bank"):
            old = parts.loc[parts.part_id == pid, "scope"].iloc[0]
            if old != tag:
                parts.loc[parts.part_id == pid, ["scope", "scope_source"]] = [tag, "human_override"]
                log.add("scope_override", int(pid.split("-")[0]), pid, 0.0, 0.0, f"human set scope {old} -> {tag}")
    return parts


def common_extent_table(parts: gpd.GeoDataFrame, scope: CoastScope, years: list[int]) -> pd.DataFrame:
    a, b = scope.a, scope.b
    ax = (b - a) / np.linalg.norm(b - a)
    cov = {}
    for y in years:
        g = list(parts[(parts.year == y) & (parts.scope == "open_coast")].geometry)
        cov[y] = covered_intervals(g, a, ax)
    rows = []
    for i, y1 in enumerate(years):
        for y2 in years[i + 1:]:
            ov = interval_overlap(cov[y1], cov[y2])
            rows.append({"year_a": y1, "year_b": y2, "covered_a_km": total(cov[y1]), "covered_b_km": total(cov[y2]), "common_km": total(ov)})
    allov = cov[years[0]]
    for y in years[1:]:
        allov = interval_overlap(allov, cov[y])
    rows.append({"year_a": "all", "year_b": "all", "covered_a_km": np.nan, "covered_b_km": np.nan, "common_km": total(allov)})
    df = pd.DataFrame(rows)
    df.attrs["all_intervals"] = allov
    return df


def write_gpkg(path, layers: dict, log_df: pd.DataFrame) -> None:
    import pyogrio
    p = repo_path(path)
    if p.exists():
        p.unlink()
    first = True
    for name, gdf in layers.items():
        if len(gdf):
            gdf.to_file(p, layer=name, driver="GPKG", mode="w" if first else "a")
            first = False
    # the log is a plain (non-spatial) table inside the GeoPackage
    pyogrio.write_dataframe(log_df.copy(), p, layer="clean_log", driver="GPKG", append=not first)


def review_map(chains, parts, quarantine, log_df, out) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cols = {1990: "#1f3a93", 2000: "#2ecc40", 2010: "#8e44ad", 2020: "#e74c3c", 2025: "#f39c12"}
    fig, axs = plt.subplots(1, 2, figsize=(20, 8))
    for ax, zoom in zip(axs, [None, (347500, 2026500, 360000, 2035000)]):
        for y, c in cols.items():
            for _, r in parts[parts.year == y].iterrows():
                x, yy = r.geometry.xy
                ax.plot(x, yy, color=c, lw=1.6 if r.scope == "open_coast" else 0.7, ls="-" if r.scope == "open_coast" else "--", alpha=0.9)
            ax.plot([], [], color=c, label=str(y))
        if len(quarantine):
            for _, r in quarantine.iterrows():
                x, yy = r.geometry.xy; ax.plot(x, yy, color="k", lw=2.5, label='quarantined "Hig"')
        rv = log_df[log_df.needs_human_review & log_df.x.notna()]
        ax.scatter(rv.x, rv.y, marker="*", s=90, color="gold", edgecolor="k", zorder=5, label="needs human review")
        rm = log_df[(log_df.action == "small_loop_removed") & log_df.x.notna()]
        ax.scatter(rm.x, rm.y, marker="x", s=60, color="red", zorder=5, label="small loop removed")
        ax.set_aspect("equal")
        if zoom:
            ax.set_xlim(zoom[0], zoom[2]); ax.set_ylim(zoom[1], zoom[3])
        ax.set_title("Cleaned shorelines (solid thick = open coast, dashed thin = estuarine bank) " + ("- river-mouth zoom" if zoom else "- all"), fontsize=9)
        ax.tick_params(labelsize=7)
    axs[0].legend(fontsize=7, loc="lower left")
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)


def run() -> None:  # pragma: no cover
    cfg = load_config()
    rep = RunReport("clean", cfg)
    P = cfg["paths"]; work = cfg["crs_work"]
    rep.add_input(P["shorelines_vector"]); rep.add_input(P["barangays_all"])
    raw = read_vector(P["shorelines_vector"])
    land = unary_union(list(read_vector(P["barangays_all"], work).geometry))
    log = CleanLog()
    res = clean_shorelines(raw, cfg, land, log)
    parts = apply_review_mask(res["parts"], cfg["scope"]["review_mask_file"], log)
    chains, quarantine, scope = res["chains"], res["quarantine"], res["scope"]
    log_df = log.frame()

    # summary before / after per year
    legacy = A.normalise_lines(raw, work)
    summ = []
    for y in res["years"]:
        b = legacy[legacy.year == y]
        a_ = chains[chains.year == y]
        p_ = parts[parts.year == y]
        summ.append({"year": y, "features_before": len(b), "km_before": b.length.sum() / 1000, "chains_after": len(a_),
                     "km_after": a_.length.sum() / 1000, "km_open_coast": p_[p_.scope == "open_coast"].length.sum() / 1000,
                     "km_estuarine": p_[p_.scope == "estuarine_bank"].length.sum() / 1000,
                     "removed_km": (b.length.sum() - a_.length.sum()) / 1000})
    summary = pd.DataFrame(summ)
    cov = common_extent_table(parts, scope, res["years"])

    out_t = ensure_dir("outputs/tables"); ensure_dir("data/interim")
    log_df.to_csv(out_t / "clean_log.csv", index=False)
    log_df[log_df.needs_human_review].to_csv(out_t / "clean_review_list.csv", index=False)
    summary.to_csv(out_t / "clean_summary.csv", index=False)
    cov.to_csv(out_t / "clean_common_extent.csv", index=False)
    parts_w = parts.assign(scope_override=None)
    write_gpkg("data/interim/shorelines_clean.gpkg", {"shorelines_clean": chains, "shoreline_parts": parts, "quarantine": quarantine}, log_df)
    # editable review package
    review = parts_w[["part_id", "year", "chain_id", "scope", "scope_source", "length_m", "scope_override", "geometry"]]
    p = repo_path("data/interim/scope_review.gpkg")
    if p.exists():
        p.unlink()
    review.to_file(p, layer="shoreline_parts", driver="GPKG")
    gpd.GeoDataFrame({"name": ["sea-facing outline (hull chain)"], "geometry": [scope.chain]}, crs=work).to_file(p, layer="hull_chain", driver="GPKG", mode="a")
    gpd.GeoDataFrame({"name": [f"open-coast zone ({cfg['scope']['hull_tolerance_m']} m)"], "geometry": [scope.chain.buffer(scope.tol)]}, crs=work).to_file(p, layer="open_coast_zone", driver="GPKG", mode="a")
    review_map(chains, parts, quarantine, log_df, repo_path("outputs/maps/clean_review.png"))

    rep.count("input_features", len(raw)); rep.count("chains", len(chains)); rep.count("parts", len(parts))
    rep.count("log_actions", log_df.action.value_counts().to_dict())
    for f in ("data/interim/shorelines_clean.gpkg", "data/interim/scope_review.gpkg", "outputs/maps/clean_review.png"):
        rep.add_output(repo_path(f))
    if len(quarantine):
        rep.warn(f"{len(quarantine)} feature(s) quarantined (year not a number): set manual_year_overrides in config once a human decides")
    rep.warn_if_null(cfg["uncertainty_m"], "uncertainty_m")
    rep.write()
    print(summary.round(2).to_string(index=False)); print(cov.round(2).to_string(index=False))
    print(log_df.action.value_counts())


if __name__ == "__main__":  # pragma: no cover
    run()
