"""Phase 3B: shorelines traced from the Earth Engine edge-pixel rasters, compared with the vector set.

The rasters only contain *edge pixels* (a ~2-pixel band around every water/land boundary of the
NDWI>0 mask).  Their centre line is therefore good to about +/- one pixel (~30 m) at best; sub-pixel
accuracy is impossible from these files.  Steps (all logged):

  1. thin each year's band to a 1-pixel skeleton                (scikit-image ``skeletonize``)
  2. prune short spurs (< ``SPUR_PX`` pixels)                   (speckle that touches the coast)
  3. trace the skeleton into polylines in EPSG:32651
  4. keep only components that touch the open-coast zone and are long enough, i.e. the water body
     connected to the open sea; drop ponds, inland water and open-sea speckle (areas/lengths logged)
  5. tag open_coast / estuarine_bank with the SAME rule as the vector set (``scope.py``)
Output: ``data/interim/shorelines_raster_clean.gpkg`` (same layer layout as the vector set).
"""
from __future__ import annotations

from collections import Counter, defaultdict

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge, unary_union
from skimage.morphology import skeletonize

from . import audit as A
from . import compare as CMP
from .audit_gee import YEARS, GeeRasters
from .clean import CleanLog, apply_review_mask, common_extent_table, orient_nw_se, tag_parts, write_gpkg
from .io import ensure_dir, load_config, read_vector, repo_path
from .runreport import RunReport
from .scope import CoastScope

SPUR_PX = 4                 # branches shorter than this (~120 m) that end freely are speckle, not coast
SPECKLE_AREA_PX = 120        # enclosed regions smaller than this (~10 ha) are noise holes/islets
MIN_COMPONENT_M = 300.0     # a traced component must be at least this long to count as a shoreline

_NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def thin_adjacency(skel: np.ndarray) -> dict:
    """8-neighbour graph of skeleton pixels, minus redundant staircase diagonals.

    A diagonal link p-q is redundant when p and q also share a 4-neighbour pixel, otherwise every
    corner of a staircase would look like a junction."""
    pix = set(zip(*np.nonzero(skel)))
    adj: dict = {p: set() for p in pix}
    for (r, c) in pix:
        for dr, dc in _NB:
            q = (r + dr, c + dc)
            if q in pix:
                if dr != 0 and dc != 0 and ((r + dr, c) in pix or (r, c + dc) in pix):
                    continue
                adj[(r, c)].add(q)
    for p in list(adj):
        for q in list(adj[p]):
            adj[q].add(p)
    return adj


def trace_edges(skel: np.ndarray) -> list[list[tuple[int, int]]]:
    """Pixel paths between key pixels (ends, junctions); closed rings are returned as one path."""
    adj = thin_adjacency(skel)
    key = {p for p, n in adj.items() if len(n) != 2}
    seen: set = set()
    edges = []
    def walk(start, nxt):
        path = [start, nxt]
        prev, cur = start, nxt
        while cur not in key:
            n = [x for x in adj[cur] if x != prev]
            if not n:
                break
            prev, cur = cur, n[0]
            path.append(cur)
            if cur == start:
                break
        return path
    for k in key:
        for n in adj[k]:
            e = frozenset((k, n))
            if e in seen:
                continue
            path = walk(k, n)
            for a, b in zip(path[:-1], path[1:]):
                seen.add(frozenset((a, b)))
            edges.append(path)
    # rings with no key pixel
    remaining = {p for p in adj if p not in key}
    used = {p for e in edges for p in e}
    for p in sorted(remaining - used):
        if p in used:
            continue
        n0 = next(iter(adj[p]))
        path = walk(p, n0)
        used |= set(path)
        edges.append(path)
    return edges


def prune_spurs(skel: np.ndarray, min_px: int, max_iter: int = 8) -> tuple[np.ndarray, int]:
    """Remove branches shorter than ``min_px`` that end freely on a junction (iteratively)."""
    skel = skel.copy()
    removed = 0
    for _ in range(max_iter):
        edges = trace_edges(skel)
        deg = Counter()
        for e in edges:
            deg[e[0]] += 1; deg[e[-1]] += 1
        kill = [e for e in edges if len(e) < min_px and e[0] != e[-1] and
                ((deg[e[0]] == 1 and deg[e[-1]] >= 3) or (deg[e[-1]] == 1 and deg[e[0]] >= 3))]
        if not kill:
            break
        for e in kill:
            end_free = e[0] if deg[e[0]] == 1 else e[-1]
            core = e[:-1] if end_free == e[0] else e[1:]
            for (r, c) in core:
                skel[r, c] = False
            removed += 1
    return skel, removed


def edges_to_lines(edges, x: np.ndarray, y: np.ndarray) -> list[LineString]:
    out = []
    for e in edges:
        if len(e) >= 2:
            out.append(LineString([(x[r, c], y[r, c]) for r, c in e]))
    return out


