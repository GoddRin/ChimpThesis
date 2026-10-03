"""Scope rule: which parts of the shoreline are the open, sea-facing coast?

The thesis studies "one continuous shoreline" of eight barangays, but the legacy lines
also run up both banks of the Cagayan River mouth.  River banks move for different
reasons (flood discharge, bar migration) than a wave-exposed coast, so mixing them
distorts rates.  We therefore tag every position as ``open_coast`` or something else
with ONE transparent rule, and export a QGIS-editable mask so the students can overrule it.

Rule (``config.scope.hull_tolerance_m``):
  1. Take all supplied shorelines (all years) and wrap a *concave hull* around them (a
     tight outline, ``scope.concave_ratio``).  Its sea-facing edge hugs the open coast and
     bridges the river mouth with one long straight edge; the river banks lie behind it.
  2. A position is ``open_coast`` if it is within the tolerance of that sea-facing hull
     edge ("chain").  Beyond the chain on the sea side is ``sea``; behind it is ``land`` or
     ``inner_water`` (river, estuary, lagoon).
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import LineString, MultiPoint, Polygon
from shapely.ops import unary_union


def _ring_chains(hull: Polygon, a: np.ndarray, b: np.ndarray) -> tuple[LineString, LineString]:
    """Split the hull ring into the two chains between the extreme points a and b."""
    ring = np.array(hull.exterior.coords)[:-1]
    ia = int(np.argmin(np.hypot(*(ring - a).T)))
    ib = int(np.argmin(np.hypot(*(ring - b).T)))
    n = len(ring)
    idx1 = [(ia + k) % n for k in range((ib - ia) % n + 1)]
    idx2 = [(ib + k) % n for k in range((ia - ib) % n + 1)]
    return LineString(ring[idx1]), LineString(ring[idx2])


class CoastScope:
    """Geometry of the open-coast rule, built once from the supplied lines.

    Parameters
    ----------
    geoms : iterable of shapely lines (any year), in a metric CRS.
    land : shapely (multi)polygon of land (municipal barangays), same CRS.
    tol_m : distance to the sea-facing hull edge counted as open coast.
    """

    def __init__(self, geoms, land, tol_m: float, concave_ratio: float = 0.1, densify_m: float = 100.0):
        self.tol = float(tol_m)
        self.land = land
        dens = [shapely.segmentize(g, densify_m) for g in geoms]        # so the hull follows the lines, not just their vertices
        pts = np.vstack([np.array(g.coords)[:, :2] for g in dens])
        self.hull = shapely.concave_hull(MultiPoint(pts), ratio=concave_ratio)
        s = pts[:, 0] - pts[:, 1]                       # NW end has the smallest x - y, SE end the largest
        self.a, self.b = pts[np.argmin(s)], pts[np.argmax(s)]
        self._ab = self.b - self.a
        # Sea is the side of the NW-SE chord that is away from the bulk of the shoreline vertices
        # (the river banks run inland, so the vertex cloud's centre sits on the land side).
        self._sea_sign = -np.sign(self._cross(pts.mean(axis=0)))[0]
        c1, c2 = _ring_chains(self.hull, self.a, self.b)
        def seaness(ch: LineString) -> float:
            samp = np.array([ch.interpolate(f, normalized=True).coords[0] for f in np.linspace(0, 1, 80)])
            return float((self._cross(samp) * self._sea_sign).mean())
        self.chain = c1 if seaness(c1) >= seaness(c2) else c2
        # "Sea" = everything on the sea side of the chain: the chain pushed 60 km along the sea normal.
        n = self._sea_sign * np.array([-self._ab[1], self._ab[0]]) / np.linalg.norm(self._ab)
        self.sea_normal = n
        cc = np.array(self.chain.coords)
        self.sea_poly = Polygon(np.vstack([cc, (cc + 60_000 * n)[::-1]]))
        if not self.sea_poly.is_valid:
            self.sea_poly = self.sea_poly.buffer(0)

    def _cross(self, p: np.ndarray) -> np.ndarray:
        p = np.atleast_2d(p)
        return self._ab[0] * (p[:, 1] - self.a[1]) - self._ab[1] * (p[:, 0] - self.a[0])

    def classify_xy(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Zone of each point: open_coast | sea | land | inner_water.

        ``inner_water`` = behind the sea-facing edge but not on the municipal land polygons
        (river, estuary, lagoon)."""
        x = np.asarray(x, float); y = np.asarray(y, float)
        pts = shapely.points(x, y)
        d = shapely.distance(pts, self.chain)
        in_sea = shapely.contains(self.sea_poly, pts)
        on_land = shapely.contains(self.land, pts)
        return np.where(d <= self.tol, "open_coast",
               np.where(in_sea, "sea", np.where(on_land, "land", "inner_water")))

    def classify_line_vertices(self, geom) -> np.ndarray:
        c = np.array(geom.coords)[:, :2]
        return self.classify_xy(c[:, 0], c[:, 1])


def runs(flags: np.ndarray) -> list[tuple[int, int, bool]]:
    """Run-length encode a boolean vector -> (start, end_inclusive, value)."""
    out, start = [], 0
    for i in range(1, len(flags) + 1):
        if i == len(flags) or flags[i] != flags[start]:
            out.append((start, i - 1, bool(flags[start])))
            start = i
    return out
