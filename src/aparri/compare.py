"""Comparison of two shoreline sets (used by Phase 3B and Phase 6).

For each year we walk along set A every ``step_m`` metres and measure the distance to the nearest
point of set B.  The *signed* offset is projected on the sea-pointing normal of the coast:
positive = A lies seaward of B, negative = landward.  This is a direct, explainable measure of how
much two independent shorelines disagree - the basis for the positional-uncertainty proposal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import nearest_points, unary_union


def sample_line_points(geoms, step_m: float) -> np.ndarray:
    pts = []
    for g in geoms:
        parts = g.geoms if hasattr(g, "geoms") else [g]
        for p in parts:
            if p.length == 0:
                continue
            d = np.arange(0, p.length, step_m)
            d = np.append(d, p.length)
            pts += [p.interpolate(x).coords[0] for x in d]
    return np.array(pts) if pts else np.empty((0, 2))


def signed_offsets(a_geoms, b_geoms, sea_normal: np.ndarray, step_m: float = 30.0, max_search_m: float = 400.0) -> pd.DataFrame:
    """Offsets of points on A to B.  Points of A with no B within ``max_search_m`` are flagged ``unmatched``."""
    pts = sample_line_points(a_geoms, step_m)
    if len(pts) == 0:
        return pd.DataFrame(columns=["x", "y", "dist_m", "signed_m", "unmatched"])
    b = unary_union(list(b_geoms))
    sp = shapely.points(pts[:, 0], pts[:, 1])
    nearest = shapely.shortest_line(sp, b)             # line from each A point to its nearest point on B
    coords = shapely.get_coordinates(nearest).reshape(-1, 2, 2)
    vec = coords[:, 0, :] - coords[:, 1, :]            # from B to A
    dist = np.hypot(vec[:, 0], vec[:, 1])
    signed = vec @ sea_normal
    # keep the sign of the normal component, magnitude = projection
    return pd.DataFrame({"x": pts[:, 0], "y": pts[:, 1], "dist_m": dist, "signed_m": signed, "unmatched": dist > max_search_m})


def summarize(df: pd.DataFrame) -> dict:
    m = df[~df.unmatched]
    if len(m) == 0:
        return {"n": 0}
    return {"n": int(len(df)), "matched_share": float(len(m) / len(df)), "mean_signed_m": float(m.signed_m.mean()),
            "median_abs_m": float(m.dist_m.median()), "rmse_m": float(np.sqrt((m.dist_m ** 2).mean())),
            "p95_m": float(m.dist_m.quantile(0.95)), "share_over_60m": float((m.dist_m > 60).mean())}