def remove_speckle_rings(mask: np.ndarray, max_area_px: int) -> tuple[np.ndarray, int]:
    """Delete small closed rings of edge pixels (islands / holes of a few pixels in the water mask).

    A region completely enclosed by edge pixels and smaller than ``max_area_px`` is a hole or islet in
    the NDWI mask - i.e. noise at 30 m - not a coastline.  The enclosing ring pixels are removed."""
    from scipy import ndimage
    lab, n = ndimage.label(~mask, structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    h, w = mask.shape
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    out = mask.copy()
    n_removed = 0
    for k in range(1, n + 1):
        if k in border or sizes[k] > max_area_px:
            continue
        reg = lab == k
        ring = ndimage.binary_dilation(reg, structure=np.ones((3, 3), bool)) & mask
        out &= ~ring
        n_removed += 1
    return out, n_removed


def raster_year_lines(mask: np.ndarray, x: np.ndarray, y: np.ndarray, scope: CoastScope, log: CleanLog, year: int,
                      min_component_m: float = MIN_COMPONENT_M, spur_px: int = SPUR_PX) -> list[LineString]:
    mask, n_rings = remove_speckle_rings(mask, SPECKLE_AREA_PX)
    if n_rings:
        log.add("speckle_rings_removed", year, "raster", float(n_rings), 0.0,
                f"{n_rings} closed rings enclosing < {SPECKLE_AREA_PX} px (~{SPECKLE_AREA_PX*0.085:.0f} ha) removed (holes/islets of the water mask)")
    skel = skeletonize(mask)
    log.add("skeletonize", year, "raster", float(mask.sum()), float(skel.sum()), f"edge band {int(mask.sum())} px -> centre line {int(skel.sum())} px")
    skel, n_sp = prune_spurs(skel, spur_px)
    if n_sp:
        log.add("spurs_pruned", year, "raster", float(n_sp), 0.0, f"{n_sp} branches shorter than {spur_px} px (~{spur_px*30} m) that end freely were removed")
    edges = trace_edges(skel)
    # components = connected groups of skeleton pixels (8-connectivity - exact and fast)
    from scipy import ndimage
    lab, ncomp = ndimage.label(skel, structure=np.ones((3, 3)))
    kept: list[LineString] = []
    zone = scope.chain.buffer(scope.tol)
    edge_comp: dict[int, list[LineString]] = {}
    for e in edges:
        if len(e) >= 2:
            edge_comp.setdefault(int(lab[e[0][0], e[0][1]]), []).append(LineString([(x[r, c], y[r, c]) for r, c in e]))
    for cid, members in edge_comp.items():
        L = sum(m.length for m in members)
        in_zone = sum(m.intersection(zone).length for m in members)
        if L < min_component_m or in_zone <= 0:
            cen = unary_union(members).centroid
            log.add("component_dropped", year, "raster", L, 0.0,
                    ("shorter than %d m" % min_component_m if L < min_component_m else "does not touch the open-coast zone (pond / inland water / open-sea speckle)"),
                    (cen.x, cen.y))
            continue
        kept.extend(members)
    return kept


def build(cfg: dict) -> dict:  # pragma: no cover - IO heavy
    work = cfg["crs_work"]; P = cfg["paths"]
    r = GeeRasters(repo_path(P["gee_dir"]), work)
    lines = A.normalise_lines(read_vector(P["shorelines_vector"]), work)
    from shapely.ops import unary_union as uu
    land = uu(list(read_vector(P["barangays_all"], work).geometry))
    scope = CoastScope(list(lines.geometry), land, cfg["scope"]["hull_tolerance_m"], cfg["scope"].get("concave_ratio", 0.1))
    log = CleanLog()
    chains, parts = [], []
    for y in YEARS:
        ls = raster_year_lines(r.shore[y] > 0, r.x, r.y, scope, log, y)
        merged = linemerge(ls) if ls else None
        geoms = list(merged.geoms) if merged is not None and merged.geom_type == "MultiLineString" else ([merged] if merged is not None else [])
        n = 0
        for g in geoms:
            if g.length < 60:
                continue
            n += 1
            g = LineString(orient_nw_se(np.array(g.coords)[:, :2]))
            cid = f"{y}-{n}"
            chains.append({"year": y, "chain_id": cid, "source_fids": "raster", "length_m": g.length, "n_vertices": len(g.coords), "geometry": g})
            for k, (sub, tag, ln) in enumerate(tag_parts(g, scope, cfg["clean"].get("min_scope_run_m", 150.0)), start=1):
                parts.append({"year": y, "chain_id": cid, "part_id": f"{cid}-{k}", "scope": tag, "scope_source": "rule", "length_m": sub.length, "geometry": sub})
        log.add("year_summary", y, f"{n} chains", float(r.shore[y].sum()) * 30, sum(g.length for g in geoms), f"{n} traced chains, {sum(g.length for g in geoms)/1000:.1f} km")
    return {"chains": gpd.GeoDataFrame(chains, crs=work), "parts": gpd.GeoDataFrame(parts, crs=work), "log": log, "scope": scope, "rasters": r}


def compare_sets(raster_parts: gpd.GeoDataFrame, vector_parts: gpd.GeoDataFrame, scope: CoastScope, years) -> tuple[pd.DataFrame, gpd.GeoDataFrame]:
    rows, bad = [], []
    for y in years:
        a = list(raster_parts[(raster_parts.year == y) & (raster_parts.scope == "open_coast")].geometry)
        b = list(vector_parts[(vector_parts.year == y) & (vector_parts.scope == "open_coast")].geometry)
        if not a or not b:
            continue
        off = CMP.signed_offsets(a, b, scope.sea_normal, 30.0)        # raster -> vector
        s = CMP.summarize(off)
        # reverse direction: how much of the vector coast has a raster line within 60 m
        rev = CMP.signed_offsets(b, a, scope.sea_normal, 30.0)
        s_rev = CMP.summarize(rev)
        la = sum(g.length for g in a); lb = sum(g.length for g in b)
        rows.append({"year": y, "raster_open_km": la / 1000, "vector_open_km": lb / 1000, "length_ratio": la / lb,
                     "vector_covered_within_60m": float((rev.dist_m <= 60).mean()), **{f"r2v_{k}": v for k, v in s.items()}})
        d = off[off.dist_m > 60].assign(year=y)
        bad.append(d)
    out = pd.DataFrame(rows)
    badg = pd.concat(bad) if bad else pd.DataFrame(columns=["x", "y", "dist_m", "signed_m", "year"])
    return out, gpd.GeoDataFrame(badg, geometry=gpd.points_from_xy(badg.x, badg.y), crs=32651)


def comparison_figure(raster_parts, vector_parts, scope, years, out) -> None:  # pragma: no cover
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    a = scope.a; ab = (scope.b - scope.a) / np.linalg.norm(scope.b - scope.a)
    fig, axs = plt.subplots(len(years), 1, figsize=(15, 2.6 * len(years)), sharex=True)
    for ax, y in zip(axs, years):
        ra = list(raster_parts[(raster_parts.year == y) & (raster_parts.scope == "open_coast")].geometry)
        ve = list(vector_parts[(vector_parts.year == y) & (vector_parts.scope == "open_coast")].geometry)
        if not ra or not ve:
            continue
        off = CMP.signed_offsets(ra, ve, scope.sea_normal, 30.0)
        t = (off[["x", "y"]].values - a) @ ab / 1000
        ax.scatter(t, off.signed_m, s=3, c="#d62728")
        ax.axhline(0, color="k", lw=0.5); ax.axhspan(-60, 60, color="0.9", zorder=0)
        ax.set_ylim(-250, 250); ax.set_ylabel(f"{y}\nraster - vector (m)", fontsize=8)
        ax.text(0.01, 0.85, f"median |d| = {off.dist_m.median():.0f} m, p95 = {off.dist_m.quantile(.95):.0f} m", transform=ax.transAxes, fontsize=8)
    axs[-1].set_xlabel("distance along the coast from the NW end (km)")
    fig.suptitle("Offset between the raster-derived and the vector shoreline along the open coast (+ = raster is seaward). Grey band = ±2 pixels (60 m)")
    fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)


def run() -> None:  # pragma: no cover
    cfg = load_config()
    rep = RunReport("raster_shore", cfg)
    P = cfg["paths"]
    for f in repo_path(P["gee_dir"]).glob("Aparri_Shoreline_*.tif"):
        rep.add_input(f)
    res = build(cfg)
    parts, chains, log, scope = res["parts"], res["chains"], res["log"], res["scope"]
    vec_parts = gpd.read_file(repo_path("data/interim/shorelines_clean.gpkg"), layer="shoreline_parts")
    rep.add_input("data/interim/shorelines_clean.gpkg")
    cmp_df, bad = compare_sets(parts, vec_parts, scope, YEARS)
    log_df = log.frame()
    t = ensure_dir("outputs/tables")
    log_df.to_csv(t / "raster_clean_log.csv", index=False)
    cmp_df.to_csv(t / "raster_vs_vector_comparison.csv", index=False)
    cov = common_extent_table(parts, scope, YEARS); cov.to_csv(t / "raster_common_extent.csv", index=False)
    write_gpkg("data/interim/shorelines_raster_clean.gpkg", {"shorelines_clean": chains, "shoreline_parts": parts}, log_df)
    if len(bad):
        bad.to_file(repo_path("data/interim/shorelines_raster_clean.gpkg"), layer="disagreement_points", driver="GPKG", mode="a")
    comparison_figure(parts, vec_parts, scope, YEARS, repo_path("outputs/maps/raster_vs_vector_offsets.png"))
    rep.count("chains", len(chains)); rep.count("parts", len(parts)); rep.count("disagreement_points_gt60m", len(bad))
    rep.add_output(repo_path("data/interim/shorelines_raster_clean.gpkg"))
    rep.warn_if_null(cfg["uncertainty_m"], "uncertainty_m")
    rep.write()
    print(cmp_df.round(2).to_string(index=False)); print(cov.round(2).tail(1).to_string(index=False))
    print(log_df.action.value_counts())


if __name__ == "__main__":  # pragma: no cover
    run()
